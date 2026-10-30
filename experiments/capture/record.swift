// Records system audio and the microphone to separate lossless files with
// ScreenCaptureKit (macOS 15+), without a virtual audio device.
//
//   swift experiments/capture/record.swift [--app <name>]... [--mic <name>] [--out <dir>]
//
// Writes system.m4a and mic.m4a (Apple Lossless, 48 kHz) and timing.json into
// the output folder. Stop with Ctrl-C.

import AVFoundation
import Foundation
import ScreenCaptureKit

let sampleRate = 48_000

struct Options {
    var apps: [String] = []
    var mic: String?
    var outDir: URL

    static func parse() -> Options {
        let stamp = ISO8601DateFormatter.string(
            from: Date(), timeZone: .current, formatOptions: [.withFullDate, .withTime, .withDashSeparatorInDate]
        )
        let base = ProcessInfo.processInfo.environment["MEETING_REVIEW_DATA"].map {
            URL(fileURLWithPath: $0).appendingPathComponent("raw")
        } ?? URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
        var options = Options(outDir: base.appendingPathComponent(stamp))
        var args = CommandLine.arguments.dropFirst().makeIterator()
        while let arg = args.next() {
            switch arg {
            case "--app": if let v = args.next() { options.apps.append(v) }
            case "--mic": options.mic = args.next()
            case "--out": if let v = args.next() { options.outDir = URL(fileURLWithPath: v) }
            default:
                FileHandle.standardError.write("usage: record.swift [--app <name>]... [--mic <name>] [--out <dir>]\n".data(using: .utf8)!)
                exit(2)
            }
        }
        return options
    }
}

/// One output file fed from one ScreenCaptureKit stream type.
final class Track {
    let name: String
    let writer: AVAssetWriter
    let input: AVAssetWriterInput
    let channels: Int
    var firstTime: CMTime?
    var lastEnd: CMTime = .zero
    var silenceFilled: Double = 0
    var peak: Float = 0

    init(name: String, url: URL, channels: Int) throws {
        self.name = name
        self.channels = channels
        writer = try AVAssetWriter(outputURL: url, fileType: .m4a)
        input = AVAssetWriterInput(mediaType: .audio, outputSettings: [
            AVFormatIDKey: kAudioFormatAppleLossless,
            AVSampleRateKey: sampleRate,
            AVNumberOfChannelsKey: channels,
            AVEncoderBitDepthHintKey: 16,
        ])
        input.expectsMediaDataInRealTime = true
        writer.add(input)
    }

    func append(_ buffer: CMSampleBuffer, sessionStart: CMTime) {
        if writer.status == .unknown {
            writer.startWriting()
            writer.startSession(atSourceTime: sessionStart)
        }
        guard writer.status == .writing, input.isReadyForMoreMediaData else { return }
        let time = buffer.presentationTimeStamp
        if firstTime == nil {
            firstTime = time
            lastEnd = sessionStart
        }
        // Fill a late start or a dropout with silence so both files keep one timeline.
        if (time - lastEnd).seconds > 0.01, let silence = Track.silence(like: buffer, from: lastEnd, to: time) {
            silenceFilled += (time - lastEnd).seconds
            input.append(silence)
        }
        lastEnd = time + buffer.duration
        peak = max(peak, Track.peak(of: buffer))
        input.append(buffer)
    }

    /// A zeroed buffer in the same format as `buffer`, covering `start` to `end`.
    static func silence(like buffer: CMSampleBuffer, from start: CMTime, to end: CMTime) -> CMSampleBuffer? {
        guard let description = buffer.formatDescription else { return nil }
        let format = AVAudioFormat(cmAudioFormatDescription: description)
        let count = AVAudioFrameCount(((end - start).seconds * format.sampleRate).rounded())
        guard count > 0, let pcm = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: count) else { return nil }
        pcm.frameLength = count
        for audio in UnsafeMutableAudioBufferListPointer(pcm.mutableAudioBufferList) {
            if let data = audio.mData { memset(data, 0, Int(audio.mDataByteSize)) }
        }
        var timing = CMSampleTimingInfo(
            duration: CMTime(value: 1, timescale: CMTimeScale(format.sampleRate)),
            presentationTimeStamp: start, decodeTimeStamp: .invalid
        )
        var sample: CMSampleBuffer?
        guard CMSampleBufferCreate(
            allocator: nil, dataBuffer: nil, dataReady: false, makeDataReadyCallback: nil, refcon: nil,
            formatDescription: description, sampleCount: CMItemCount(count),
            sampleTimingEntryCount: 1, sampleTimingArray: &timing,
            sampleSizeEntryCount: 0, sampleSizeArray: nil, sampleBufferOut: &sample
        ) == noErr, let sample,
            CMSampleBufferSetDataBufferFromAudioBufferList(
                sample, blockBufferAllocator: nil, blockBufferMemoryAllocator: nil, flags: 0, bufferList: pcm.audioBufferList
            ) == noErr else { return nil }
        return sample
    }

    /// Peak absolute sample value, assuming ScreenCaptureKit's float PCM.
    static func peak(of buffer: CMSampleBuffer) -> Float {
        var result: Float = 0
        try? buffer.withAudioBufferList { list, _ in
            for audio in list {
                guard let data = audio.mData else { continue }
                let samples = data.assumingMemoryBound(to: Float.self)
                for i in 0..<Int(audio.mDataByteSize) / MemoryLayout<Float>.size {
                    result = max(result, abs(samples[i]))
                }
            }
        }
        return result
    }

    func takePeakDB() -> String {
        defer { peak = 0 }
        return peak > 0 ? String(format: "%6.1f dB", 20 * log10(peak)) : "  silent"
    }
}

final class Recorder: NSObject, SCStreamOutput, SCStreamDelegate {
    let system: Track
    let mic: Track
    let queue = DispatchQueue(label: "capture")
    var sessionStart: CMTime?
    var stream: SCStream?

    init(outDir: URL) throws {
        system = try Track(name: "system", url: outDir.appendingPathComponent("system.m4a"), channels: 2)
        mic = try Track(name: "mic", url: outDir.appendingPathComponent("mic.m4a"), channels: 1)
    }

    func start(apps: [String], mic micName: String?) async throws {
        let content = try await SCShareableContent.excludingDesktopWindows(false, onScreenWindowsOnly: false)
        guard let display = content.displays.first else { throw CaptureError("no display found") }
        let filter: SCContentFilter
        if apps.isEmpty {
            filter = SCContentFilter(display: display, excludingApplications: [], exceptingWindows: [])
        } else {
            let chosen = content.applications.filter { app in
                apps.contains { app.applicationName.localizedCaseInsensitiveContains($0) || app.bundleIdentifier.localizedCaseInsensitiveContains($0) }
            }
            guard !chosen.isEmpty else { throw CaptureError("no running app matches \(apps)") }
            print("capturing audio from: \(chosen.map(\.applicationName).joined(separator: ", "))")
            filter = SCContentFilter(display: display, including: chosen, exceptingWindows: [])
        }

        let config = SCStreamConfiguration()
        config.capturesAudio = true
        config.captureMicrophone = true
        // Must stay off: it drops audio from the whole app that launched this
        // script (the terminal, and anything else run from it).
        config.excludesCurrentProcessAudio = false
        if let micName {
            let devices = AVCaptureDevice.DiscoverySession(
                deviceTypes: [.microphone, .external], mediaType: .audio, position: .unspecified
            ).devices
            guard let device = devices.first(where: { $0.localizedName.localizedCaseInsensitiveContains(micName) }) else {
                throw CaptureError("no microphone matches \"\(micName)\"; have: \(devices.map(\.localizedName))")
            }
            print("microphone: \(device.localizedName)")
            config.microphoneCaptureDeviceID = device.uniqueID
        }
        config.sampleRate = sampleRate
        config.channelCount = 2
        // Video can't be turned off; keep it tiny and rare.
        config.width = 2
        config.height = 2
        config.minimumFrameInterval = CMTime(value: 1, timescale: 1)

        let stream = SCStream(filter: filter, configuration: config, delegate: self)
        try stream.addStreamOutput(self, type: .screen, sampleHandlerQueue: queue)
        try stream.addStreamOutput(self, type: .audio, sampleHandlerQueue: queue)
        try stream.addStreamOutput(self, type: .microphone, sampleHandlerQueue: queue)
        try await stream.startCapture()
        self.stream = stream
    }

    func stream(_ stream: SCStream, didOutputSampleBuffer buffer: CMSampleBuffer, of type: SCStreamOutputType) {
        guard buffer.isValid, buffer.numSamples > 0 else { return }
        let track: Track
        switch type {
        case .audio: track = system
        case .microphone: track = mic
        default: return
        }
        // Both files share one timeline: the first audio buffer from either stream.
        if sessionStart == nil { sessionStart = buffer.presentationTimeStamp }
        track.append(buffer, sessionStart: sessionStart!)
    }

    func stream(_ stream: SCStream, didStopWithError error: Error) {
        print("capture stopped: \(error.localizedDescription)")
        Task { await self.stop(); exit(1) }
    }

    func meter() -> String {
        queue.sync {
            let seconds = sessionStart.map { (system.lastEnd == .zero ? mic.lastEnd : max(system.lastEnd, mic.lastEnd)) - $0 }?.seconds ?? 0
            return String(format: "%02d:%02d  system %@  mic %@", Int(seconds) / 60, Int(seconds) % 60, system.takePeakDB(), mic.takePeakDB())
        }
    }

    func stop() async {
        try? await stream?.stopCapture()
        stream = nil
        for track in [system, mic] where track.writer.status == .writing {
            track.input.markAsFinished()
            await track.writer.finishWriting()
        }
    }

    func timing() -> [String: Any] {
        var result: [String: Any] = ["sample_rate": sampleRate]
        for track in [system, mic] {
            result[track.name] = [
                "starts_at_seconds": track.firstTime.flatMap { t in sessionStart.map { (t - $0).seconds } } ?? NSNull(),
                "duration_seconds": sessionStart.map { (track.lastEnd - $0).seconds } ?? 0,
                "silence_filled_seconds": track.silenceFilled,
                "written": track.writer.status == .completed,
            ]
        }
        return result
    }
}

struct CaptureError: Error, CustomStringConvertible {
    let description: String
    init(_ description: String) { self.description = description }
}

let options = Options.parse()
try FileManager.default.createDirectory(at: options.outDir, withIntermediateDirectories: true)
let recorder = try Recorder(outDir: options.outDir)
do {
    try await recorder.start(apps: options.apps, mic: options.mic)
} catch {
    print("could not start capture: \(error)")
    print("grant Screen & System Audio Recording and Microphone to your terminal in System Settings > Privacy & Security, then restart the terminal.")
    exit(1)
}
print("recording to \(options.outDir.path)  (Ctrl-C to stop)")

signal(SIGINT, SIG_IGN)
let stopSignal = DispatchSource.makeSignalSource(signal: SIGINT, queue: .main)
stopSignal.setEventHandler {
    Task {
        await recorder.stop()
        let data = try JSONSerialization.data(withJSONObject: recorder.timing(), options: [.prettyPrinted, .sortedKeys])
        try data.write(to: options.outDir.appendingPathComponent("timing.json"))
        print("\nsaved system.m4a, mic.m4a, timing.json in \(options.outDir.path)")
        print(String(data: data, encoding: .utf8)!)
        exit(0)
    }
}
stopSignal.resume()

let meterTimer = DispatchSource.makeTimerSource(queue: .global())
meterTimer.schedule(deadline: .now() + 5, repeating: 5)
meterTimer.setEventHandler { print(recorder.meter()) }
meterTimer.resume()

while true { try await Task.sleep(for: .seconds(3600)) }
