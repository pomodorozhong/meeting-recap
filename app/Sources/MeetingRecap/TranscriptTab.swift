import SwiftUI

struct TranscriptTab: View {
    @Environment(AppModel.self) private var model
    let sample: Sample
    @State private var cursor = -1

    var body: some View {
        let uncertain = model.uncertainLines(in: sample)
        ScrollViewReader { proxy in
            ScrollView {
                VStack(alignment: .leading, spacing: 12) {
                    legend
                    checkBar(uncertain)
                    LazyVStack(alignment: .leading, spacing: 6) {
                        ForEach(sample.lines) { line in
                            LineRow(sample: sample, line: line).id(line.id)
                        }
                    }
                }
                .padding(.bottom, 20)
            }
            .scrollIndicators(.hidden)
            .onChange(of: model.scrollTarget) {
                guard let target = model.scrollTarget else { return }
                withAnimation { proxy.scrollTo(target, anchor: .center) }
                model.scrollTarget = nil
            }
            .onAppear {
                // Arriving from a recap citation: the target was set before this view existed.
                guard let target = model.scrollTarget else { return }
                Task { @MainActor in
                    withAnimation { proxy.scrollTo(target, anchor: .center) }
                    model.scrollTarget = nil
                }
            }
        }
    }

    private var legend: some View {
        HStack(spacing: 16) {
            ForEach(0..<sample.speakerCount, id: \.self) { index in
                HStack(spacing: 5) {
                    Circle().fill(Palette.speaker(index)).frame(width: 8, height: 8)
                    Text(Palette.speakerName(index) + (index == 0 ? " (you)" : "")).font(.callout).foregroundStyle(.secondary)
                }
            }
        }
    }

    @ViewBuilder private func checkBar(_ uncertain: [TranscriptLine]) -> some View {
        HStack {
            if uncertain.isEmpty {
                Label("Every speaker label is checked", systemImage: "checkmark.circle").foregroundStyle(.green)
            } else {
                Label("\(uncertain.count) line\(uncertain.count == 1 ? "" : "s") to check", systemImage: "questionmark.bubble")
                    .foregroundStyle(.orange)
            }
            Spacer()
            if !uncertain.isEmpty {
                Button("Previous") { go(uncertain, forward: false) }.buttonStyle(.glass)
                Button("Next") { go(uncertain, forward: true) }.buttonStyle(.glass)
            }
        }
        .font(.callout)
        .padding(.horizontal, 14).padding(.vertical, 8)
        .glassEffect(.regular, in: .capsule)
    }

    private func go(_ uncertain: [TranscriptLine], forward: Bool) {
        let ids = uncertain.map(\.id)
        let next = forward ? (ids.first { $0 > cursor } ?? ids.first) : (ids.last { $0 < cursor } ?? ids.last)
        guard let next else { return }
        cursor = next
        model.highlighted = [next]
        model.scrollTarget = next
    }
}

struct LineRow: View {
    @Environment(AppModel.self) private var model
    let sample: Sample
    let line: TranscriptLine

    var body: some View {
        let speaker = model.speaker(of: line, in: sample)
        let unsure = !line.candidates.isEmpty && model.resolved[sample.id]?[line.id] == nil
        HStack(alignment: .top, spacing: 12) {
            RoundedRectangle(cornerRadius: 2).fill(Palette.speaker(speaker)).frame(width: 4)
            Text(clock(line.start)).font(.caption.monospacedDigit()).foregroundStyle(.secondary)
                .frame(width: 40, alignment: .leading).padding(.top, 2)
            VStack(alignment: .leading, spacing: 3) {
                Text(Palette.speakerName(speaker) + (speaker == 0 ? " (you)" : ""))
                    .font(.caption.weight(.medium)).foregroundStyle(Palette.speaker(speaker))
                Text(line.text).textSelection(.enabled)
                if unsure {
                    HStack(spacing: 8) {
                        Text("Speaker unsure: " + line.candidates.map(Palette.speakerName).joined(separator: " or "))
                            .font(.caption).foregroundStyle(.orange)
                        Menu("Choose") {
                            ForEach(0..<sample.speakerCount, id: \.self) { index in
                                Button(Palette.speakerName(index)) { model.resolve(line, in: sample, as: index) }
                            }
                        }
                        .menuStyle(.button).buttonStyle(.glass).controlSize(.small).fixedSize()
                    }
                }
            }
            Spacer(minLength: 0)
        }
        .padding(.vertical, 6).padding(.horizontal, 10)
        .background(rowBackground(unsure: unsure), in: RoundedRectangle(cornerRadius: 12))
    }

    private func rowBackground(unsure: Bool) -> AnyShapeStyle {
        if model.highlighted.contains(line.id) { return AnyShapeStyle(Color.yellow.opacity(0.22)) }
        if unsure { return AnyShapeStyle(Color.orange.opacity(0.14)) }
        return AnyShapeStyle(.clear)
    }
}
