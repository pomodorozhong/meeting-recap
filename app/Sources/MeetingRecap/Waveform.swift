import AVFoundation
import SwiftUI

struct WaveBar: Hashable {
    var level: Float
    var color: Color
}

/// Bars for one track, drawn left to right across the recording, or right-aligned for a live recording.
struct WaveformView: View {
    var bars: [WaveBar]
    var playhead: Double?
    var alignRight = false
    var height: CGFloat = 44
    var onSeek: ((Double) -> Void)?

    var body: some View {
        Canvas { context, size in
            let count = max(bars.count, 1)
            let step: CGFloat = alignRight ? 3 : size.width / CGFloat(count)
            let width = max(1.5, step * 0.62)
            for (index, bar) in bars.enumerated() {
                let x = alignRight ? size.width - CGFloat(bars.count - index) * step : CGFloat(index) * step
                let barHeight = max(2, CGFloat(bar.level) * size.height)
                let rect = CGRect(x: x, y: (size.height - barHeight) / 2, width: width, height: barHeight)
                context.fill(Path(roundedRect: rect, cornerRadius: width / 2), with: .color(bar.color))
            }
            if let playhead {
                let x = CGFloat(playhead) * size.width
                context.fill(Path(CGRect(x: x - 0.75, y: 0, width: 1.5, height: size.height)), with: .color(.primary))
            }
        }
        .frame(height: height)
        .background(.quaternary.opacity(0.4), in: RoundedRectangle(cornerRadius: 10))
        .overlay {
            if let onSeek {
                GeometryReader { box in
                    Color.clear.contentShape(Rectangle())
                        .gesture(DragGesture(minimumDistance: 0).onChanged { drag in
                            onSeek(min(1, max(0, drag.location.x / box.size.width)))
                        })
                }
            }
        }
    }
}

enum Waveforms {
    static let bucketCount = 240

    /// Bars for a sample meeting: a speaker's lines light up the lane they would have been recorded on (Speaker A on
    /// the microphone, everyone else on the call), in that speaker's color. Invented, like the rest of the sample.
    static func bars(for sample: Sample, lane: Lane, speakerOf: (TranscriptLine) -> Int) -> [WaveBar] {
        (0..<bucketCount).map { index in
            let time = Double(index) / Double(bucketCount) * sample.durationSeconds
            guard let line = sample.lines.first(where: { time >= $0.start && time < $0.end }),
                  (speakerOf(line) == 0) == (lane == .you)
            else { return WaveBar(level: 0.04, color: .secondary.opacity(0.4)) }
            let noise = abs(sin(Double(index) * 12.9898 + Double(line.id) * 4.1) * 43758.5453).truncatingRemainder(dividingBy: 1)
            return WaveBar(level: Float(0.25 + 0.75 * noise), color: Palette.speaker(speakerOf(line)))
        }
    }

    static func liveBars(_ levels: [Float], color: Color) -> [WaveBar] {
        levels.map { WaveBar(level: max($0, 0.04), color: $0 > 0 ? color : .secondary.opacity(0.4)) }
    }

    enum Lane { case call, you }

    /// Peak levels (0...1, on a 60 dB scale) of an audio file, in `bucketCount` buckets across its length.
    static func levels(of url: URL) -> [Float] {
        guard let file = try? AVAudioFile(forReading: url), file.length > 0,
              let buffer = AVAudioPCMBuffer(pcmFormat: file.processingFormat, frameCapacity: 16_384)
        else { return [] }
        var result: [Float] = []
        for bucket in 0..<bucketCount {
            let end = AVAudioFramePosition(Double(bucket + 1) / Double(bucketCount) * Double(file.length))
            var peak: Float = 0
            while file.framePosition < end {
                let want = AVAudioFrameCount(min(Int64(buffer.frameCapacity), end - file.framePosition))
                guard (try? file.read(into: buffer, frameCount: want)) != nil, buffer.frameLength > 0,
                      let data = buffer.floatChannelData else { break }
                for channel in 0..<Int(buffer.format.channelCount) {
                    for frame in 0..<Int(buffer.frameLength) { peak = max(peak, abs(data[channel][frame])) }
                }
            }
            result.append(peak > 0 ? max(0, min(1, (20 * log10(peak) + 60) / 60)) : 0)
        }
        return result
    }
}
