import SwiftUI

/// The meeting in time order: what was said and what was on screen, with an overview strip on top.
struct TimelineTab: View {
    @Environment(AppModel.self) private var model
    let sample: Sample
    @State private var cursor = -1
    @State private var showShots = true

    private enum Entry: Identifiable {
        case line(TranscriptLine)
        case shot(Shot)

        var id: String {
            switch self {
            case .line(let line): "l\(line.id)"
            case .shot(let shot): "s\(shot.id)"
            }
        }

        var time: Double {
            switch self {
            case .line(let line): line.start
            case .shot(let shot): shot.time
            }
        }
    }

    private var entries: [Entry] {
        let all = sample.lines.map(Entry.line) + (showShots ? sample.shots.map(Entry.shot) : [])
        return all.sorted { ($0.time, $0.id) < ($1.time, $1.id) }
    }

    var body: some View {
        let uncertain = model.uncertainLines(in: sample)
        ScrollViewReader { proxy in
            VStack(alignment: .leading, spacing: 12) {
                header
                TimelineStrip(sample: sample, showShots: showShots, speakerOf: { model.speaker(of: $0, in: sample) }) { time in
                    if let nearest = entries.min(by: { abs($0.time - time) < abs($1.time - time) }) {
                        withAnimation { proxy.scrollTo(nearest.id, anchor: .top) }
                    }
                }
                checkBar(uncertain)
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 6) {
                        ForEach(entries) { entry in
                            switch entry {
                            case .line(let line): LineRow(sample: sample, line: line).id(entry.id)
                            case .shot(let shot): ShotRow(shot: shot).id(entry.id)
                            }
                        }
                    }
                    .padding(.bottom, 20)
                }
                .scrollIndicators(.hidden)
            }
            .onChange(of: model.scrollTarget) {
                guard let target = model.scrollTarget else { return }
                withAnimation { proxy.scrollTo("l\(target)", anchor: .center) }
                model.scrollTarget = nil
            }
            .onAppear {
                // Arriving from a recap citation: the target was set before this view existed.
                guard let target = model.scrollTarget else { return }
                Task { @MainActor in
                    withAnimation { proxy.scrollTo("l\(target)", anchor: .center) }
                    model.scrollTarget = nil
                }
            }
        }
    }

    private var header: some View {
        HStack(spacing: 16) {
            ForEach(0..<sample.speakerCount, id: \.self) { index in
                HStack(spacing: 5) {
                    Circle().fill(Palette.speaker(index)).frame(width: 8, height: 8)
                    Text(Palette.speakerName(index) + (index == 0 ? " (you)" : "")).font(.callout).foregroundStyle(.secondary)
                }
            }
            Spacer()
            Toggle(isOn: $showShots) { Label("Screenshots", systemImage: "camera") }
                .toggleStyle(.button).buttonStyle(.glass).controlSize(.small)
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

/// The whole meeting in one strip: who spoke when, and where the screenshots fall. Click to jump.
struct TimelineStrip: View {
    let sample: Sample
    let showShots: Bool
    let speakerOf: (TranscriptLine) -> Int
    let pick: (Double) -> Void

    var body: some View {
        GeometryReader { box in
            let width = box.size.width
            let total = max(sample.durationSeconds, 1)
            ZStack(alignment: .topLeading) {
                RoundedRectangle(cornerRadius: 3).fill(.quaternary.opacity(0.5)).frame(width: width, height: 16)
                ForEach(sample.lines) { line in
                    RoundedRectangle(cornerRadius: 2)
                        .fill(Palette.speaker(speakerOf(line)))
                        .frame(width: max(2, (line.end - line.start) / total * width), height: 16)
                        .offset(x: line.start / total * width)
                }
                if showShots {
                    ForEach(sample.shots) { shot in
                        VStack(spacing: 0) {
                            Rectangle().fill(.secondary).frame(width: 1, height: 6)
                            Image(systemName: "camera.fill").font(.system(size: 10)).foregroundStyle(.secondary)
                        }
                        .frame(width: 16)
                        .offset(x: shot.time / total * width - 8, y: 16)
                    }
                }
            }
            .frame(width: width, height: 40, alignment: .topLeading)
            .contentShape(Rectangle())
            .gesture(DragGesture(minimumDistance: 0).onEnded { pick(min(max($0.location.x / width, 0), 1) * total) })
        }
        .frame(height: 40)
        .help("Click to jump to that moment.")
    }
}

struct ShotRow: View {
    let shot: Shot

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            RoundedRectangle(cornerRadius: 2).fill(.secondary.opacity(0.5)).frame(width: 4)
            Text(clock(shot.time)).font(.caption.monospacedDigit()).foregroundStyle(.secondary)
                .frame(width: 40, alignment: .leading).padding(.top, 2)
            VStack(alignment: .leading, spacing: 6) {
                Label("Screenshot · \(shot.app)", systemImage: "camera.fill")
                    .font(.caption.weight(.medium)).foregroundStyle(.secondary)
                ShotThumb(kind: shot.kind)
                    .frame(width: 240, height: 150)
                    .clipShape(RoundedRectangle(cornerRadius: 10))
                    .overlay(RoundedRectangle(cornerRadius: 10).strokeBorder(.quaternary))
                Text(shot.caption).font(.callout).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
            }
            Spacer(minLength: 0)
        }
        .padding(.vertical, 6).padding(.horizontal, 10)
    }
}

/// A drawn stand-in for a screenshot. Nothing here is real screen content.
struct ShotThumb: View {
    let kind: ShotKind

    private func bar(_ width: CGFloat, _ height: CGFloat = 8) -> some View {
        RoundedRectangle(cornerRadius: 3).fill(.secondary.opacity(0.35)).frame(width: width, height: height)
    }

    var body: some View {
        VStack(spacing: 0) {
            HStack(spacing: 5) {
                ForEach([Color.red, .yellow, .green], id: \.self) { Circle().fill($0.opacity(0.7)).frame(width: 7, height: 7) }
                Spacer()
            }
            .padding(.horizontal, 10).frame(height: 22)
            .background(.quaternary.opacity(0.6))
            content.padding(14).frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        }
        .background(.background)
    }

    @ViewBuilder private var content: some View {
        switch kind {
        case .slides:
            VStack(alignment: .leading, spacing: 10) {
                RoundedRectangle(cornerRadius: 4).fill(Palette.teal.opacity(0.6)).frame(width: 150, height: 16)
                bar(180); bar(160); bar(120)
            }
        case .dashboard:
            HStack(alignment: .bottom, spacing: 8) {
                ForEach([40, 70, 55, 90, 30], id: \.self) { height in
                    RoundedRectangle(cornerRadius: 3).fill(height == 30 ? Palette.coral.opacity(0.7) : Palette.teal.opacity(0.55))
                        .frame(width: 24, height: CGFloat(height))
                }
                Spacer()
                VStack(alignment: .leading, spacing: 8) { bar(50, 14); bar(50, 14) }
            }
        case .document:
            VStack(alignment: .leading, spacing: 7) {
                bar(130, 12)
                ForEach([200, 190, 170, 195, 120], id: \.self) { bar(CGFloat($0), 6) }
            }
        case .chat:
            VStack(alignment: .leading, spacing: 8) {
                bar(120, 16)
                HStack { Spacer(); RoundedRectangle(cornerRadius: 8).fill(Palette.purple.opacity(0.5)).frame(width: 110, height: 16) }
                bar(150, 16)
                HStack { Spacer(); RoundedRectangle(cornerRadius: 8).fill(Palette.purple.opacity(0.5)).frame(width: 80, height: 16) }
            }
        case .calendar:
            VStack(spacing: 5) {
                ForEach(0..<4, id: \.self) { row in
                    HStack(spacing: 5) {
                        ForEach(0..<7, id: \.self) { column in
                            RoundedRectangle(cornerRadius: 3)
                                .fill((row == 1 && column == 3) || (row == 2 && column == 5) ? Palette.coral.opacity(0.7) : .secondary.opacity(0.2))
                                .frame(width: 26, height: 20)
                        }
                    }
                }
            }
        case .ticket:
            VStack(alignment: .leading, spacing: 8) {
                HStack { bar(120, 12); RoundedRectangle(cornerRadius: 4).fill(Palette.coral.opacity(0.7)).frame(width: 36, height: 12) }
                bar(200, 6); bar(180, 6); bar(150, 6)
            }
        }
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
