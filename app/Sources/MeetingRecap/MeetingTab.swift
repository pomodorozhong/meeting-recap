import RecorderCore
import SwiftUI

/// What the player card needs, from a real recording or from a sample.
struct PlayerState {
    var position: Double
    var duration: Double
    var isPlaying: Bool
    var toggle: () -> Void
}

/// The player: play, both tracks, and (for a sample) who spoke when and where the screenshots fall. It sits above the
/// scrolling part of the Meeting tab, so it stays on screen.
struct PlayerCard: View {
    let state: PlayerState
    let call: [WaveBar]
    let mic: [WaveBar]
    var sample: Sample?
    var speakerOf: ((TranscriptLine) -> Int)?
    var showShots: Binding<Bool>?
    /// Jumps to a time in seconds.
    let seek: (Double) -> Void

    var body: some View {
        let fraction = state.duration > 0 ? state.position / state.duration : 0
        VStack(spacing: 8) {
            HStack(spacing: 12) {
                Button { state.toggle() } label: {
                    Image(systemName: state.isPlaying ? "pause.fill" : "play.fill").frame(width: 16, height: 16)
                }
                .buttonStyle(.glass).buttonBorderShape(.circle)
                .keyboardShortcut(.space, modifiers: [])
                Text("\(clock(state.position)) / \(clock(state.duration))")
                    .font(.callout.monospacedDigit()).foregroundStyle(.secondary)
                Spacer()
                if let showShots {
                    Toggle(isOn: showShots) { Label("Screenshots", systemImage: "camera") }
                        .toggleStyle(.button).buttonStyle(.glass).controlSize(.small)
                }
            }
            LaneRow(label: "Call") {
                WaveformView(bars: call, playhead: fraction, height: 28, onSeek: { seek($0 * state.duration) })
            }
            LaneRow(label: "You") {
                WaveformView(bars: mic, playhead: fraction, height: 28, onSeek: { seek($0 * state.duration) })
            }
            if let sample, let speakerOf {
                LaneRow(label: "Turns") {
                    TimelineStrip(sample: sample, showShots: showShots?.wrappedValue ?? true, position: state.position,
                                  speakerOf: speakerOf, pick: seek)
                }
            }
        }
        .glassCard(radius: 20, padding: 12)
    }
}

/// A sample meeting: the player on top, then speech and screenshots in time order. Playback is simulated.
struct SampleMeeting: View {
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

    /// The line being spoken at the playhead, once playback has started.
    private var currentLine: Int? {
        guard model.samplePosition > 0 else { return nil }
        return sample.lines.last { $0.start <= model.samplePosition }?.id
    }

    var body: some View {
        let uncertain = model.uncertainLines(in: sample)
        let speakerOf = { (line: TranscriptLine) in model.speaker(of: line, in: sample) }
        ScrollViewReader { proxy in
            VStack(alignment: .leading, spacing: 12) {
                PlayerCard(
                    state: PlayerState(position: model.samplePosition, duration: sample.durationSeconds,
                                       isPlaying: model.samplePlaying,
                                       toggle: { model.toggleSample(duration: sample.durationSeconds) }),
                    call: Waveforms.bars(for: sample, lane: .call, speakerOf: speakerOf),
                    mic: Waveforms.bars(for: sample, lane: .you, speakerOf: speakerOf),
                    sample: sample, speakerOf: speakerOf, showShots: $showShots
                ) { seconds in jump(to: seconds, proxy: proxy) }

                ScrollView {
                    VStack(alignment: .leading, spacing: 12) {
                        legend
                        checkBar(uncertain)
                        LazyVStack(alignment: .leading, spacing: 6) {
                            ForEach(entries) { entry in
                                switch entry {
                                case .line(let line):
                                    LineRow(sample: sample, line: line, current: line.id == currentLine) {
                                        model.seekSample(to: line.start)
                                    }.id(entry.id)
                                case .shot(let shot):
                                    ShotRow(shot: shot) { model.seekSample(to: shot.time) }.id(entry.id)
                                }
                            }
                        }
                        HStack(alignment: .top, spacing: 16) {
                            TalkTime(sample: sample)
                            FilesCard(rows: [("Length", clock(sample.durationSeconds)), ("Gaps filled", "none"), ("Dropped", "none")],
                                      folder: nil)
                        }
                        .padding(.top, 12)
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
            .onChange(of: currentLine) {
                guard model.samplePlaying, let id = currentLine else { return }
                withAnimation { proxy.scrollTo("l\(id)", anchor: .center) }
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

    private func jump(to seconds: Double, proxy: ScrollViewProxy) {
        model.seekSample(to: seconds)
        if let target = entries.last(where: { $0.time <= seconds }) ?? entries.first {
            withAnimation { proxy.scrollTo(target.id, anchor: .top) }
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

/// A real recording: the player on top. The transcript and screenshots aren't connected yet.
struct RecordingMeeting: View {
    @Environment(AppModel.self) private var model
    let info: RecordingInfo
    @State private var call: [WaveBar] = []
    @State private var mic: [WaveBar] = []

    var body: some View {
        let player = model.player
        VStack(alignment: .leading, spacing: 12) {
            PlayerCard(
                state: PlayerState(position: player.position, duration: player.duration, isPlaying: player.isPlaying,
                                   toggle: { player.toggle() }),
                call: call, mic: mic
            ) { seconds in
                if player.duration > 0 { player.seek(to: seconds / player.duration) }
            }
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    Label("The transcript and screenshots appear here once the pipeline is connected. The sample meetings show how.",
                          systemImage: "text.bubble")
                        .foregroundStyle(.secondary)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .glassCard()
                    HStack(alignment: .top, spacing: 16) {
                        VStack(alignment: .leading, spacing: 6) {
                            Text("Talk time").font(.headline)
                            Text("Speakers and how long each talked appear after transcription.")
                                .font(.callout).foregroundStyle(.secondary)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading).glassCard()
                        FilesCard(rows: [
                            ("Length", clock(info.durationSeconds)),
                            ("Gaps filled", info.silenceFilledSeconds > 0.5 ? String(format: "%.1f s", info.silenceFilledSeconds) : "none"),
                            ("Dropped", info.droppedSeconds > 0.01 ? String(format: "%.1f s", info.droppedSeconds) : "none"),
                        ], folder: info.folder, problems: info.problems)
                    }
                }
                .padding(.bottom, 20)
            }
            .scrollIndicators(.hidden)
        }
        .task(id: info.id) {
            model.player.load(folder: info.folder)
            call = []; mic = []
            let folder = info.folder
            let (system, mine) = await Task.detached {
                (Waveforms.levels(of: folder.appendingPathComponent("system.m4a")),
                 Waveforms.levels(of: folder.appendingPathComponent("mic.m4a")))
            }.value
            call = system.map { WaveBar(level: max($0, 0.04), color: $0 > 0 ? Palette.call : .secondary.opacity(0.4)) }
            mic = mine.map { WaveBar(level: max($0, 0.04), color: $0 > 0 ? Palette.you : .secondary.opacity(0.4)) }
        }
    }
}

/// The whole meeting in one strip: who spoke when, where the screenshots fall, and the playhead. Click to jump.
struct TimelineStrip: View {
    let sample: Sample
    let showShots: Bool
    let position: Double
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
                            Rectangle().fill(.secondary).frame(width: 1, height: 4)
                            Image(systemName: "camera.fill").font(.system(size: 9)).foregroundStyle(.secondary)
                        }
                        .frame(width: 16)
                        .offset(x: shot.time / total * width - 8, y: 16)
                    }
                }
                Rectangle().fill(.primary).frame(width: 1.5, height: 16)
                    .offset(x: min(max(position / total, 0), 1) * width - 0.75)
            }
            .frame(width: width, height: 34, alignment: .topLeading)
            .contentShape(Rectangle())
            .gesture(DragGesture(minimumDistance: 0).onChanged { pick(min(max($0.location.x / width, 0), 1) * total) })
        }
        .frame(height: 34)
        .help("Click to jump to that moment.")
    }
}

struct ShotRow: View {
    let shot: Shot
    var onTap: () -> Void = {}

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
        .contentShape(Rectangle())
        .onTapGesture(perform: onTap)
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
    /// True while the playhead is on this line.
    var current = false
    var onTap: () -> Void = {}

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
                Text(line.text)
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
        .contentShape(Rectangle())
        .onTapGesture(perform: onTap)
    }

    private func rowBackground(unsure: Bool) -> AnyShapeStyle {
        if model.highlighted.contains(line.id) { return AnyShapeStyle(Color.yellow.opacity(0.22)) }
        if current { return AnyShapeStyle(Color.accentColor.opacity(0.2)) }
        if unsure { return AnyShapeStyle(Color.orange.opacity(0.14)) }
        return AnyShapeStyle(.clear)
    }
}
