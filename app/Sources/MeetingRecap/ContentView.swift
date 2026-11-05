import RecorderCore
import SwiftUI

func clock(_ seconds: Double) -> String {
    let total = Int(seconds.rounded())
    return total >= 3600
        ? String(format: "%d:%02d:%02d", total / 3600, total % 3600 / 60, total % 60)
        : String(format: "%d:%02d", total / 60, total % 60)
}

struct ContentView: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        @Bindable var model = model
        NavigationSplitView {
            List(selection: $model.selection) {
                Section("Samples") {
                    Label(Fixtures.title, systemImage: "doc.text")
                        .tag(Selection.sample)
                }
                Section("Recordings") {
                    if model.recordings.isEmpty {
                        Text("Nothing recorded yet").foregroundStyle(.secondary)
                    }
                    ForEach(model.recordings) { item in
                        HStack {
                            Image(systemName: item.isComplete ? "waveform" : "exclamationmark.triangle")
                                .foregroundStyle(item.isComplete ? Color.secondary : Color.orange)
                            VStack(alignment: .leading) {
                                Text(item.id.replacingOccurrences(of: "T", with: "  ")).font(.body.monospacedDigit())
                                Text(clock(item.durationSeconds)).font(.caption).foregroundStyle(.secondary)
                            }
                        }
                        .tag(Selection.recording(item.id))
                    }
                }
            }
            .navigationSplitViewColumnWidth(min: 200, ideal: 240)
        } detail: {
            VStack(spacing: 0) {
                RecordBar()
                Divider()
                if let message = model.errorMessage {
                    ErrorBanner(message: message) { model.errorMessage = nil }
                }
                switch model.selection {
                case .recording:
                    if let info = model.recording(for: model.selection) {
                        ReviewView(title: info.id, info: info)
                    } else {
                        Placeholder(text: "Recording not found")
                    }
                case .sample:
                    ReviewView(title: Fixtures.title, info: nil)
                case nil:
                    Placeholder(text: "Select a recording")
                }
            }
        }
    }
}

struct Placeholder: View {
    let text: String
    var body: some View {
        Text(text).foregroundStyle(.secondary).frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

struct ErrorBanner: View {
    let message: String
    let dismiss: () -> Void
    var body: some View {
        HStack(alignment: .top) {
            Image(systemName: "exclamationmark.triangle.fill").foregroundStyle(.orange)
            Text(message).textSelection(.enabled).frame(maxWidth: .infinity, alignment: .leading)
            Button("Dismiss", action: dismiss).buttonStyle(.borderless)
        }
        .padding(10)
        .background(Color.orange.opacity(0.15))
    }
}

/// Record controls and the live meters, always visible above the review pane.
struct RecordBar: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        @Bindable var model = model
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 14) {
                Button {
                    Task { model.phase == .recording ? await model.stop() : await model.start() }
                } label: {
                    Label(model.phase == .recording ? "Stop" : "Record",
                          systemImage: model.phase == .recording ? "stop.circle.fill" : "record.circle")
                        .frame(minWidth: 84)
                }
                .keyboardShortcut("r", modifiers: .command)
                .buttonStyle(.borderedProminent)
                .controlSize(.large)
                .tint(model.phase == .recording ? .red : .accentColor)
                .disabled(model.phase == .starting || model.phase == .stopping)

                switch model.phase {
                case .recording:
                    Text(clock(model.meter.elapsedSeconds)).font(.title2.monospacedDigit())
                    LevelMeter(label: "Others", peak: model.meter.systemPeak)
                    LevelMeter(label: "You", peak: model.meter.micPeak)
                case .starting: ProgressView().controlSize(.small); Text("Starting…").foregroundStyle(.secondary)
                case .stopping: ProgressView().controlSize(.small); Text("Saving…").foregroundStyle(.secondary)
                case .idle: Text("Records the call's audio and your microphone to two files.").foregroundStyle(.secondary)
                }
                Spacer()
            }
            if model.phase == .idle {
                HStack(spacing: 14) {
                    Picker("Microphone", selection: $model.microphone) {
                        Text("System default").tag(String?.none)
                        ForEach(model.microphones, id: \.self) { Text($0).tag(String?.some($0)) }
                    }
                    .frame(maxWidth: 300)
                    TextField("Only this app's audio (optional), such as Teams", text: $model.appFilter)
                        .textFieldStyle(.roundedBorder)
                        .frame(maxWidth: 340)
                }
            }
        }
        .padding(12)
    }
}

struct LevelMeter: View {
    let label: String
    let peak: Float
    /// Holds the last peak briefly, so short sounds stay visible between readings.
    @State private var shown: Float = 0

    var body: some View {
        let db = peak > 0 ? 20 * log10(peak) : -80
        let level = CGFloat(min(1, max(0, (db + 60) / 60)))
        HStack(spacing: 6) {
            Text(label).font(.caption).foregroundStyle(.secondary)
            GeometryReader { box in
                ZStack(alignment: .leading) {
                    Capsule().fill(.quaternary)
                    Capsule().fill(level > 0.92 ? Color.red : Color.green)
                        .frame(width: box.size.width * max(level, CGFloat(shown)))
                }
            }
            .frame(width: 110, height: 8)
        }
        .onChange(of: level) { _, new in
            shown = Float(new)
            withAnimation(.easeOut(duration: 0.4)) { shown = 0 }
        }
    }
}
