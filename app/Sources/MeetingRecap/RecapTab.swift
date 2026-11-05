import AppKit
import SwiftUI

struct RecapTab: View {
    @Environment(AppModel.self) private var model
    let sample: Sample

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                VStack(alignment: .leading, spacing: 18) {
                    section("Summary") { ForEach(sample.recap.summary) { item in line(item) } }
                    section("Decisions") { ForEach(sample.recap.decisions) { item in line(item) } }
                    section("Action items") { ForEach(sample.recap.actions) { item in action(item) } }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .glassCard(radius: 24, padding: 22)

                HStack(spacing: 10) {
                    Button { copy() } label: { Label("Copy", systemImage: "doc.on.doc") }.buttonStyle(.glassProminent)
                    Button("Save as Markdown") { save() }.buttonStyle(.glass)
                    Button { } label: { Label("Regenerate", systemImage: "arrow.clockwise") }
                        .buttonStyle(.glass).disabled(true).help("The recap model isn't connected in this prototype.")
                    Spacer()
                    Text("Written by Qwen3.5 9B")
                        .font(.callout).foregroundStyle(.secondary)
                        .help("Sample text. The pipeline's recap model is Qwen3.5 9B 4-bit (revision 8b2b98c); read the cited line before acting on an owner, date or decision.")
                }
                Text("Click a number to jump to the line it comes from. Read that line before acting on an owner, date or decision.")
                    .font(.footnote).foregroundStyle(.secondary)
            }
            .padding(.bottom, 20)
        }
        .scrollIndicators(.hidden)
    }

    private func section<Content: View>(_ name: String, @ViewBuilder _ content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(name).font(.title3.weight(.semibold))
            content()
        }
    }

    private func line(_ item: RecapItem) -> some View {
        HStack(alignment: .firstTextBaseline, spacing: 6) {
            Text(item.text).font(.system(.body, design: .serif)).fixedSize(horizontal: false, vertical: true)
            chips(item)
            Spacer(minLength: 0)
        }
    }

    private func action(_ item: RecapItem) -> some View {
        let key = "\(sample.id)-\(item.id)"
        let done = model.doneActions.contains(key)
        return HStack(alignment: .firstTextBaseline, spacing: 8) {
            Button {
                if done { model.doneActions.remove(key) } else { model.doneActions.insert(key) }
            } label: { Image(systemName: done ? "checkmark.square.fill" : "square") }
                .buttonStyle(.plain)
            if let speaker = item.speaker {
                Circle().fill(Palette.speaker(speaker)).frame(width: 8, height: 8)
                Text(Palette.speakerName(speaker) + ":").foregroundStyle(.secondary)
            }
            Text(item.text).strikethrough(done).foregroundStyle(done ? .secondary : .primary)
                .fixedSize(horizontal: false, vertical: true)
            chips(item)
            if let due = item.due { Text("· \(due)").foregroundStyle(.secondary) }
            Spacer(minLength: 0)
        }
    }

    private func chips(_ item: RecapItem) -> some View {
        HStack(spacing: 4) {
            ForEach(item.cites, id: \.self) { index in
                Button { model.jump(to: item.cites) } label: {
                    Text("\(index + 1)").font(.caption2.monospacedDigit())
                        .padding(.horizontal, 6).padding(.vertical, 1)
                        .background(.quaternary, in: Capsule())
                }
                .buttonStyle(.plain)
                .help("Line \(index + 1), \(Palette.speakerName(sample.lines[index].speaker))")
            }
        }
    }

    private var markdown: String {
        func cites(_ item: RecapItem) -> String { " [" + item.cites.map { String($0 + 1) }.joined(separator: ", ") + "]" }
        var text = "# \(sample.title)\n\n## Summary\n"
        for item in sample.recap.summary { text += "- \(item.text)\(cites(item))\n" }
        text += "\n## Decisions\n"
        for item in sample.recap.decisions { text += "- \(item.text)\(cites(item))\n" }
        text += "\n## Action items\n"
        for item in sample.recap.actions {
            let who = item.speaker.map { Palette.speakerName($0) + ": " } ?? ""
            text += "- [ ] \(who)\(item.text)\(item.due.map { " (\($0))" } ?? "")\(cites(item))\n"
        }
        return text
    }

    private func copy() {
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(markdown, forType: .string)
    }

    private func save() {
        let panel = NSSavePanel()
        panel.nameFieldStringValue = "\(sample.title).md"
        if panel.runModal() == .OK, let url = panel.url {
            try? markdown.write(to: url, atomically: true, encoding: .utf8)
        }
    }
}
