import Foundation

/// One line a person typed during a recording. Times are seconds on the recording's own timeline, the one
/// `timing.json` and both audio files share, not the wall clock.
public struct Note: Identifiable, Hashable, Sendable {
    public let id: Int
    /// When the first character of the line was typed.
    public var start: Double
    /// When the person pressed Return; nil while the line is still being typed.
    public var end: Double?
    public var text: String

    public init(id: Int, start: Double, end: Double?, text: String) {
        self.id = id
        self.start = start
        self.end = end
        self.text = text
    }
}

/// `notes.txt` in a recording's folder: a header, then one note per line as `start<TAB>end<TAB>text`, with times in
/// seconds. It is rewritten as the person types, so a crash or a failed recording keeps what was typed.
public enum NotesFile {
    public static let name = "notes.txt"

    static let header = """
        # Notes typed during this recording, one per line: start and end in seconds on the recording's timeline
        # (the same one as timing.json and the audio files), then the note. An empty end means the line was not finished.
        """

    public static func format(_ notes: [Note]) -> String {
        let rows = notes.map { note in
            let text = note.text.replacingOccurrences(of: "\t", with: " ")
                .replacingOccurrences(of: "\r", with: " ").replacingOccurrences(of: "\n", with: " ")
            return "\(seconds(note.start))\t\(note.end.map(seconds) ?? "")\t\(text)"
        }
        return ([header] + rows).joined(separator: "\n") + "\n"
    }

    /// Notes in file order. Comment lines and lines that don't parse are skipped.
    public static func parse(_ contents: String) -> [Note] {
        var notes: [Note] = []
        for line in contents.split(separator: "\n", omittingEmptySubsequences: true) where !line.hasPrefix("#") {
            let fields = line.split(separator: "\t", maxSplits: 2, omittingEmptySubsequences: false)
            guard fields.count == 3, let start = Double(fields[0]) else { continue }
            let end = Double(fields[1])
            notes.append(Note(id: notes.count, start: start, end: end, text: String(fields[2])))
        }
        return notes
    }

    public static func write(_ notes: [Note], to folder: URL) throws {
        try format(notes).write(to: folder.appendingPathComponent(name), atomically: true, encoding: .utf8)
    }

    /// The folder's notes, or none when it has no `notes.txt`.
    public static func read(folder: URL) -> [Note] {
        guard let contents = try? String(contentsOf: folder.appendingPathComponent(name), encoding: .utf8) else { return [] }
        return parse(contents)
    }

    private static func seconds(_ value: Double) -> String { String(format: "%.1f", value) }
}
