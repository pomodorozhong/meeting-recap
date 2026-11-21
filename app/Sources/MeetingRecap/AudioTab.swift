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
