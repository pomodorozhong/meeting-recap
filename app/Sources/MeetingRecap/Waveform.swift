import AVFoundation
import SwiftUI

enum Waveforms {
    static let bucketCount = 240

    /// A level (on the 60 dB scale) above which a track counts as someone talking: about -27 dBFS.
    static let talkLevel: Float = 0.55

    /// Who was talking, for a real recording with no transcript yet: you (in your color) when the microphone is above
    /// `talkLevel` and louder than the call; otherwise someone on the call, in grey, since who that is isn't known
    /// until transcription. Both lists cover `duration` in equal buckets.
    static func turns(call: [Float], mic: [Float], duration: Double) -> [TurnSpan] {
        let count = max(call.count, mic.count)
        guard count > 0, duration > 0 else { return [] }
        let width = duration / Double(count)
        var spans: [TurnSpan] = []
        for index in 0..<count {
            let callLevel = index < call.count ? call[index] : 0
            let micLevel = index < mic.count ? mic[index] : 0
            extend(&spans, who: who(call: callLevel, mic: micLevel), from: Double(index) * width, length: width)
        }
        return spans
    }

    /// 0 for you, 1 for someone on the call, nil for nobody, from one stretch's peak levels.
    static func who(call: Float, mic: Float) -> Int? {
        if mic >= talkLevel, mic >= call { return 0 }
        if call >= talkLevel { return 1 }
        return nil
    }

    /// Adds one stretch to `spans`, joining it to the last span when the same person talked right before.
    static func extend(_ spans: inout [TurnSpan], who: Int?, from start: Double, length: Double) {
        guard let who else { return }
        if let last = spans.last, last.who == who, abs(last.end - start) < length / 2 {
            spans[spans.count - 1].end = start + length
        } else {
            spans.append(TurnSpan(start: start, end: start + length, who: who,
                                  color: who == 0 ? Palette.you : Palette.unknownSpeaker))
        }
    }

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
