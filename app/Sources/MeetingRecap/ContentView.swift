import RecorderCore
import SwiftUI

struct ContentView: View {
    @Environment(AppModel.self) private var model
    @State private var columns: NavigationSplitViewVisibility = .all

    var body: some View {
        @Bindable var model = model
        NavigationSplitView(columnVisibility: $columns) {
            Sidebar()
                .navigationSplitViewColumnWidth(min: 220, ideal: 260, max: 340)
        } detail: {
            DetailView()
        }
        .onChange(of: model.selection) { model.selectionChanged() }
    }
}

struct Sidebar: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        @Bindable var model = model
        List(selection: $model.selection) {
            if model.phase != .idle {
                MeetingRow(title: "New meeting", subtitle: model.phase == .stopping ? "Saving…" : "Recording",
                           trailing: clock(model.meter.elapsedSeconds), recording: true)
                    .tag(Selection.live)
            } else if model.draftOpen {
                MeetingRow(title: "New meeting", subtitle: "Not started").tag(Selection.draft)
            }
            if !model.recordings.isEmpty {
                Section("Recent") {
                    ForEach(model.recordings) { info in
                        MeetingRow(title: title(of: info), subtitle: "\(whenLabel(info.date)) · \(clock(info.durationSeconds))",
                                   pill: pill(for: info))
                            .tag(Selection.recording(info.id))
                    }
                }
            }
            Section("Samples") {
                ForEach(Samples.all) { sample in
                    let toCheck = model.uncertainLines(in: sample).count
                    MeetingRow(title: sample.title, subtitle: "Sample · \(clock(sample.durationSeconds))",
                               pill: toCheck > 0 ? ("\(toCheck) to check", .warn) : ("Recap ready", .good))
                        .tag(Selection.sample(sample.id))
                }
            }
        }
        .safeAreaInset(edge: .top, spacing: 0) {
            Button { model.newMeeting() } label: {
                Label("New meeting", systemImage: "plus").frame(maxWidth: .infinity)
            }
            .buttonStyle(.glassProminent)
            .controlSize(.large)
            .keyboardShortcut("n", modifiers: .command)
            .padding(.horizontal, 12).padding(.bottom, 8)
        }
    }

    private func pill(for info: RecordingInfo) -> (String, StatusPill.Tone) {
        if !info.isComplete || info.droppedSeconds > 0.01 { return ("Audio gap", .bad) }
        return ("Not transcribed", .neutral)
    }
}

func title(of info: RecordingInfo) -> String {
    if let title = info.title { return title }
    guard let date = info.date else { return "Meeting" }
    return "Meeting at " + date.formatted(.dateTime.hour().minute())
}

func whenLabel(_ date: Date?) -> String {
    guard let date else { return "" }
    let time = date.formatted(.dateTime.hour().minute())
    if Calendar.current.isDateInToday(date) { return "Today \(time)" }
    if Calendar.current.isDateInYesterday(date) { return "Yesterday \(time)" }
    return date.formatted(.dateTime.month(.abbreviated).day()) + " " + time
}

struct MeetingRow: View {
    let title: String
    let subtitle: String
    var trailing: String?
    var recording = false
    var pill: (String, StatusPill.Tone)?

    var body: some View {
        HStack(alignment: .top) {
            VStack(alignment: .leading, spacing: 2) {
                HStack(spacing: 6) {
                    if recording { Circle().fill(.red).frame(width: 7, height: 7) }
                    Text(title).lineLimit(1)
                }
                Text(subtitle).font(.caption).foregroundStyle(.secondary)
                if let pill { StatusPill(text: pill.0, tone: pill.1).padding(.top, 2) }
            }
            Spacer(minLength: 0)
            if let trailing { Text(trailing).font(.callout.monospacedDigit()).foregroundStyle(.red) }
        }
        .padding(.vertical, 3)
    }
}
