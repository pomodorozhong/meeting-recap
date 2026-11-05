import Foundation

// Mock content. Nothing here comes from a real call or from the pipeline: these are two invented meetings shaped like
// what the pipeline is expected to produce (labeled lines with times, one line whose speaker is unsure, and a recap
// whose every item cites transcript lines). Replace this file with the pipeline's output once one is chosen.

struct TranscriptLine: Identifiable, Hashable {
    let id: Int
    let start: Double
    let end: Double
    /// Index into `Palette.speakers`; the best guess when `candidates` is not empty.
    let speaker: Int
    let text: String
    /// Speakers the line could belong to when the label is unsure; empty when it is not.
    var candidates: [Int] = []
}

struct RecapItem: Identifiable, Hashable {
    let id: Int
    let text: String
    /// Transcript line ids that support this item.
    let cites: [Int]
    var speaker: Int?
    var due: String?
}

struct Recap {
    let summary: [RecapItem]
    let decisions: [RecapItem]
    let actions: [RecapItem]
}

/// What a mock screenshot shows; `ShotThumb` draws a stand-in for each kind. No real screen content is used.
enum ShotKind { case slides, dashboard, document, chat, calendar, ticket }

/// A screenshot taken during the meeting, placed on the timeline.
struct Shot: Identifiable, Hashable {
    let id: Int
    let time: Double
    let app: String
    /// What the pipeline is expected to say about the screenshot.
    let caption: String
    let kind: ShotKind
}

struct Sample: Identifiable {
    let id: String
    let title: String
    let whenLabel: String
    let durationSeconds: Double
    let lines: [TranscriptLine]
    let shots: [Shot]
    let recap: Recap

    var speakerCount: Int { (lines.map(\.speaker).max() ?? 0) + 1 }
}

enum Samples {
    static let all = [weeklyPlanning, customerCall]

    private static func lines(_ rows: [(Double, Double, Int, String, [Int])]) -> [TranscriptLine] {
        rows.enumerated().map {
            TranscriptLine(id: $0.offset, start: $0.element.0, end: $0.element.1, speaker: $0.element.2,
                           text: $0.element.3, candidates: $0.element.4)
        }
    }

    static let weeklyPlanning = Sample(
        id: "sample-weekly-planning",
        title: "Weekly planning",
        whenLabel: "Sample",
        durationSeconds: 185,
        lines: lines([
            (0, 13, 0, "Thanks for joining. We need to settle the launch date for the pilot and who covers onboarding.", []),
            (14, 30, 1, "From the engineering side, the pilot build is stable. The open item is the export bug, which I can fix this week.", []),
            (31, 46, 2, "Support can handle onboarding, but we need the guide finished before the first customers arrive.", []),
            (47, 51, 0, "Who owns the guide?", []),
            (52, 65, 2, "I can draft it, but I need screenshots from the final build.", []),
            (66, 80, 1, "I'll send screenshots as soon as the export fix is merged. Probably Thursday.", []),
            (83, 95, 0, "Then the launch date. Is the fifteenth realistic, or should we leave a buffer?", []),
            (97, 111, 2, "Customers start arriving on the fifteenth, so the guide must be done by the twelfth.", []),
            (113, 129, 1, "The twelfth works if the fix lands Thursday. If it slips, we move everything by a week.", []),
            (131, 146, 0, "Okay. We commit to the fifteenth, and we decide on Friday whether to slip.", []),
            (148, 160, 2, "Agreed. I'll also set up a shared inbox for pilot questions.", [2, 1]),
            (163, 178, 0, "Good. Last thing: I'll tell the account team the date once Friday's check is done.", []),
        ]),
        shots: [
            Shot(id: 0, time: 4, app: "Slides", caption: "Slide titled “Pilot launch”, listing the date, owners and open risks.", kind: .slides),
            Shot(id: 1, time: 22, app: "Dashboard", caption: "Build status chart with one failing export check.", kind: .dashboard),
            Shot(id: 2, time: 57, app: "Docs", caption: "Draft of the onboarding guide with empty screenshot placeholders.", kind: .document),
            Shot(id: 3, time: 88, app: "Calendar", caption: "Month view with the fifteenth and the twelfth marked.", kind: .calendar),
            Shot(id: 4, time: 150, app: "Chat", caption: "Team channel with a request for a shared inbox.", kind: .chat),
        ],
        recap: Recap(
            summary: [
                RecapItem(id: 0, text: "The pilot build is stable except for an export bug that engineering expects to fix this week.", cites: [1]),
                RecapItem(id: 1, text: "Onboarding depends on a guide that needs screenshots from the final build.", cites: [2, 4]),
                RecapItem(id: 2, text: "The team weighed launching on the fifteenth against leaving a buffer.", cites: [6, 7]),
            ],
            decisions: [
                RecapItem(id: 3, text: "Launch on the fifteenth, with a Friday check on whether to slip.", cites: [9]),
                RecapItem(id: 4, text: "If the export fix slips past Thursday, move everything by a week.", cites: [8]),
            ],
            actions: [
                RecapItem(id: 5, text: "Fix the export bug and send screenshots", cites: [1, 5], speaker: 1, due: "Thursday"),
                RecapItem(id: 6, text: "Draft the onboarding guide and set up a shared inbox for pilot questions", cites: [4, 7, 10], speaker: 2, due: "the twelfth"),
                RecapItem(id: 7, text: "Tell the account team the launch date", cites: [11], speaker: 0, due: "after Friday's check"),
            ]
        )
    )

    static let customerCall = Sample(
        id: "sample-customer-call",
        title: "Customer call",
        whenLabel: "Sample",
        durationSeconds: 130,
        lines: lines([
            (0, 10, 1, "Hi, our exports stopped working after the update and I need the monthly file by Friday.", []),
            (11, 22, 0, "Thanks for letting us know. Which version are you on, and what error do you see?", []),
            (23, 35, 1, "Version 2.4. It says the file is too large and stops at about eighty percent.", []),
            (36, 52, 0, "That's a known issue in 2.4. A fix is coming in 2.5 next Tuesday. Until then I can split the export by region.", []),
            (53, 64, 1, "Splitting works for me, but can you send me the steps?", []),
            (65, 80, 0, "Yes, I'll email the steps today. I'll also check back on Wednesday to confirm the new version works.", []),
            (81, 92, 1, "Great. Can we also add two more people to our account?", []),
            (93, 110, 0, "Of course. Send me their names and I'll add them this afternoon.", []),
            (111, 125, 1, "Perfect, thank you.", []),
        ]),
        shots: [
            Shot(id: 0, time: 14, app: "Support", caption: "Ticket for a failed export on version 2.4, status “Open”.", kind: .ticket),
            Shot(id: 1, time: 42, app: "Docs", caption: "Release notes listing the export fix for version 2.5.", kind: .document),
            Shot(id: 2, time: 96, app: "Dashboard", caption: "Account page with two free seats.", kind: .dashboard),
        ],
        recap: Recap(
            summary: [
                RecapItem(id: 0, text: "The customer's monthly export fails at about eighty percent on version 2.4; the fix ships in 2.5 next Tuesday.", cites: [2, 3]),
                RecapItem(id: 1, text: "The customer also asked to add two people to their account.", cites: [6, 7]),
            ],
            decisions: [
                RecapItem(id: 2, text: "Split the export by region until version 2.5 is available.", cites: [3, 4]),
            ],
            actions: [
                RecapItem(id: 3, text: "Email the steps for splitting the export", cites: [5], speaker: 0, due: "today"),
                RecapItem(id: 4, text: "Check back to confirm the new version works", cites: [5], speaker: 0, due: "Wednesday"),
                RecapItem(id: 5, text: "Send the names of the two new people", cites: [7], speaker: 1, due: nil),
                RecapItem(id: 6, text: "Add the two people to the account", cites: [6, 7], speaker: 0, due: "this afternoon"),
            ]
        )
    )
}
