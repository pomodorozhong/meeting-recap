import RecorderCore
import SwiftUI

/// What the player card needs, from a real recording or from a sample.
struct PlayerState {
    var position: Double
    var duration: Double
    var isPlaying: Bool
    var toggle: () -> Void
}

/// While recording: the card shows the timer and Stop in place of playback, and the timeline grows with the recording.
struct LiveControls {
    var elapsed: Double
    var stopping: Bool
    var stopLabel = "Stop and save"
    /// The stretch the timeline shows: a fixed length, so turns keep their size, ending at the newest audio once the
    /// recording is longer than that.
    var windowStart: Double
    var windowLength: Double
    /// Every turn so far, for the overview of the whole recording above the window.
    var allTurns: [TurnSpan] = []
    var stop: () -> Void
}

/// One stretch on the Turns row: who talked, and in which color.
struct TurnSpan: Hashable {
    var start: Double
    var end: Double
    var who: Int
    var color: Color
}

/// The meeting's timeline, the same while recording and afterwards: who talked when, with the screenshots above it,
/// and your notes. Afterwards it spans the whole meeting; while recording it shows a fixed window that fills from the
/// left and then moves with the recording, and there is no playhead. It sits above the scrolling part of the Meeting
/// tab, so it stays on screen.
struct PlayerCard: View {
    let state: PlayerState
    var live: LiveControls?
    var turns: [TurnSpan] = []
    var shots: [Shot] = []
    var showShots: Binding<Bool>?
    var notes: [Note] = []
    /// Jumps to a time in seconds.
    let seek: (Double) -> Void

    var body: some View {
        let position: Double? = live == nil ? state.position : nil
        let start = live?.windowStart ?? 0
        let length = live?.windowLength ?? state.duration
        VStack(spacing: 8) {
            HStack(spacing: 12) {
                if let live {
                    Circle().fill(.red).frame(width: 10, height: 10)
                    Text(clock(live.elapsed)).font(.title2.weight(.medium).monospacedDigit())
                    Text("Timeline: \(clock(live.windowStart)) – \(clock(live.windowStart + live.windowLength))")
                        .font(.callout.monospacedDigit()).foregroundStyle(.secondary)
                    Spacer()
                    Button { live.stop() } label: {
                        Label(live.stopping ? "Saving…" : live.stopLabel, systemImage: "stop.circle.fill")
                    }
                    .buttonStyle(.glassProminent).tint(.red)
                    .keyboardShortcut("r", modifiers: .command)
                    .disabled(live.stopping)
                } else {
                    Button { state.toggle() } label: {
                        Image(systemName: state.isPlaying ? "pause.fill" : "play.fill").frame(width: 16, height: 16)
                    }
                    .buttonStyle(.glass).buttonBorderShape(.circle)
                    .keyboardShortcut(.space, modifiers: [])
                    Text("\(clock(state.position)) / \(clock(state.duration))")
                        .font(.callout.monospacedDigit()).foregroundStyle(.secondary)
                    Spacer()
                }
                if let showShots {
                    Toggle(isOn: showShots) { Label("Screenshots", systemImage: "camera") }
                        .toggleStyle(.button).buttonStyle(.glass).controlSize(.small)
                }
            }
            if let live {
                LaneRow(label: "Overview") {
                    OverviewStrip(turns: live.allTurns, notes: notes, duration: live.elapsed,
                                  windowStart: live.windowStart, windowLength: live.windowLength)
                }
            }
            LaneRow(label: "Turns") {
                TurnsStrip(turns: turns, shots: (showShots?.wrappedValue ?? true) ? shots : [], start: start, duration: length,
                           position: position, pick: live == nil ? seek : nil)
            }
            LaneRow(label: "Notes") {
                NotesStrip(notes: notes, start: start, duration: length, now: live?.elapsed, position: position,
                           pick: live == nil ? seek : nil)
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
        case note(Note)

        var id: String {
            switch self {
            case .line(let line): "l\(line.id)"
            case .shot(let shot): "s\(shot.id)"
            case .note(let note): "n\(note.id)"
            }
        }

        var time: Double {
            switch self {
            case .line(let line): line.start
            case .shot(let shot): shot.time
            case .note(let note): note.start
            }
        }
    }

    private var entries: [Entry] {
        let all = sample.lines.map(Entry.line) + (showShots ? sample.shots.map(Entry.shot) : []) + sample.notes.map(Entry.note)
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
                    turns: sample.lines.map { TurnSpan(start: $0.start, end: $0.end, who: speakerOf($0), color: Palette.speaker(speakerOf($0))) },
                    shots: sample.shots, showShots: $showShots, notes: sample.notes
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
                                case .note(let note):
                                    NoteRow(note: note) { model.seekSample(to: note.start) }.id(entry.id)
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

/// A real recording: the same timeline as while it was recording, with playback, then your notes. The transcript and
/// screenshots aren't connected yet.
struct RecordingMeeting: View {
    @Environment(AppModel.self) private var model
    let info: RecordingInfo
    @State private var call: [Float] = []
    @State private var mic: [Float] = []
    @State private var notes: [Note] = []

    var body: some View {
        let player = model.player
        let seek = { (seconds: Double) in
            if player.duration > 0 { player.seek(to: seconds / player.duration) }
        }
        let duration = player.duration > 0 ? player.duration : info.durationSeconds
        VStack(alignment: .leading, spacing: 12) {
            PlayerCard(
                state: PlayerState(position: player.position, duration: duration, isPlaying: player.isPlaying,
                                   toggle: { player.toggle() }),
                turns: Waveforms.turns(call: call, mic: mic, duration: duration), notes: notes, seek: seek
            )
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    NotesFeed(notes: notes) { seek($0.start) }
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
            notes = NotesFile.read(folder: info.folder)
            let folder = info.folder
            (call, mic) = await Task.detached {
                (Waveforms.levels(of: folder.appendingPathComponent("system.m4a")),
                 Waveforms.levels(of: folder.appendingPathComponent("mic.m4a")))
            }.value
        }
    }
}

/// Your notes in time order, under the timeline. `onEdit`, while recording, lets a finished note be fixed in place.
struct NotesFeed: View {
    let notes: [Note]
    var onEdit: ((Note, String) -> Void)?
    let pick: (Note) -> Void

    var body: some View {
        if !notes.isEmpty {
            VStack(alignment: .leading, spacing: 6) {
                ForEach(notes) { note in
                    NoteRow(note: note, onTap: { pick(note) }, onEdit: onEdit.map { edit in { edit(note, $0) } }).id("n\(note.id)")
                }
            }
        }
    }
}

/// Who talked when, with the screenshots above it, and the playhead. Click to jump (not while recording).
struct TurnsStrip: View {
    let turns: [TurnSpan]
    let shots: [Shot]
    /// The time at the left edge, and how many seconds the strip shows.
    var start: Double = 0
    let duration: Double
    let position: Double?
    let pick: ((Double) -> Void)?

    var body: some View {
        GeometryReader { box in
            let width = box.size.width
            let total = max(duration, 1)
            // Screenshots sit above the turns: a camera with a tick pointing down at its moment.
            let top: CGFloat = 18
            ZStack(alignment: .topLeading) {
                RoundedRectangle(cornerRadius: 3).fill(.quaternary.opacity(0.5)).frame(width: width, height: 16)
                    .offset(y: top)
                ForEach(Array(turns.enumerated()), id: \.offset) { _, turn in
                    RoundedRectangle(cornerRadius: 2)
                        .fill(turn.color)
                        .frame(width: max(2, (turn.end - turn.start) / total * width), height: 16)
                        .offset(x: (turn.start - start) / total * width, y: top)
                }
                ForEach(shots) { shot in
                    VStack(spacing: 0) {
                        Image(systemName: "camera.fill").font(.system(size: 9)).foregroundStyle(.secondary)
                        Rectangle().fill(.secondary).frame(width: 1, height: 4)
                    }
                    .frame(width: 16)
                    .offset(x: (shot.time - start) / total * width - 8, y: 1)
                }
                if let position {
                    Rectangle().fill(.primary).frame(width: 1.5, height: 16)
                        .offset(x: min(max((position - start) / total, 0), 1) * width - 0.75, y: top)
                }
            }
            .frame(width: width, height: 34, alignment: .topLeading)
            .clipped()
            .contentShape(Rectangle())
            .gesture(DragGesture(minimumDistance: 0).onChanged { drag in
                pick?(start + min(max(drag.location.x / width, 0), 1) * total)
            })
        }
        .frame(height: 34)
        .help(pick == nil ? "Who is talking: you or the call." : "Click to jump to that moment.")
    }
}

/// While recording: the whole recording so far in one thin strip, turns above and notes below, with a frame around
/// the stretch the timeline under it shows. It squeezes as the recording grows; the turns themselves never change.
struct OverviewStrip: View {
    let turns: [TurnSpan]
    let notes: [Note]
    let duration: Double
    let windowStart: Double
    let windowLength: Double

    var body: some View {
        Canvas { context, size in
            let total = max(duration, windowLength, 1)
            func x(_ time: Double) -> CGFloat { CGFloat(time / total) * size.width }
            context.fill(Path(roundedRect: CGRect(x: 0, y: 3, width: size.width, height: 10), cornerRadius: 2),
                         with: .color(.secondary.opacity(0.12)))
            for turn in turns {
                let rect = CGRect(x: x(turn.start), y: 3, width: max(1, x(turn.end) - x(turn.start)), height: 6)
                context.fill(Path(rect), with: .color(turn.color))
            }
            for note in notes {
                let end = note.end ?? duration
                let rect = CGRect(x: x(note.start), y: 10, width: max(2, x(end) - x(note.start)), height: 3)
                context.fill(Path(rect), with: .color(Palette.note.opacity(note.end == nil ? 0.55 : 1)))
            }
            // Dim what the timeline below doesn't show, and frame what it does.
            let left = x(windowStart), right = min(size.width, x(windowStart + windowLength))
            context.fill(Path(CGRect(x: 0, y: 0, width: left, height: size.height)), with: .color(.black.opacity(0.35)))
            context.fill(Path(CGRect(x: right, y: 0, width: size.width - right, height: size.height)),
                         with: .color(.black.opacity(0.35)))
            let frame = CGRect(x: left, y: 0, width: right - left, height: size.height).insetBy(dx: 0.75, dy: 0.75)
            context.stroke(Path(roundedRect: frame, cornerRadius: 3), with: .color(.primary.opacity(0.7)), lineWidth: 1.5)
        }
        .frame(height: 16)
        .help("The whole recording so far. The frame is the stretch shown below.")
    }
}

/// Your notes on their own row under the turns: each spans from its first keystroke to Return. Click to jump.
struct NotesStrip: View {
    let notes: [Note]
    /// The time at the left edge, and how many seconds the strip shows.
    var start: Double = 0
    let duration: Double
    /// While recording, where a note still being typed reaches.
    var now: Double?
    let position: Double?
    let pick: ((Double) -> Void)?

    var body: some View {
        GeometryReader { box in
            let width = box.size.width
            let total = max(duration, 1)
            ZStack(alignment: .topLeading) {
                RoundedRectangle(cornerRadius: 3).fill(.quaternary.opacity(0.5)).frame(width: width, height: 10)
                ForEach(notes) { note in
                    let end: Double = note.end ?? now ?? (start + duration)
                    let span: Double = (end - note.start) / total * Double(width)
                    let x: Double = (note.start - start) / total * Double(width)
                    RoundedRectangle(cornerRadius: 2)
                        .fill(Palette.note.opacity(note.end == nil ? 0.55 : 1))
                        .frame(width: max(4, span), height: 10)
                        .offset(x: x)
                }
                if let position {
                    Rectangle().fill(.primary).frame(width: 1.5, height: 10)
                        .offset(x: min(max((position - start) / total, 0), 1) * width - 0.75)
                }
            }
            .frame(width: width, height: 10, alignment: .topLeading)
            .clipped()
            .contentShape(Rectangle())
            .gesture(DragGesture(minimumDistance: 0).onChanged { drag in
                pick?(start + min(max(drag.location.x / width, 0), 1) * total)
            })
        }
        .frame(height: 10)
        .help("Your notes, from first keystroke to Return.")
    }
}

/// A note you typed, in the feed at its start time. With `onEdit` its text can be fixed; its times stay.
struct NoteRow: View {
    let note: Note
    var onTap: () -> Void = {}
    var onEdit: ((String) -> Void)?
    @State private var text = ""

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            RoundedRectangle(cornerRadius: 2).fill(Palette.note).frame(width: 4)
            Text(clock(note.start)).font(.caption.monospacedDigit()).foregroundStyle(.secondary)
                .frame(width: 40, alignment: .leading).padding(.top, 2)
            VStack(alignment: .leading, spacing: 3) {
                Label("Your note" + (note.end.map { " · typed until \(clock($0))" } ?? ""), systemImage: "pencil")
                    .font(.caption.weight(.medium)).foregroundStyle(Palette.note)
                if let onEdit {
                    TextField("Note", text: $text, axis: .vertical)
                        .textFieldStyle(.plain)
                        .onAppear { text = note.text }
                        .onChange(of: text) { if !text.isEmpty, text != note.text { onEdit(text) } }
                        .onSubmit { onEdit(text) }
                } else {
                    Text(note.text).fixedSize(horizontal: false, vertical: true)
                }
            }
            Spacer(minLength: 0)
        }
        .padding(.vertical, 6).padding(.horizontal, 10)
        .background(Palette.note.opacity(0.08), in: RoundedRectangle(cornerRadius: 12))
        .contentShape(Rectangle())
        .onTapGesture(perform: onTap)
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
