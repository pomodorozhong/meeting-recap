import AVFoundation
import Foundation

public let captureSampleRate = 48_000

/// One output file fed from one ScreenCaptureKit stream type. All calls come from the session's capture queue,
/// except `pad(to:)` and the finish steps, which the session runs after capture stops.
final class CaptureTrack {
    let name: String
    let writer: AVAssetWriter
    let input: AVAssetWriterInput
    var firstTime: CMTime?
    var lastEnd: CMTime = .zero
    var silenceFilled: Double = 0
    var dropped: Double = 0
    var peak: Float = 0
    /// A buffer in this track's format, to make the silence that pads its end.
    var template: CMSampleBuffer?
    /// The first write failure; once set, the recording has lost audio and must stop.
    var error: String?

    init(name: String, url: URL, channels: Int) throws {
        self.name = name
        writer = try AVAssetWriter(outputURL: url, fileType: .m4a)
        input = AVAssetWriterInput(mediaType: .audio, outputSettings: [
            AVFormatIDKey: kAudioFormatAppleLossless,
            AVSampleRateKey: captureSampleRate,
            AVNumberOfChannelsKey: channels,
            AVEncoderBitDepthHintKey: 16,
        ])
        input.expectsMediaDataInRealTime = true
        writer.add(input)
    }

    func append(_ buffer: CMSampleBuffer, sessionStart: CMTime) {
        guard error == nil else { return }
        if writer.status == .unknown {
            guard writer.startWriting() else { return fail("could not start writing") }
            writer.startSession(atSourceTime: sessionStart)
        }
        guard writer.status == .writing else { return fail("writer stopped") }
        guard input.isReadyForMoreMediaData else {
            // The encoder fell behind; the gap is filled with silence below and reported in timing.json.
            dropped += buffer.duration.seconds
            return
        }
        let time = buffer.presentationTimeStamp
        if firstTime == nil {
            firstTime = time
            lastEnd = sessionStart
        }
        // Fill a late start or a dropout with silence so both files keep one timeline.
        if (time - lastEnd).seconds > 0.01, let silence = CaptureTrack.silence(like: buffer, from: lastEnd, to: time) {
            silenceFilled += (time - lastEnd).seconds
            guard input.append(silence) else { return fail("could not write silence") }
        }
        lastEnd = time + buffer.duration
        peak = max(peak, CaptureTrack.peak(of: buffer))
        guard input.append(buffer) else { return fail("could not write audio") }
        if template == nil { template = buffer }
    }

    /// Fills silence from the last buffer to `end`, in one-second pieces, so a dropout that lasts until the
    /// recording stops still leaves both files on one timeline. Runs after capture stops, so it can wait for the encoder.
    func pad(to end: CMTime) {
        guard error == nil, writer.status == .writing, let template, (end - lastEnd).seconds > 0.01 else { return }
        let missing = (end - lastEnd).seconds
        let piece = CMTime(value: CMTimeValue(captureSampleRate), timescale: CMTimeScale(captureSampleRate))
        while (end - lastEnd).seconds > 0.001 {
            let next = min(end, lastEnd + piece)
            let deadline = Date().addingTimeInterval(5)
            while !input.isReadyForMoreMediaData {
                guard Date() < deadline else { return fail("the encoder did not accept the end padding") }
                usleep(10_000)
            }
            guard let silence = CaptureTrack.silence(like: template, from: lastEnd, to: next), input.append(silence) else {
                return fail("could not pad the end with silence")
            }
            lastEnd = next
        }
        silenceFilled += missing
    }

    func fail(_ what: String) {
        error = "\(what): \(writer.error?.localizedDescription ?? "unknown error")"
    }

    /// A zeroed buffer in the same format as `buffer`, covering `start` to `end`.
    static func silence(like buffer: CMSampleBuffer, from start: CMTime, to end: CMTime) -> CMSampleBuffer? {
        guard let description = buffer.formatDescription else { return nil }
        let format = AVAudioFormat(cmAudioFormatDescription: description)
        let count = AVAudioFrameCount(((end - start).seconds * format.sampleRate).rounded())
        guard count > 0, let pcm = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: count) else { return nil }
        pcm.frameLength = count
        for audio in UnsafeMutableAudioBufferListPointer(pcm.mutableAudioBufferList) {
            if let data = audio.mData { memset(data, 0, Int(audio.mDataByteSize)) }
        }
        var timing = CMSampleTimingInfo(
            duration: CMTime(value: 1, timescale: CMTimeScale(format.sampleRate)),
            presentationTimeStamp: start, decodeTimeStamp: .invalid
        )
        var sample: CMSampleBuffer?
        guard CMSampleBufferCreate(
            allocator: nil, dataBuffer: nil, dataReady: false, makeDataReadyCallback: nil, refcon: nil,
            formatDescription: description, sampleCount: CMItemCount(count),
            sampleTimingEntryCount: 1, sampleTimingArray: &timing,
            sampleSizeEntryCount: 0, sampleSizeArray: nil, sampleBufferOut: &sample
        ) == noErr, let sample,
            CMSampleBufferSetDataBufferFromAudioBufferList(
                sample, blockBufferAllocator: nil, blockBufferMemoryAllocator: nil, flags: 0, bufferList: pcm.audioBufferList
            ) == noErr else { return nil }
        return sample
    }

    /// Peak absolute sample value, assuming ScreenCaptureKit's float PCM.
    static func peak(of buffer: CMSampleBuffer) -> Float {
        var result: Float = 0
        try? buffer.withAudioBufferList { list, _ in
            for audio in list {
                guard let data = audio.mData else { continue }
                let samples = data.assumingMemoryBound(to: Float.self)
                for i in 0..<Int(audio.mDataByteSize) / MemoryLayout<Float>.size {
                    result = max(result, abs(samples[i]))
                }
            }
        }
        return result
    }
}
