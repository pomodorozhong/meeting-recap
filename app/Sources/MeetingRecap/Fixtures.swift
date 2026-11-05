import Foundation

// Mock content. Nothing here comes from a real call or from the pipeline: it is an invented planning call between
// Speaker A, B and C, shaped like what the pipeline is expected to produce (labeled lines with times, and a recap
// whose every item cites transcript lines). Replace this file with the pipeline's output once one is chosen.

struct TranscriptLine: Identifiable, Hashable {
    let id: Int
    let start: Double
    let speaker: String
    let text: String
}

struct RecapItem: Identifiable, Hashable {
    let id: Int
    let text: String
    /// Transcript line ids that support this item.
    let cites: [Int]
}

struct Recap {
    let summary: [RecapItem]
    let decisions: [RecapItem]
    let actions: [RecapItem]
}

enum Fixtures {
    static let title = "Sample call (mock)"
    static let durationSeconds: Double = 412

    static let transcript: [TranscriptLine] = [
        (0, "Speaker A", "Thanks for joining. We need to settle the launch date for the pilot and who covers onboarding."),
        (14, "Speaker B", "From the engineering side, the pilot build is stable. The open item is the export bug, which I can fix this week."),
        (31, "Speaker C", "Support can handle onboarding, but we need the guide finished before the first customers arrive."),
        (47, "Speaker A", "Who owns the guide?"),
        (52, "Speaker C", "I can draft it, but I need screenshots from the final build."),
        (66, "Speaker B", "I'll send screenshots as soon as the export fix is merged. Probably Thursday."),
        (83, "Speaker A", "Then the launch date. Is the fifteenth realistic, or should we leave a buffer?"),
        (97, "Speaker C", "Customers start arriving on the fifteenth, so the guide must be done by the twelfth."),
        (113, "Speaker B", "The twelfth works if the fix lands Thursday. If it slips, we move everything by a week."),
        (131, "Speaker A", "Okay. We commit to the fifteenth, and we decide on Friday whether to slip."),
        (148, "Speaker C", "Agreed. I'll also set up a shared inbox for pilot questions."),
        (163, "Speaker A", "Good. Last thing: I'll tell the account team the date once Friday's check is done."),
    ].enumerated().map { TranscriptLine(id: $0.offset, start: Double($0.element.0), speaker: $0.element.1, text: $0.element.2) }

    static let recap = Recap(
        summary: [
            RecapItem(id: 0, text: "The pilot build is stable except for an export bug that engineering expects to fix this week.", cites: [1]),
            RecapItem(id: 1, text: "Onboarding depends on a guide that needs screenshots from the final build.", cites: [2, 4]),
            RecapItem(id: 2, text: "The team compared the fifteenth as a launch date against leaving a buffer.", cites: [6, 7]),
        ],
        decisions: [
            RecapItem(id: 3, text: "Commit to launching on the fifteenth, with a Friday check on whether to slip.", cites: [9]),
            RecapItem(id: 4, text: "If the export fix slips past Thursday, move everything by a week.", cites: [8]),
        ],
        actions: [
            RecapItem(id: 5, text: "Speaker B: fix the export bug and send screenshots, expected Thursday.", cites: [1, 5]),
            RecapItem(id: 6, text: "Speaker C: draft the onboarding guide by the twelfth and set up a shared inbox for pilot questions.", cites: [4, 7, 10]),
            RecapItem(id: 7, text: "Speaker A: tell the account team the launch date after Friday's check.", cites: [11]),
        ]
    )
}
