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
    /// Levels (0...1) of the two tracks every 0.1 s since the recording started, for the live timeline.
    private(set) var liveCall: [Float] = []
    private(set) var liveMic: [Float] = []
    /// How long the call track has been silent, in seconds.
    private(set) var callSilentSeconds: Double = 0
    /// Notes typed during the recording in progress; the last one has no end while it is being typed.
    private(set) var liveNotes: [Note] = []
    /// Who talked while recording, settled half a second at a time: each half second is decided once, when it ends,
    /// and never changes, so the live timeline only grows.
    private(set) var liveTurns: [TurnSpan] = []
    /// True while a demo recording runs: invented levels, no capture, nothing saved.
    private(set) var isDemo = false
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
            liveNotes = []
            liveTurns = []
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

    func stop() async {
        if isDemo { return stopDemo() }
        await finish(failure: nil)
    }

    // MARK: Demo recording
    // The live screen without capture, so its design can be seen without the recording permissions. Levels are
    // invented (you and the call taking turns) and notes are kept only in memory.

    func startDemo() {
        guard phase == .idle else { return }
        errorMessage = nil
        meter = .zero
        liveCall = []
        liveMic = []
        liveNotes = []
        liveTurns = []
        callSilentSeconds = 0
        isDemo = true
        phase = .recording
        draftOpen = false
        selection = .live
        tab = .meeting
        meterTask = Task { [weak self] in
            while !Task.isCancelled {
                try? await Task.sleep(for: .milliseconds(100))
                guard let self, self.isDemo else { return }
                self.tick(Self.demoReading(at: self.meter.elapsedSeconds + 0.1))
            }
        }
    }

    private func stopDemo() {
        meterTask?.cancel()
        isDemo = false
        phase = .idle
        draftOpen = true
        selection = .draft
    }

    /// Invented peaks for second `time` of a demo: in each 30 s you talk, the call answers, you reply, the call goes on.
    static func demoReading(at time: Double) -> Meter {
        let second = time.truncatingRemainder(dividingBy: 30)
        let you = (0.5..<6).contains(second) || (19..<22).contains(second)
        let call = (7..<17.5).contains(second) || (23..<29).contains(second)
        func peak(_ talking: Bool, _ seed: Double) -> Float {
            let noise = Float(abs(sin(time * 12.9898 + seed) * 43758.5453).truncatingRemainder(dividingBy: 1))
            // About -26 to -4 dB while talking; room noise near -55 dB otherwise.
            return talking ? pow(10, (-26 + 22 * noise) / 20) : pow(10, (-58 + 6 * noise) / 20)
        }
        return Meter(elapsedSeconds: time, systemPeak: peak(call, 1.7), micPeak: peak(you, 5.3))
    }

    // MARK: Notes while recording
    // A line starts at its first character and ends on Return, both on the recording's timeline (the timer shown on
    // screen). Editing a finished line keeps its times. Every change is written to notes.txt at once.

    /// The line being typed: its text changed to `text`.
    func typeNote(_ text: String) {
        guard phase == .recording else { return }
        if let last = liveNotes.indices.last, liveNotes[last].end == nil {
            if text.isEmpty { liveNotes.removeLast() } else { liveNotes[last].text = text }
        } else if !text.isEmpty {
            liveNotes.append(Note(id: (liveNotes.map(\.id).max() ?? -1) + 1, start: meter.elapsedSeconds, end: nil, text: text))
        }
        saveNotes()
    }

    /// Return: ends the line being typed.
    func finishNote() {
        guard let last = liveNotes.indices.last, liveNotes[last].end == nil else { return }
        if liveNotes[last].text.trimmingCharacters(in: .whitespaces).isEmpty {
            liveNotes.removeLast()
        } else {
            liveNotes[last].end = max(meter.elapsedSeconds, liveNotes[last].start)
        }
        saveNotes()
    }

    /// Changes a finished line's text and keeps its times. An emptied line is removed.
    func editNote(_ id: Int, to text: String) {
        guard let index = liveNotes.firstIndex(where: { $0.id == id }) else { return }
        if text.trimmingCharacters(in: .whitespaces).isEmpty { liveNotes.remove(at: index) } else { liveNotes[index].text = text }
        saveNotes()
    }

    private func saveNotes() {
        guard let folder = session?.folder else { return }
        do { try NotesFile.write(liveNotes, to: folder) } catch { errorMessage = "Could not save notes: \(error.localizedDescription)" }
    }

    private func tick(_ reading: Meter) {
        meter = reading
        func level(_ peak: Float) -> Float { peak > 0 ? max(0, min(1, (20 * log10(peak) + 60) / 60)) : 0 }
        liveCall.append(level(reading.systemPeak))
        liveMic.append(level(reading.micPeak))
        // Levels come every 0.1 s; each full half second becomes part of the turns once.
        if liveCall.count % 5 == 0 {
            let half = liveCall.count / 5 - 1
            Waveforms.extend(&liveTurns, who: Waveforms.who(call: liveCall.suffix(5).max() ?? 0, mic: liveMic.suffix(5).max() ?? 0),
                             from: Double(half) * 0.5, length: 0.5)
        }
        callSilentSeconds = reading.systemPeak < 0.0005 ? callSilentSeconds + 0.1 : 0
    }

    /// Stops once. A failure ends the recording the same way, then shows what went wrong.
    private func finish(failure: String?) async {
        guard let session, !finishing else { return }
        finishing = true
        phase = .stopping
        meterTask?.cancel()
        // A line still being typed ends when the recording does.
        if let last = liveNotes.indices.last, liveNotes[last].end == nil {
            liveNotes[last].end = max(meter.elapsedSeconds, liveNotes[last].start)
            saveNotes()
        }
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
