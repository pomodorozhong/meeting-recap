import AVFoundation
import AppKit
import CoreGraphics
import Foundation
import Observation
import RecorderCore

enum Selection: Hashable {
    /// A "New meeting" that has not started recording.
    case draft
    /// The recording in progress.
    case live
    case sample(String)
    case recording(String)
}

enum DetailTab: String, CaseIterable, Identifiable {
    case audio = "Audio", transcript = "Transcript", recap = "Recap"
    var id: String { rawValue }
}

@MainActor @Observable final class AppModel {
    enum Phase: Equatable {
        case idle
        case starting
        case recording
        case stopping
    }

    private(set) var phase: Phase = .idle
    private(set) var meter = Meter.zero
    /// Recent levels (0...1) of the two tracks, newest last, for the live waveforms.
    private(set) var liveCall: [Float] = []
    private(set) var liveMic: [Float] = []
    /// How long the call track has been silent, in seconds.
    private(set) var callSilentSeconds: Double = 0
    private(set) var recordings: [RecordingInfo] = []
    private(set) var microphones: [String] = []

    var selection: Selection? = .sample(Samples.weeklyPlanning.id)
    var tab: DetailTab = .audio
    var draftOpen = false
    var errorMessage: String?
    /// Capture system audio only from apps matching this text; empty means all system audio.
    var appFilter = ""
    /// A microphone name, or nil for the system default.
    var microphone: String?

    // Review state for the samples; it lives here so it survives switching tabs and recordings.
    var resolved: [String: [Int: Int]] = [:]
    var doneActions: Set<String> = []
    var highlighted: Set<Int> = []
    var scrollTarget: Int?

    let root: URL
    let player = Player()
    private var session: CaptureSession?
    private var meterTask: Task<Void, Never>?
    private var finishing = false

    init(root: URL = RecordingFolder.defaultRoot()) {
        self.root = root
        refresh()
    }

    func refresh() {
        recordings = RecordingLibrary.list(root: root)
        microphones = CaptureSession.microphoneNames()
        if let microphone, !microphones.contains(microphone) { self.microphone = nil }
    }

    func selectionChanged() {
        if selection != .draft { draftOpen = false }
        if case .recording = selection {} else { player.stop() }
        highlighted = []
        scrollTarget = nil
        if selection == .draft || selection == .live { tab = .audio }
    }

    func newMeeting() {
        if phase == .idle {
            draftOpen = true
            selection = .draft
        } else {
            selection = .live
        }
        tab = .audio
    }

    func rename(_ info: RecordingInfo, to title: String) {
        try? RecordingLibrary.rename(folder: info.folder, to: title)
        refresh()
    }

    // MARK: Review state for samples

    func speaker(of line: TranscriptLine, in sample: Sample) -> Int {
        resolved[sample.id]?[line.id] ?? line.speaker
    }

    func uncertainLines(in sample: Sample) -> [TranscriptLine] {
        sample.lines.filter { !$0.candidates.isEmpty && resolved[sample.id]?[$0.id] == nil }
    }

    func resolve(_ line: TranscriptLine, in sample: Sample, as speaker: Int) {
        resolved[sample.id, default: [:]][line.id] = speaker
    }

    func jump(to lines: [Int]) {
        highlighted = Set(lines)
        scrollTarget = lines.min()
        tab = .transcript
    }

    // MARK: Recording

    func start() async {
        guard phase == .idle else { return }
        errorMessage = nil
        phase = .starting
        guard await AVCaptureDevice.requestAccess(for: .audio) else {
            return fail("Microphone access is off. Allow Meeting Recap in System Settings > Privacy & Security > Microphone.")
        }
        if !CGPreflightScreenCaptureAccess() { _ = CGRequestScreenCaptureAccess() }
        do {
            let folder = try RecordingFolder.create(under: root)
            let session = try CaptureSession(folder: folder)
            session.onFailure = { [weak self] message in
                Task { @MainActor in await self?.finish(failure: message) }
            }
            let apps = appFilter.split(separator: ",").map { $0.trimmingCharacters(in: .whitespaces) }.filter { !$0.isEmpty }
            do {
                try await session.start(apps: apps, micName: microphone)
            } catch {
                try? FileManager.default.removeItem(at: folder)
                throw error
            }
            self.session = session
            finishing = false
            meter = .zero
            liveCall = []
            liveMic = []
            callSilentSeconds = 0
            phase = .recording
            draftOpen = false
            selection = .live
            meterTask = Task { [weak self] in
                while !Task.isCancelled {
                    try? await Task.sleep(for: .milliseconds(100))
                    guard let self, let session = self.session else { return }
                    self.tick(session.meter())
                }
            }
        } catch {
            fail(describe(error))
        }
    }

    func stop() async { await finish(failure: nil) }

    private func tick(_ reading: Meter) {
        meter = reading
        func level(_ peak: Float) -> Float { peak > 0 ? max(0, min(1, (20 * log10(peak) + 60) / 60)) : 0 }
        liveCall.append(level(reading.systemPeak))
        liveMic.append(level(reading.micPeak))
        if liveCall.count > 400 { liveCall.removeFirst(liveCall.count - 400) }
        if liveMic.count > 400 { liveMic.removeFirst(liveMic.count - 400) }
        callSilentSeconds = reading.systemPeak < 0.0005 ? callSilentSeconds + 0.1 : 0
    }

    /// Stops once. A failure ends the recording the same way, then shows what went wrong.
    private func finish(failure: String?) async {
        guard let session, !finishing else { return }
        finishing = true
        phase = .stopping
        meterTask?.cancel()
        let problems = await session.finish(failure: failure)
        self.session = nil
        phase = .idle
        refresh()
        selection = .recording(session.folder.lastPathComponent)
        tab = .audio
        if !problems.isEmpty {
            errorMessage = "The recording may be incomplete:\n" + problems.joined(separator: "\n")
        }
    }

    private func fail(_ message: String) {
        errorMessage = message
        phase = .idle
    }

    private func describe(_ error: Error) -> String {
        let text = (error as? CaptureError)?.description ?? error.localizedDescription
        if (error as NSError).domain == "com.apple.ScreenCaptureKit.SCStreamErrorDomain" {
            return "Could not start capture. Allow Meeting Recap in System Settings > Privacy & Security > Screen & System Audio Recording, then quit and reopen it.\n(\(text))"
        }
        return text
    }
}
