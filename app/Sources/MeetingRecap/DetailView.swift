import RecorderCore
import SwiftUI

struct DetailView: View {
    @Environment(AppModel.self) private var model

    enum Kind {
        case none, draft, live
        case sample(Sample)
        case recording(RecordingInfo)
    }

    var kind: Kind {
        switch model.selection {
        case nil: .none
        case .draft: .draft
        case .live: .live
        case .sample(let id): Samples.all.first { $0.id == id }.map(Kind.sample) ?? .none
        case .recording(let id): model.recordings.first { $0.id == id }.map(Kind.recording) ?? .none
        }
    }

    var body: some View {
        @Bindable var model = model
        VStack(alignment: .leading, spacing: 0) {
            if let message = model.errorMessage {
                ErrorBanner(message: message) { model.errorMessage = nil }
            }
            switch kind {
            case .none:
                ContentUnavailableView("Select a meeting", systemImage: "waveform", description: Text("Or start a new one."))
            default:
                VStack(alignment: .leading, spacing: 16) {
                    header
                    TabSwitcher(selection: $model.tab, enabled: enabledTabs)
                    content
                }
                .padding([.horizontal, .bottom], 28)
                .padding(.top, 8)
                .frame(maxWidth: 860, maxHeight: .infinity, alignment: .topLeading)
                .frame(maxWidth: .infinity)
            }
        }
        .background(Backdrop())
    }

    private var enabledTabs: Set<DetailTab> {
        switch kind {
        case .draft, .live, .none: [.meeting]
        default: Set(DetailTab.allCases)
        }
    }

    @ViewBuilder private var header: some View {
        switch kind {
        case .draft:
            Header(title: "New meeting", subtitle: "Not started")
        case .live:
            Header(title: "New meeting", subtitle: model.phase == .stopping ? "Saving…" : "Recording", recording: true)
        case .sample(let sample):
            Header(title: sample.title, subtitle: "\(clock(sample.durationSeconds)) · \(sample.speakerCount) speakers") {
                StatusPill(text: "Sample", tone: .neutral)
            }
        case .recording(let info):
            RecordingHeader(info: info)
        case .none:
            EmptyView()
        }
    }

    @ViewBuilder private var content: some View {
        switch (model.tab, kind) {
        case (.meeting, .draft): DraftSetup()
        case (.meeting, .live): RecorderPanel()
        case (.meeting, .sample(let sample)): SampleMeeting(sample: sample)
        case (.meeting, .recording(let info)): RecordingMeeting(info: info)
        case (.recap, .sample(let sample)): RecapTab(sample: sample)
        case (.recap, .recording):
            ContentUnavailableView("Not processed yet", systemImage: "text.bubble",
                                   description: Text("The transcription pipeline isn't connected in this prototype. The sample meetings show what this tab will look like."))
        default: EmptyView()
        }
    }
}

struct Header<Accessory: View>: View {
    let title: String
    let subtitle: String
    var recording = false
    @ViewBuilder var accessory: Accessory

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(spacing: 10) {
                Text(title).font(.largeTitle.weight(.semibold))
                accessory
            }
            HStack(spacing: 6) {
                if recording { Circle().fill(.red).frame(width: 8, height: 8) }
                Text(subtitle).foregroundStyle(.secondary)
            }
        }
    }
}

extension Header where Accessory == EmptyView {
    init(title: String, subtitle: String, recording: Bool = false) {
        self.init(title: title, subtitle: subtitle, recording: recording) { EmptyView() }
    }
}

struct RecordingHeader: View {
    @Environment(AppModel.self) private var model
    let info: RecordingInfo
    @State private var name = ""
    @FocusState private var editing: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            TextField("Name this meeting", text: $name)
                .textFieldStyle(.plain)
                .font(.largeTitle.weight(.semibold))
                .focused($editing)
                .onSubmit { model.rename(info, to: name); editing = false }
                .onChange(of: editing) { if !editing { model.rename(info, to: name) } }
            Text("\(whenLabel(info.date)) · \(clock(info.durationSeconds))").foregroundStyle(.secondary)
        }
        .onAppear { name = title(of: info) }
        .onChange(of: info.id) { name = title(of: info) }
    }
}

/// Meeting and Recap. A tab that can't show anything yet is dimmed.
struct TabSwitcher: View {
    @Binding var selection: DetailTab
    let enabled: Set<DetailTab>

    var body: some View {
        HStack(spacing: 2) {
            ForEach(DetailTab.allCases) { tab in
                Button { selection = tab } label: {
                    Text(tab.rawValue)
                        .padding(.horizontal, 16).padding(.vertical, 6)
                        .background(selection == tab ? AnyShapeStyle(.tint.opacity(0.28)) : AnyShapeStyle(.clear), in: Capsule())
                        .contentShape(Capsule())
                }
                .buttonStyle(.plain)
                .foregroundStyle(enabled.contains(tab) ? .primary : .tertiary)
                .disabled(!enabled.contains(tab))
            }
        }
        .padding(3)
        .glassEffect(.regular, in: .capsule)
        .fixedSize()
        .help(enabled.count == 1 ? "Transcript and recap are made after you stop." : "")
    }
}

struct ErrorBanner: View {
    let message: String
    let dismiss: () -> Void

    var body: some View {
        HStack(alignment: .top) {
            Image(systemName: "exclamationmark.triangle.fill").foregroundStyle(.orange)
            Text(message).textSelection(.enabled).frame(maxWidth: .infinity, alignment: .leading)
            Button("Dismiss", action: dismiss).buttonStyle(.glass)
        }
        .padding(12)
        .glassEffect(.regular.tint(.orange.opacity(0.25)), in: .rect(cornerRadius: 16))
        .padding(12)
    }
}
