import AVFoundation
import Foundation
import ScreenCaptureKit

/// Peak levels (0...1) since the previous reading, and how long the recording has run.
public struct Meter: Sendable {
    public var elapsedSeconds: Double
    public var systemPeak: Float
    public var micPeak: Float

    public static let zero = Meter(elapsedSeconds: 0, systemPeak: 0, micPeak: 0)

    public init(elapsedSeconds: Double, systemPeak: Float, micPeak: Float) {
        self.elapsedSeconds = elapsedSeconds
        self.systemPeak = systemPeak
        self.micPeak = micPeak
    }
}

/// Records system audio and the microphone to `system.m4a` and `mic.m4a` (Apple Lossless, 48 kHz) in one folder,
/// plus `timing.json`. Both files share one timeline that starts at the first audio buffer from either stream.
public final class CaptureSession: NSObject, SCStreamOutput, SCStreamDelegate, @unchecked Sendable {
    public let folder: URL
    let system: CaptureTrack
    let mic: CaptureTrack
    let queue = DispatchQueue(label: "meeting-recap.capture")
    var sessionStart: CMTime?
    var stream: SCStream?
    var reportedFailure = false
    /// Called once, on the capture queue, when a track can no longer be written or the stream stops.
    public var onFailure: @Sendable (String) -> Void = { _ in }

    /// `folder` must exist already; make it with `RecordingFolder.create(under:)`.
    public init(folder: URL) throws {
        self.folder = folder
        system = try CaptureTrack(name: "system", url: folder.appendingPathComponent("system.m4a"), channels: 2)
        mic = try CaptureTrack(name: "mic", url: folder.appendingPathComponent("mic.m4a"), channels: 1)
    }

    /// Names of the microphones `start(micName:)` can match.
    public static func microphoneNames() -> [String] {
        AVCaptureDevice.DiscoverySession(deviceTypes: [.microphone, .external], mediaType: .audio, position: .unspecified)
            .devices.map(\.localizedName)
    }

    /// `apps` limits system audio to apps whose name or bundle ID contains one of the strings; empty captures all
    /// system audio. `micName` picks the input device by name; nil uses the system default.
    public func start(apps: [String] = [], micName: String? = nil) async throws {
        let content = try await SCShareableContent.excludingDesktopWindows(false, onScreenWindowsOnly: false)
        guard let display = content.displays.first else { throw CaptureError("no display found") }
        let filter: SCContentFilter
        if apps.isEmpty {
            filter = SCContentFilter(display: display, excludingApplications: [], exceptingWindows: [])
        } else {
            let chosen = content.applications.filter { app in
                apps.contains { app.applicationName.localizedCaseInsensitiveContains($0) || app.bundleIdentifier.localizedCaseInsensitiveContains($0) }
            }
            guard !chosen.isEmpty else { throw CaptureError("no running app matches \(apps.joined(separator: ", "))") }
            filter = SCContentFilter(display: display, including: chosen, exceptingWindows: [])
        }

        let config = SCStreamConfiguration()
        config.capturesAudio = true
        config.captureMicrophone = true
        // Must stay off: it drops audio from the whole app that launched the capture.
        config.excludesCurrentProcessAudio = false
        if let micName {
            let devices = AVCaptureDevice.DiscoverySession(
                deviceTypes: [.microphone, .external], mediaType: .audio, position: .unspecified
            ).devices
            guard let device = devices.first(where: { $0.localizedName.localizedCaseInsensitiveContains(micName) }) else {
                throw CaptureError("no microphone matches \"\(micName)\"")
            }
            config.microphoneCaptureDeviceID = device.uniqueID
        }
        config.sampleRate = captureSampleRate
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

    public func stream(_ stream: SCStream, didOutputSampleBuffer buffer: CMSampleBuffer, of type: SCStreamOutputType) {
        guard buffer.isValid, buffer.numSamples > 0 else { return }
        let track: CaptureTrack
        switch type {
        case .audio: track = system
        case .microphone: track = mic
        default: return
        }
        if sessionStart == nil { sessionStart = buffer.presentationTimeStamp }
        track.append(buffer, sessionStart: sessionStart!)
        if let error = track.error, !reportedFailure {
            reportedFailure = true
            onFailure("\(track.name).m4a: \(error)")
        }
    }

    public func stream(_ stream: SCStream, didStopWithError error: Error) {
        guard !reportedFailure else { return }
        reportedFailure = true
        onFailure("capture stopped: \(error.localizedDescription)")
    }

    /// Levels since the previous call, for a live meter.
    public func meter() -> Meter {
        queue.sync {
            let end = system.lastEnd == .zero ? mic.lastEnd : max(system.lastEnd, mic.lastEnd)
            let seconds = sessionStart.map { (end - $0).seconds } ?? 0
            defer { system.peak = 0; mic.peak = 0 }
            return Meter(elapsedSeconds: max(0, seconds), systemPeak: system.peak, micPeak: mic.peak)
        }
    }

    /// Stops capture, finishes both files, and writes `timing.json`. Returns what went wrong; empty means both
    /// files and `timing.json` are complete.
    public func finish(failure: String? = nil) async -> [String] {
        var problems = failure.map { [$0] } ?? []
        try? await stream?.stopCapture()
        stream = nil
        // A track whose input went quiet before the stop would otherwise end early; both end where the later one does.
        queue.sync {
            let end = max(system.lastEnd, mic.lastEnd)
            for track in [system, mic] { track.pad(to: end) }
        }
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
        do {
            let data = try JSONSerialization.data(withJSONObject: timing(), options: [.prettyPrinted, .sortedKeys])
            try data.write(to: folder.appendingPathComponent("timing.json"))
        } catch {
            problems.append("timing.json: \(error.localizedDescription)")
        }
        return problems
    }

    func timing() -> [String: Any] {
        var result: [String: Any] = ["sample_rate": captureSampleRate]
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
