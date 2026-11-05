import Foundation

public struct CaptureError: Error, CustomStringConvertible, LocalizedError {
    public let description: String
    public init(_ description: String) { self.description = description }
    public var errorDescription: String? { description }
}

/// Where recordings go. Recordings are private, so a folder inside a Git checkout is refused.
public enum RecordingFolder {
    /// `~/Library/Application Support/MeetingRecap/Recordings`, outside any checkout.
    public static func defaultRoot() -> URL {
        let support = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        return support.appendingPathComponent("MeetingRecap").appendingPathComponent("Recordings")
    }

    /// A new folder name from the local date and time, such as `2026-11-05T14-30-00`.
    public static func name(for date: Date, timeZone: TimeZone = .current) -> String {
        let format = DateFormatter()
        format.locale = Locale(identifier: "en_US_POSIX")
        format.calendar = Calendar(identifier: .gregorian)
        format.timeZone = timeZone
        format.dateFormat = "yyyy-MM-dd'T'HH-mm-ss"
        return format.string(from: date)
    }

    /// The folder with symlinks resolved. Throws when it is inside a Git checkout (a worktree's `.git` is a file)
    /// or already holds files.
    public static func validate(_ url: URL) throws -> URL {
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
                throw CaptureError("refusing to record into \(resolved.path): it is inside the Git checkout at \(folder.path)")
            }
            if folder.path == "/" { break }
            folder.deleteLastPathComponent()
        }
        if let contents = try? files.contentsOfDirectory(atPath: resolved.path), !contents.isEmpty {
            throw CaptureError("refusing to record into \(resolved.path): it already holds files")
        }
        return resolved
    }

    /// Creates and returns a fresh recording folder under `root`.
    public static func create(under root: URL, now: Date = Date()) throws -> URL {
        let folder = try validate(root.appendingPathComponent(name(for: now)))
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
        return folder
    }
}

/// What the app shows about a finished recording, read from its `timing.json`.
public struct RecordingInfo: Identifiable, Hashable, Sendable {
    public var id: String { folder.lastPathComponent }
    public let folder: URL
    public let durationSeconds: Double
    /// Empty when both files were written completely.
    public let problems: [String]
    public let silenceFilledSeconds: Double
    public let droppedSeconds: Double

    public var isComplete: Bool { problems.isEmpty }
}

public enum RecordingLibrary {
    /// Recordings under `root`, newest first. A folder without a readable `timing.json` is reported as incomplete.
    public static func list(root: URL) -> [RecordingInfo] {
        let files = FileManager.default
        let names = (try? files.contentsOfDirectory(atPath: root.path)) ?? []
        return names.sorted(by: >).compactMap { name in
            var isDirectory: ObjCBool = false
            let folder = root.appendingPathComponent(name)
            guard files.fileExists(atPath: folder.path, isDirectory: &isDirectory), isDirectory.boolValue else { return nil }
            return read(folder: folder)
        }
    }

    static func read(folder: URL) -> RecordingInfo {
        func incomplete(_ why: String) -> RecordingInfo {
            RecordingInfo(folder: folder, durationSeconds: 0, problems: [why], silenceFilledSeconds: 0, droppedSeconds: 0)
        }
        guard let data = try? Data(contentsOf: folder.appendingPathComponent("timing.json")),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
        else { return incomplete("timing.json is missing, so the recording did not finish") }
        var duration = 0.0, silence = 0.0, dropped = 0.0
        var problems: [String] = []
        for track in ["system", "mic"] {
            guard let entry = json[track] as? [String: Any] else { problems.append("\(track): no timing"); continue }
            duration = max(duration, entry["duration_seconds"] as? Double ?? 0)
            silence += entry["silence_filled_seconds"] as? Double ?? 0
            dropped += entry["dropped_seconds"] as? Double ?? 0
            if let error = entry["error"] as? String { problems.append("\(track): \(error)") }
            else if entry["written"] as? Bool != true { problems.append("\(track): not written completely") }
        }
        return RecordingInfo(folder: folder, durationSeconds: duration, problems: problems,
                             silenceFilledSeconds: silence, droppedSeconds: dropped)
    }
}
