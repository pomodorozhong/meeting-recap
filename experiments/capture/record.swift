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
        let usage = "usage: record.swift [--app <name>]... [--mic <name>] [--out <dir>]"
        var apps: [String] = [], mic: String?, out: String?
        var args = CommandLine.arguments.dropFirst().makeIterator()
        while let arg = args.next() {
            guard ["--app", "--mic", "--out"].contains(arg) else { fail(usage) }
            // A missing value must not quietly widen the capture, as a bare --app would to all system audio.
            guard let value = args.next(), !value.isEmpty, !value.hasPrefix("--") else { fail("\(arg) needs a value\n\(usage)") }
            switch arg {
            case "--app": apps.append(value)
            case "--mic": mic = value
            default: out = value
            }
        }
        let outDir: URL
        if let out {
            outDir = URL(fileURLWithPath: out)
        } else if let data = ProcessInfo.processInfo.environment["MEETING_REVIEW_DATA"], !data.isEmpty {
            let stamp = ISO8601DateFormatter.string(
                from: Date(), timeZone: .current, formatOptions: [.withFullDate, .withTime, .withDashSeparatorInDate]
            )
            outDir = URL(fileURLWithPath: data).appendingPathComponent("raw").appendingPathComponent(stamp)
        } else {
            fail("set MEETING_REVIEW_DATA to the private dataset folder, or pass --out <dir> outside any Git checkout")
        }
        return Options(apps: apps, mic: mic, outDir: privateFolder(outDir))
    }
}

func fail(_ message: String, status: Int32 = 2) -> Never {
    FileHandle.standardError.write((message + "\n").data(using: .utf8)!)
    exit(status)
}

/// The output folder with symlinks resolved, refused when it is inside a Git checkout (a worktree's .git is a
/// file) or already holds files: recordings are private and must never land in this public repository.
func privateFolder(_ url: URL) -> URL {
    let files = FileManager.default
    // Resolve the deepest part that exists, so a symlink anywhere on the path counts where it points.
    var existing = url.standardizedFileURL, rest: [String] = []
    while !files.fileExists(atPath: existing.path), existing.path != "/" {
        rest.insert(existing.lastPathComponent, at: 0)
        existing.deleteLastPathComponent()
    }
    let resolved = rest.reduce(existing.resolvingSymlinksInPath()) { $0.appendingPathComponent($1) }
    var folder = resolved
    while true {
        if files.fileExists(atPath: folder.appendingPathComponent(".git").path) {
            fail("refusing to record into \(resolved.path): it is inside the Git checkout at \(folder.path)")
        }
        if folder.path == "/" { break }
        folder.deleteLastPathComponent()
    }
    if let contents = try? files.contentsOfDirectory(atPath: resolved.path), !contents.isEmpty {
        fail("refusing to record into \(resolved.path): it already holds files")
    }
    return resolved
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
    var dropped: Double = 0
    var peak: Float = 0
    /// The first write failure; once set, the recording has lost audio and must stop.
    var error: String?

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
        guard error == nil else { return }
        if writer.status == .unknown {
            guard writer.startWriting() else { return fail("could not start writing") }
            writer.startSession(atSourceTime: sessionStart)
        }
        guard writer.status == .writing else { return fail("writer stopped") }
        guard input.isReadyForMoreMediaData else {
            // The encoder fell behind; the gap is filled with silence below and reported in timing.json.
            dropped += buffer.duration.seconds
            return
        }
        let time = buffer.presentationTimeStamp
        if firstTime == nil {
            firstTime = time
            lastEnd = sessionStart
        }
        // Fill a late start or a dropout with silence so both files keep one timeline.
        if (time - lastEnd).seconds > 0.01, let silence = Track.silence(like: buffer, from: lastEnd, to: time) {
            silenceFilled += (time - lastEnd).seconds
            guard input.append(silence) else { return fail("could not write silence") }
        }
        lastEnd = time + buffer.duration
        peak = max(peak, Track.peak(of: buffer))
        guard input.append(buffer) else { return fail("could not write audio") }
    }

    func fail(_ what: String) {
        error = "\(what): \(writer.error?.localizedDescription ?? "unknown error")"
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
    /// Called once, on the capture queue, when a track can no longer be written.
    var onFailure: (String) -> Void = { _ in }
    var reportedFailure = false

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
        if let error = track.error, !reportedFailure {
            reportedFailure = true
            onFailure("\(track.name).m4a: \(error)")
        }
    }

    func stream(_ stream: SCStream, didStopWithError error: Error) {
        onFailure("capture stopped: \(error.localizedDescription)")
    }

    func meter() -> String {
        queue.sync {
            let seconds = sessionStart.map { (system.lastEnd == .zero ? mic.lastEnd : max(system.lastEnd, mic.lastEnd)) - $0 }?.seconds ?? 0
            return String(format: "%02d:%02d  system %@  mic %@", Int(seconds) / 60, Int(seconds) % 60, system.takePeakDB(), mic.takePeakDB())
        }
    }

    /// Stops capture and finishes both files, returning what went wrong with each; empty means both are complete.
    func stop() async -> [String] {
        try? await stream?.stopCapture()
        stream = nil
        var problems: [String] = []
        for track in [system, mic] {
            if track.writer.status == .writing {
                track.input.markAsFinished()
                await track.writer.finishWriting()
            }
            if let error = track.error {
                problems.append("\(track.name).m4a: \(error)")
            } else if track.writer.status == .unknown {
                problems.append("\(track.name).m4a: no audio arrived")
            } else if track.writer.status != .completed {
                problems.append("\(track.name).m4a: \(track.writer.error?.localizedDescription ?? "not finished")")
            }
        }
        return problems
    }

    func timing() -> [String: Any] {
        var result: [String: Any] = ["sample_rate": sampleRate]
        for track in [system, mic] {
            result[track.name] = [
                "starts_at_seconds": track.firstTime.flatMap { t in sessionStart.map { (t - $0).seconds } } ?? NSNull(),
                "duration_seconds": sessionStart.map { (track.lastEnd - $0).seconds } ?? 0,
                "silence_filled_seconds": track.silenceFilled,
                "dropped_seconds": track.dropped,
                "written": track.writer.status == .completed,
                "error": track.error.map { $0 as Any } ?? NSNull(),
            ] as [String: Any]
        }
        return result
    }
}

struct CaptureError: Error, CustomStringConvertible {
    let description: String
    init(_ description: String) { self.description = description }
}

let options = Options.parse()
do {
    try FileManager.default.createDirectory(at: options.outDir, withIntermediateDirectories: true)
} catch {
    fail("could not create \(options.outDir.path): \(error.localizedDescription)", status: 1)
}
let recorder: Recorder
do {
    recorder = try Recorder(outDir: options.outDir)
} catch {
    fail("could not create the output files: \(error.localizedDescription)", status: 1)
}

let finishing = NSLock()
var finished = false

/// Stops once, writes timing.json, and exits 0 only when both files and timing.json were written completely.
@MainActor func finish(failure: String? = nil) async -> Never {
    let first = finishing.withLock {
        defer { finished = true }
        return !finished
    }
    guard first else {
        // Another stop is already writing the files; it exits when done.
        while true { try? await Task.sleep(for: .seconds(3600)) }
    }
    var problems = failure.map { [$0] } ?? []
    problems += await recorder.stop()
    do {
        let data = try JSONSerialization.data(withJSONObject: recorder.timing(), options: [.prettyPrinted, .sortedKeys])
        try data.write(to: options.outDir.appendingPathComponent("timing.json"))
        print(String(data: data, encoding: .utf8)!)
    } catch {
        problems.append("timing.json: \(error.localizedDescription)")
    }
    guard problems.isEmpty else {
        fail("\nRECORDING FAILED; the files in \(options.outDir.path) may be incomplete:\n" + problems.joined(separator: "\n"), status: 1)
    }
    print("\nsaved system.m4a, mic.m4a, timing.json in \(options.outDir.path)")
    exit(0)
}

recorder.onFailure = { message in Task { await finish(failure: message) } }
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
stopSignal.setEventHandler { Task { await finish() } }
stopSignal.resume()

let meterTimer = DispatchSource.makeTimerSource(queue: .global())
meterTimer.schedule(deadline: .now() + 5, repeating: 5)
meterTimer.setEventHandler { print(recorder.meter()) }
meterTimer.resume()

while true { try await Task.sleep(for: .seconds(3600)) }
