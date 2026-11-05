import AppKit
import RecorderCore
import SwiftUI

/// Shows one call: the recording's real facts (when it is a recording) and the mock transcript and recap.
struct ReviewView: View {
    let title: String
    let info: RecordingInfo?
    @State private var tab = Tab.recap
    @State private var highlighted: Set<Int> = []
    @State private var scrollTarget: Int?

    enum Tab: String, CaseIterable { case recap = "Recap", transcript = "Transcript" }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            header
            MockBanner(isRecording: info != nil)
            Picker("", selection: $tab) {
                ForEach(Tab.allCases, id: \.self) { Text($0.rawValue).tag($0) }
            }
            .pickerStyle(.segmented)
            .labelsHidden()
            .frame(maxWidth: 260)
            .padding([.horizontal, .top], 14)
            switch tab {
            case .recap: RecapView(highlighted: $highlighted, showTranscript: { lines in
                highlighted = Set(lines)
                scrollTarget = lines.min()
                tab = .transcript
            })
            case .transcript: TranscriptView(highlighted: highlighted, scrollTarget: $scrollTarget)
            }
        }
        .onChange(of: title) { highlighted = []; scrollTarget = nil }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title).font(.title2.bold())
            if let info {
                HStack(spacing: 12) {
                    Text(clock(info.durationSeconds) + " recorded")
                    if info.silenceFilledSeconds > 0.5 {
                        Text(String(format: "%.1f s of silence filled in", info.silenceFilledSeconds))
                    }
                    if info.droppedSeconds > 0.01 {
                        Text(String(format: "%.1f s dropped by the encoder", info.droppedSeconds)).foregroundStyle(.orange)
                    }
                    Button("Show in Finder") { NSWorkspace.shared.activateFileViewerSelecting([info.folder]) }
                        .buttonStyle(.link)
                }
                .font(.callout).foregroundStyle(.secondary)
                ForEach(info.problems, id: \.self) { Text($0).font(.callout).foregroundStyle(.orange) }
            } else {
                Text("\(clock(Fixtures.durationSeconds)) · 3 speakers · invented for the prototype")
                    .font(.callout).foregroundStyle(.secondary)
            }
        }
        .padding(14)
    }
}

struct MockBanner: View {
    let isRecording: Bool
    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: "hammer")
            Text(isRecording
                 ? "Mock content: the transcript and recap below are a sample, not from this recording. The pipeline is not connected yet."
                 : "Mock content: an invented call, to show how transcripts and recaps will look. The pipeline is not connected yet.")
        }
        .font(.callout)
        .padding(10)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.blue.opacity(0.12))
    }
}

func speakerColor(_ speaker: String) -> Color {
    switch speaker {
    case "Speaker A": .blue
    case "Speaker B": .orange
    default: .purple
    }
}

struct RecapView: View {
    @Binding var highlighted: Set<Int>
    let showTranscript: ([Int]) -> Void

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 22) {
                section("Summary", Fixtures.recap.summary)
                section("Decisions", Fixtures.recap.decisions)
                section("Action items", Fixtures.recap.actions)
                Text("Click a number to jump to the transcript line it comes from. Check the line before acting on an owner, date or decision.")
                    .font(.footnote).foregroundStyle(.secondary)
            }
            .padding(14)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private func section(_ name: String, _ items: [RecapItem]) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(name).font(.headline)
            ForEach(items) { item in
                HStack(alignment: .firstTextBaseline, spacing: 6) {
                    Text("•")
                    Text(item.text)
                    ForEach(item.cites, id: \.self) { line in
                        Button("\(line + 1)") { showTranscript(item.cites) }
                            .buttonStyle(.bordered).controlSize(.mini)
                            .help("Transcript line \(line + 1), \(Fixtures.transcript[line].speaker)")
                    }
                }
            }
        }
    }
}

struct TranscriptView: View {
    let highlighted: Set<Int>
    @Binding var scrollTarget: Int?

    var body: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 4) {
                    ForEach(Fixtures.transcript) { line in
                        HStack(alignment: .firstTextBaseline, spacing: 10) {
                            Text("\(line.id + 1)").font(.caption.monospacedDigit()).foregroundStyle(.tertiary).frame(width: 22, alignment: .trailing)
                            Text(clock(line.start)).font(.caption.monospacedDigit()).foregroundStyle(.secondary).frame(width: 40, alignment: .leading)
                            Text(line.speaker).bold().foregroundStyle(speakerColor(line.speaker)).frame(width: 84, alignment: .leading)
                            Text(line.text).textSelection(.enabled)
                        }
                        .padding(.vertical, 4).padding(.horizontal, 8)
                        .background(highlighted.contains(line.id) ? Color.yellow.opacity(0.25) : .clear, in: RoundedRectangle(cornerRadius: 6))
                        .id(line.id)
                    }
                }
                .padding(14)
            }
            .onAppear { scroll(proxy) }
            .onChange(of: scrollTarget) { scroll(proxy) }
        }
    }

    private func scroll(_ proxy: ScrollViewProxy) {
        guard let target = scrollTarget else { return }
        withAnimation { proxy.scrollTo(target, anchor: .top) }
        scrollTarget = nil
    }
}
