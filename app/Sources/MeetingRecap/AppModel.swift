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

/// An app that can be picked as the source of the Call track.
struct AppChoice: Identifiable, Hashable {
    /// The bundle ID.
    let id: String
    let name: String

    /// Apps people take calls in, listed first.
    private static let callApps = ["teams", "zoom", "meet", "chrome", "slack", "webex", "facetime", "discord", "safari", "firefox", "edge", "arc"]

    static func running() -> [AppChoice] {
        let own = Bundle.main.bundleIdentifier
        let apps = NSWorkspace.shared.runningApplications.compactMap { app -> AppChoice? in
            guard app.activationPolicy == .regular, let id = app.bundleIdentifier, id != own,
                  let name = app.localizedName else { return nil }
            return AppChoice(id: id, name: name)
        }
        func rank(_ app: AppChoice) -> Int {
            let key = (app.name + " " + app.id).lowercased()
            return callApps.firstIndex { key.contains($0) } ?? callApps.count
        }
        return Array(Set(apps)).sorted { (rank($0), $0.name.lowercased()) < (rank($1), $1.name.lowercased()) }
    }
}

enum DetailTab: String, CaseIterable, Identifiable {
    case meeting = "Meeting", recap = "Recap"
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
    private(set) var samplePosition: Double = 0
    private(set) var samplePlaying = false
    private var sampleTask: Task<Void, Never>?

    var selection: Selection? = .sample(Samples.weeklyPlanning.id)
    var tab: DetailTab = .meeting
    var draftOpen = false
    var errorMessage: String?
    /// The bundle ID of the one app whose sound goes in the Call track, or nil for all sound on this Mac.
    var callApp: String?
    private(set) var runningApps: [AppChoice] = []
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
        refreshApps()
    }

    /// The apps running now, call apps first; needs no permission.
    func refreshApps() {
        runningApps = AppChoice.running()
        if let callApp, !runningApps.contains(where: { $0.id == callApp }) { self.callApp = nil }
    }

    var callAppName: String? { runningApps.first { $0.id == callApp }?.name }

    func selectionChanged() {
        if selection != .draft { draftOpen = false }
        if case .recording = selection {} else { player.stop() }
        highlighted = []
        scrollTarget = nil
        stopSample()
        samplePosition = 0
        if selection == .draft || selection == .live { tab = .meeting }
    }

    // MARK: Sample playback
    // A sample has no audio, so its playhead is simulated: it runs in real time and can be moved, so the design
    // can be judged with something playing.

    func toggleSample(duration: Double) {
        if samplePlaying { stopSample(); return }
        if samplePosition >= duration - 0.1 { samplePosition = 0 }
        samplePlaying = true
        sampleTask = Task { [weak self] in
            while !Task.isCancelled {
                try? await Task.sleep(for: .milliseconds(100))
                guard let self, self.samplePlaying else { return }
                self.samplePosition += 0.1
                if self.samplePosition >= duration {
                    self.samplePosition = duration
                    self.stopSample()
                }
            }
        }
    }

    func stopSample() {
        samplePlaying = false
        sampleTask?.cancel()
        sampleTask = nil
    }

    func seekSample(to seconds: Double) { samplePosition = max(0, seconds) }

    func newMeeting() {
        if phase == .idle {
            draftOpen = true
            selection = .draft
        } else {
            selection = .live
        }
        tab = .meeting
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
        tab = .meeting
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
            let apps = callApp.map { [$0] } ?? []
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
        tab = .meeting
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
