import SwiftUI

/// Colors that carry meaning: one per speaker, plus the two recorded tracks. Speaker A is always you, because the
/// microphone track is yours, so the "You" lane and Speaker A share a color.
enum Palette {
    static let coral = Color(red: 0.85, green: 0.35, blue: 0.19)
    static let teal = Color(red: 0.11, green: 0.62, blue: 0.46)
    static let purple = Color(red: 0.50, green: 0.47, blue: 0.87)

    static let speakers = [coral, teal, purple]
    static let speakerNames = ["Speaker A", "Speaker B", "Speaker C"]

    static func speaker(_ index: Int) -> Color { speakers[index % speakers.count] }
    static func speakerName(_ index: Int) -> String { speakerNames[index % speakerNames.count] }

    static let you = coral
    static let call = teal
}

func clock(_ seconds: Double) -> String {
    let total = Int(seconds.rounded())
    return total >= 3600
        ? String(format: "%d:%02d:%02d", total / 3600, total % 3600 / 60, total % 60)
        : String(format: "%d:%02d", total / 60, total % 60)
}

/// Soft color behind the detail pane, so the glass has something to refract.
struct Backdrop: View {
    var body: some View {
        ZStack {
            Rectangle().fill(.background)
            Circle().fill(Palette.coral.opacity(0.16)).frame(width: 420).blur(radius: 90).offset(x: -260, y: -190)
            Circle().fill(Palette.teal.opacity(0.14)).frame(width: 460).blur(radius: 100).offset(x: 300, y: 150)
            Circle().fill(Palette.purple.opacity(0.14)).frame(width: 380).blur(radius: 90).offset(x: 80, y: -240)
        }
        .ignoresSafeArea()
    }
}

extension View {
    /// A floating Liquid Glass card.
    func glassCard(radius: CGFloat = 20, padding: CGFloat = 16) -> some View {
        self.padding(padding).glassEffect(.regular, in: .rect(cornerRadius: radius))
    }
}

struct StatusPill: View {
    enum Tone {
        case good, warn, bad, neutral
        var color: Color {
            switch self {
            case .good: .green
            case .warn: .orange
            case .bad: .red
            case .neutral: .secondary
            }
        }
    }

    let text: String
    var tone: Tone = .neutral

    var body: some View {
        Text(text)
            .font(.caption2.weight(.medium))
            .padding(.horizontal, 7).padding(.vertical, 2)
            .background(tone.color.opacity(0.18), in: Capsule())
            .foregroundStyle(tone.color)
    }
}
