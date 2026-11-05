import AVFoundation
import CoreGraphics
import Foundation
import Observation
import RecorderCore

enum Selection: Hashable {
    case sample
    case recording(String)
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
    private(set) var recordings: [RecordingInfo] = []
    private(set) var microphones: [String] = []
    var selection: Selection? = .sample
    var errorMessage: String?
    /// Capture system audio only from apps matching this text; empty means all system audio.
    var appFilter = ""
    /// A microphone name, or nil for the system default.
    var microphone: String?

    let root: URL
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

    func recording(for selection: Selection?) -> RecordingInfo? {
        guard case .recording(let id) = selection else { return nil }
        return recordings.first { $0.id == id }
    }

    func start() async {
        guard phase == .idle else { return }
        errorMessage = nil
        phase = .starting
        guard await AVCaptureDevice.requestAccess(for: .audio) else {
            return fail("Microphone access is off. Allow MeetingRecap in System Settings > Privacy & Security > Microphone.")
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
            meter = Meter.zero
            phase = .recording
            meterTask = Task { [weak self] in
                while !Task.isCancelled {
                    try? await Task.sleep(for: .milliseconds(100))
                    guard let self, let session = self.session else { return }
                    self.meter = session.meter()
                }
            }
        } catch {
            fail(describe(error))
        }
    }

    func stop() async { await finish(failure: nil) }

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
            return "Could not start capture. Allow MeetingRecap in System Settings > Privacy & Security > Screen & System Audio Recording, then quit and reopen it.\n(\(text))"
        }
        return text
    }
}
