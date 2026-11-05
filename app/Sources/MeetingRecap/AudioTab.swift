import AppKit
import RecorderCore
import SwiftUI

/// Before recording starts: pick the sources, then start.
struct DraftSetup: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        @Bindable var model = model
        VStack(alignment: .leading, spacing: 18) {
            VStack(alignment: .leading, spacing: 14) {
                Picker("Your microphone", selection: $model.microphone) {
                    Text("System default").tag(String?.none)
                    ForEach(model.microphones, id: \.self) { Text($0).tag(String?.some($0)) }
                }
                VStack(alignment: .leading, spacing: 4) {
                    Text("Call audio from")
                    TextField("Call audio from", text: $model.appFilter, prompt: Text("All apps"))
                        .labelsHidden()
                    Text("Type an app's name, such as Teams or Chrome, to leave out music and alerts.")
                        .font(.caption).foregroundStyle(.secondary)
                }
            }
            .glassCard()

            HStack(spacing: 14) {
                Button { Task { await model.start() } } label: {
                    Label("Start recording", systemImage: "record.circle").padding(.horizontal, 10)
                }
                .buttonStyle(.glassProminent).tint(.red).controlSize(.large)
                .keyboardShortcut("r", modifiers: .command)
                .disabled(model.phase == .starting)
                if model.phase == .starting { ProgressView().controlSize(.small) }
                Text("Wear headphones, or the call leaks into your microphone.")
                    .font(.callout).foregroundStyle(.secondary)
            }
            Spacer()
        }
        .frame(maxWidth: 520)
    }
}

/// While recording: the timer, the two live tracks, and Stop.
struct RecorderPanel: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack(alignment: .center) {
                Text(clock(model.meter.elapsedSeconds))
                    .font(.system(size: 52, weight: .medium)).monospacedDigit()
                Spacer()
                Button { Task { await model.stop() } } label: {
                    Label(model.phase == .stopping ? "Saving…" : "Stop and save", systemImage: "stop.circle.fill")
                        .padding(.horizontal, 8)
                }
                .buttonStyle(.glassProminent).tint(.red).controlSize(.large)
                .keyboardShortcut("r", modifiers: .command)
                .disabled(model.phase == .stopping)
            }
            .glassCard()

            VStack(spacing: 10) {
                LaneRow(label: "Call") {
                    WaveformView(bars: Waveforms.liveBars(model.liveCall, color: Palette.call), alignRight: true, height: 56)
                }
                LaneRow(label: "You") {
                    WaveformView(bars: Waveforms.liveBars(model.liveMic, color: Palette.you), alignRight: true, height: 56)
                }
            }
            .glassCard()

            if model.callSilentSeconds >= 30 {
                Label("The call track has been silent for \(Int(model.callSilentSeconds)) seconds. Check that the call is playing through this Mac.",
                      systemImage: "exclamationmark.triangle.fill")
                    .foregroundStyle(.orange)
                    .glassCard(radius: 16, padding: 12)
            }
            Text("Saving to this Mac. The transcript and recap are made after you stop.")
                .font(.callout).foregroundStyle(.secondary)
            Spacer()
        }
    }
}

struct LaneRow<Content: View>: View {
    let label: String
    @ViewBuilder var content: Content

    var body: some View {
        HStack(spacing: 10) {
            Text(label).font(.callout).foregroundStyle(.secondary).frame(width: 40, alignment: .leading)
            content
        }
    }
}

struct SamplePlayback: View {
    @Environment(AppModel.self) private var model
    let sample: Sample

    var body: some View {
        let speakerOf = { (line: TranscriptLine) in model.speaker(of: line, in: sample) }
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                VStack(spacing: 12) {
                    HStack(spacing: 12) {
                        Button {} label: { Image(systemName: "play.fill").frame(width: 18, height: 18) }
                            .buttonStyle(.glass).buttonBorderShape(.circle).controlSize(.large)
                            .disabled(true).help("Sample meetings have no audio.")
                        Text("0:00 / \(clock(sample.durationSeconds))").font(.callout.monospacedDigit()).foregroundStyle(.secondary)
                        Spacer()
                        Text("Sample: no audio").font(.callout).foregroundStyle(.secondary)
                    }
                    LaneRow(label: "Call") { WaveformView(bars: Waveforms.bars(for: sample, lane: .call, speakerOf: speakerOf)) }
                    LaneRow(label: "You") { WaveformView(bars: Waveforms.bars(for: sample, lane: .you, speakerOf: speakerOf)) }
                }
                .glassCard()

                HStack(alignment: .top, spacing: 16) {
                    TalkTime(sample: sample)
                    FilesCard(rows: [("Length", clock(sample.durationSeconds)), ("Gaps filled", "none"), ("Dropped", "none")], folder: nil)
                }
            }
        }
        .scrollIndicators(.hidden)
    }
}

struct RecordingPlayback: View {
    @Environment(AppModel.self) private var model
    let info: RecordingInfo
    @State private var call: [WaveBar] = []
    @State private var mic: [WaveBar] = []

    var body: some View {
        let player = model.player
        let fraction = player.duration > 0 ? player.position / player.duration : 0
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                VStack(spacing: 12) {
                    HStack(spacing: 12) {
                        Button { player.toggle() } label: {
                            Image(systemName: player.isPlaying ? "pause.fill" : "play.fill").frame(width: 18, height: 18)
                        }
                        .buttonStyle(.glass).buttonBorderShape(.circle).controlSize(.large)
                        .keyboardShortcut(.space, modifiers: [])
                        Text("\(clock(player.position)) / \(clock(player.duration))").font(.callout.monospacedDigit()).foregroundStyle(.secondary)
                        Spacer()
                        Text("Plays both tracks. Click a track to jump.").font(.callout).foregroundStyle(.secondary)
                    }
                    LaneRow(label: "Call") { WaveformView(bars: call, playhead: fraction, onSeek: { player.seek(to: $0) }) }
                    LaneRow(label: "You") { WaveformView(bars: mic, playhead: fraction, onSeek: { player.seek(to: $0) }) }
                }
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
        }
        .scrollIndicators(.hidden)
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
