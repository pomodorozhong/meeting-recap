import AppKit
import RecorderCore
import SwiftUI

/// Before recording starts: pick the sources, then start.
struct DraftSetup: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        @Bindable var model = model
        VStack(alignment: .leading, spacing: 18) {
            VStack(alignment: .leading, spacing: 18) {
                VStack(alignment: .leading, spacing: 4) {
                    Text("You").font(.headline)
                    Picker("Microphone", selection: $model.microphone) {
                        Text("System default microphone").tag(String?.none)
                        ForEach(model.microphones, id: \.self) { Text($0).tag(String?.some($0)) }
                    }
                    .labelsHidden()
                    Text("Your microphone is saved as its own track.").font(.caption).foregroundStyle(.secondary)
                }
                VStack(alignment: .leading, spacing: 4) {
                    Text("The call").font(.headline)
                    Picker("Record the call from", selection: $model.callApp) {
                        Text("Everything on this Mac").tag(String?.none)
                        Divider()
                        ForEach(model.runningApps) { Text($0.name).tag(String?.some($0.id)) }
                    }
                    .labelsHidden()
                    Text(model.callAppName.map { "Only \($0)'s sound goes in the Call track. Music and alerts from other apps are left out." }
                         ?? "All sound this Mac plays goes in the Call track, including music and alerts. Pick the app you're calling in to leave those out.")
                        .font(.caption).foregroundStyle(.secondary)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .glassCard()
            .onAppear { model.refreshApps() }

            VStack(spacing: 10) {
                Button { Task { await model.start() } } label: {
                    HStack(spacing: 8) {
                        if model.phase == .starting { ProgressView().controlSize(.small) }
                        Label("Start recording", systemImage: "record.circle")
                    }
                    .frame(maxWidth: .infinity)
                }
                .buttonStyle(.glassProminent).tint(.red).controlSize(.extraLarge)
                .keyboardShortcut("r", modifiers: .command)
                .disabled(model.phase == .starting)
                Text("Wear headphones, or the call leaks into your microphone.")
                    .font(.callout).foregroundStyle(.secondary)
            }
            Spacer()
        }
        .frame(maxWidth: 520)
    }
}

/// While recording: the same timeline as afterwards, growing as the recording does, then your notes, with the box
/// for the next note at the bottom.
struct RecorderPanel: View {
    @Environment(AppModel.self) private var model
    @State private var draft = ""
    @FocusState private var typing: Bool
    /// How much of the recording the timeline shows at once while recording.
    static let window: Double = 120

    var body: some View {
        let elapsed = model.meter.elapsedSeconds
        // A fixed window, so a turn keeps its size however long the meeting runs. The turns themselves are settled
        // as the recording goes (see `AppModel.liveTurns`), so the window only slides them along.
        let start = max(0, elapsed - Self.window)
        let turns = model.liveTurns.filter { $0.end > start }
        let finished = model.liveNotes.filter { $0.end != nil }
        VStack(alignment: .leading, spacing: 12) {
            PlayerCard(
                state: PlayerState(position: elapsed, duration: elapsed, isPlaying: false, toggle: {}),
                live: LiveControls(elapsed: elapsed, stopping: model.phase == .stopping, stopLabel: model.isDemo ? "Stop demo" : "Stop and save",
                                   windowStart: start, windowLength: Self.window, allTurns: model.liveTurns, stop: { Task { await model.stop() } }),
                turns: turns, notes: model.liveNotes, seek: { _ in }
            )

            if model.callSilentSeconds >= 30 {
                Label("The call track has been silent for \(Int(model.callSilentSeconds)) seconds. Check that the call is playing through this Mac.",
                      systemImage: "exclamationmark.triangle.fill")
                    .foregroundStyle(.orange)
                    .glassCard(radius: 16, padding: 12)
            }

            ScrollViewReader { proxy in
                ScrollView {
                    VStack(alignment: .leading, spacing: 6) {
                        NotesFeed(notes: finished, onEdit: { model.editNote($0.id, to: $1) }) { _ in }
                        if finished.isEmpty {
                            Text((model.isDemo ? "Demo: nothing is recorded or saved." : "Saving to this Mac.") + " Type notes below as the meeting goes; each line gets its time on the recording. The transcript and recap are made after you stop.")
                                .font(.callout).foregroundStyle(.secondary)
                        }
                        Color.clear.frame(height: 1).id("end")
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
                .scrollIndicators(.hidden)
                .onChange(of: finished.count) { withAnimation { proxy.scrollTo("end", anchor: .bottom) } }
            }

            HStack(spacing: 10) {
                Image(systemName: "pencil").foregroundStyle(Palette.note)
                TextField("Type a note, then press Return", text: $draft)
                    .textFieldStyle(.plain)
                    .focused($typing)
                    .onChange(of: draft) { model.typeNote(draft) }
                    .onSubmit {
                        model.finishNote()
                        draft = ""
                        typing = true
                    }
            }
            .padding(.horizontal, 14).padding(.vertical, 10)
            .glassEffect(.regular, in: .capsule)
        }
        .onAppear { typing = true }
    }
}

struct LaneRow<Content: View>: View {
    let label: String
    @ViewBuilder var content: Content

    var body: some View {
        HStack(spacing: 10) {
            Text(label).font(.callout).foregroundStyle(.secondary).lineLimit(1).fixedSize().frame(width: 64, alignment: .leading)
            content
        }
    }
}

struct TalkTime: View {
    @Environment(AppModel.self) private var model
    let sample: Sample

    var body: some View {
        var totals = [Double](repeating: 0, count: 3)
        for line in sample.lines { totals[model.speaker(of: line, in: sample)] += line.end - line.start }
        let sum = max(totals.reduce(0, +), 1)
        return VStack(alignment: .leading, spacing: 10) {
            Text("Talk time").font(.headline)
            ForEach(0..<sample.speakerCount, id: \.self) { index in
                VStack(alignment: .leading, spacing: 3) {
                    HStack {
                        Circle().fill(Palette.speaker(index)).frame(width: 8, height: 8)
                        Text(Palette.speakerName(index) + (index == 0 ? " (you)" : ""))
                        Spacer()
                        Text("\(Int((totals[index] / sum * 100).rounded()))%").foregroundStyle(.secondary).monospacedDigit()
                    }
                    GeometryReader { box in
                        Capsule().fill(Palette.speaker(index)).frame(width: box.size.width * totals[index] / sum, height: 4)
                    }.frame(height: 4)
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .glassCard()
    }
}

struct FilesCard: View {
    let rows: [(String, String)]
    let folder: URL?
    var problems: [String] = []

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Files").font(.headline)
            ForEach(rows, id: \.0) { row in
                HStack { Text(row.0); Spacer(); Text(row.1).foregroundStyle(.secondary).monospacedDigit() }
                    .font(.callout)
            }
            ForEach(problems, id: \.self) { Text($0).font(.callout).foregroundStyle(.orange) }
            if let folder {
                Button("Show in Finder") { NSWorkspace.shared.activateFileViewerSelecting([folder]) }
                    .buttonStyle(.link)
            } else {
                Text("Sample: nothing saved.").font(.callout).foregroundStyle(.secondary)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .glassCard()
    }
}
