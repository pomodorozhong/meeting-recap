import AVFoundation
import Foundation
import Testing
@testable import RecorderCore

/// A fresh temporary folder, removed by the OS later; tests never touch real recordings.
func temporaryFolder() throws -> URL {
    let url = FileManager.default.temporaryDirectory.appendingPathComponent("recorder-core-\(UUID().uuidString)")
    try FileManager.default.createDirectory(at: url, withIntermediateDirectories: true)
    return url.resolvingSymlinksInPath()
}

@Suite struct RecordingFolderTests {
    @Test func acceptsNewFolder() throws {
        let root = try temporaryFolder()
        let folder = try RecordingFolder.create(under: root, now: Date(timeIntervalSince1970: 0))
        #expect(FileManager.default.fileExists(atPath: folder.path))
        #expect(folder.deletingLastPathComponent() == root)
    }

    @Test func refusesFolderInsideGitCheckout() throws {
        let checkout = try temporaryFolder()
        try FileManager.default.createDirectory(at: checkout.appendingPathComponent(".git"), withIntermediateDirectories: true)
        #expect(throws: CaptureError.self) { try RecordingFolder.validate(checkout.appendingPathComponent("raw/one")) }
    }

    @Test func refusesWorktreeCheckoutWhereGitIsAFile() throws {
        let checkout = try temporaryFolder()
        try "gitdir: elsewhere".write(to: checkout.appendingPathComponent(".git"), atomically: true, encoding: .utf8)
        #expect(throws: CaptureError.self) { try RecordingFolder.validate(checkout.appendingPathComponent("one")) }
    }

    @Test func refusesSymlinkIntoCheckout() throws {
        let checkout = try temporaryFolder()
        try FileManager.default.createDirectory(at: checkout.appendingPathComponent(".git"), withIntermediateDirectories: true)
        let elsewhere = try temporaryFolder()
        let link = elsewhere.appendingPathComponent("link")
        try FileManager.default.createSymbolicLink(at: link, withDestinationURL: checkout)
        #expect(throws: CaptureError.self) { try RecordingFolder.validate(link.appendingPathComponent("one")) }
    }

    @Test func refusesNonEmptyFolder() throws {
        let folder = try temporaryFolder()
        try "x".write(to: folder.appendingPathComponent("a.txt"), atomically: true, encoding: .utf8)
        #expect(throws: CaptureError.self) { try RecordingFolder.validate(folder) }
    }

    @Test func folderNamesRoundTripToDates() {
        let date = Date(timeIntervalSince1970: 1_800_000_000)
        let name = RecordingFolder.name(for: date, timeZone: .gmt)
        #expect(RecordingFolder.date(fromName: name, timeZone: .gmt) == date)
        #expect(RecordingFolder.date(fromName: "not-a-date") == nil)
    }

    @Test func folderNamesSortByTime() {
        let a = RecordingFolder.name(for: Date(timeIntervalSince1970: 0), timeZone: .gmt)
        let b = RecordingFolder.name(for: Date(timeIntervalSince1970: 3600), timeZone: .gmt)
        #expect(a == "1970-01-01T00-00-00")
        #expect(a < b)
    }
}

@Suite struct RecordingLibraryTests {
    func writeTiming(_ folder: URL, systemWritten: Bool = true, micError: String? = nil) throws {
        let track: (Bool, String?) -> [String: Any] = { written, error in
            ["duration_seconds": 12.5, "silence_filled_seconds": 0.5, "dropped_seconds": 0.0,
             "written": written, "error": error.map { $0 as Any } ?? NSNull()]
        }
        let json: [String: Any] = ["sample_rate": 48000, "system": track(systemWritten, nil), "mic": track(true, micError)]
        try JSONSerialization.data(withJSONObject: json).write(to: folder.appendingPathComponent("timing.json"))
    }

    @Test func listsNewestFirstAndReadsTiming() throws {
        let root = try temporaryFolder()
        for name in ["2026-01-01T10-00-00", "2026-01-02T10-00-00"] {
            let folder = root.appendingPathComponent(name)
            try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
            try writeTiming(folder)
        }
        let list = RecordingLibrary.list(root: root)
        #expect(list.map(\.id) == ["2026-01-02T10-00-00", "2026-01-01T10-00-00"])
        #expect(list[0].isComplete)
        #expect(list[0].durationSeconds == 12.5)
        #expect(list[0].silenceFilledSeconds == 1.0)
    }

    @Test func reportsIncompleteRecordings() throws {
        let root = try temporaryFolder()
        let unfinished = root.appendingPathComponent("a")
        let failed = root.appendingPathComponent("b")
        for folder in [unfinished, failed] { try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true) }
        try writeTiming(failed, systemWritten: false, micError: "disk full")
        let byID = Dictionary(uniqueKeysWithValues: RecordingLibrary.list(root: root).map { ($0.id, $0) })
        #expect(byID["a"]?.isComplete == false)
        #expect(byID["b"]?.problems.count == 2)
    }

    @Test func readsAndClearsTitles() throws {
        let root = try temporaryFolder()
        let folder = root.appendingPathComponent("2026-01-01T10-00-00")
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
        try writeTiming(folder)
        #expect(RecordingLibrary.list(root: root)[0].title == nil)
        #expect(RecordingLibrary.list(root: root)[0].date != nil)
        try RecordingLibrary.rename(folder: folder, to: "  Customer call  ")
        #expect(RecordingLibrary.list(root: root)[0].title == "Customer call")
        try RecordingLibrary.rename(folder: folder, to: " ")
        #expect(RecordingLibrary.list(root: root)[0].title == nil)
    }

    @Test func ignoresPlainFiles() throws {
        let root = try temporaryFolder()
        try "x".write(to: root.appendingPathComponent(".DS_Store"), atomically: true, encoding: .utf8)
        #expect(RecordingLibrary.list(root: root).isEmpty)
    }
}

/// Float PCM in ScreenCaptureKit's layout, as a sample buffer starting at `start` seconds.
func pcmBuffer(seconds: Double, start: Double, channels: Int, value: Float) throws -> CMSampleBuffer {
    let format = AVAudioFormat(commonFormat: .pcmFormatFloat32, sampleRate: Double(captureSampleRate),
                               channels: AVAudioChannelCount(channels), interleaved: false)!
    let frames = AVAudioFrameCount(seconds * Double(captureSampleRate))
    let pcm = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: frames)!
    pcm.frameLength = frames
    for channel in 0..<channels { for i in 0..<Int(frames) { pcm.floatChannelData![channel][i] = value } }
    var timing = CMSampleTimingInfo(
        duration: CMTime(value: 1, timescale: CMTimeScale(captureSampleRate)),
        presentationTimeStamp: CMTime(seconds: start, preferredTimescale: CMTimeScale(captureSampleRate)),
        decodeTimeStamp: .invalid
    )
    var sample: CMSampleBuffer?
    try #require(CMSampleBufferCreate(
        allocator: nil, dataBuffer: nil, dataReady: false, makeDataReadyCallback: nil, refcon: nil,
        formatDescription: format.formatDescription, sampleCount: CMItemCount(frames),
        sampleTimingEntryCount: 1, sampleTimingArray: &timing,
        sampleSizeEntryCount: 0, sampleSizeArray: nil, sampleBufferOut: &sample
    ) == noErr)
    let made = try #require(sample)
    try #require(CMSampleBufferSetDataBufferFromAudioBufferList(
        made, blockBufferAllocator: nil, blockBufferMemoryAllocator: nil, flags: 0, bufferList: pcm.audioBufferList
    ) == noErr)
    return made
}

@Suite struct CaptureTrackTests {
    @Test func silenceCoversTheRequestedSpan() throws {
        let buffer = try pcmBuffer(seconds: 0.1, start: 0, channels: 1, value: 0.5)
        let silence = try #require(CaptureTrack.silence(
            like: buffer, from: .zero, to: CMTime(seconds: 0.5, preferredTimescale: 48000)
        ))
        #expect(silence.numSamples == 24000)
        #expect(CaptureTrack.peak(of: silence) == 0)
        #expect(CaptureTrack.peak(of: buffer) == 0.5)
    }

    @Test func gapsAndLateStartsAreFilledSoBothTracksShareOneTimeline() throws {
        let folder = try temporaryFolder()
        let late = try CaptureTrack(name: "late", url: folder.appendingPathComponent("late.m4a"), channels: 1)
        let early = try CaptureTrack(name: "early", url: folder.appendingPathComponent("early.m4a"), channels: 1)
        let start = CMTime.zero
        // `early` has audio at 0-1 s and 2-3 s (a 1 s dropout); `late` first speaks at 1 s and stops at 1.5 s.
        early.append(try pcmBuffer(seconds: 1, start: 0, channels: 1, value: 0.3), sessionStart: start)
        early.append(try pcmBuffer(seconds: 1, start: 2, channels: 1, value: 0.3), sessionStart: start)
        late.append(try pcmBuffer(seconds: 0.5, start: 1, channels: 1, value: 0.3), sessionStart: start)
        let end = max(early.lastEnd, late.lastEnd)
        for track in [early, late] { track.pad(to: end) }
        #expect(early.error == nil && late.error == nil)
        #expect(abs(early.silenceFilled - 1.0) < 0.01)
        #expect(abs(late.silenceFilled - 2.5) < 0.01)  // 1 s before its first audio, 1.5 s after its last

        for track in [early, late] {
            track.input.markAsFinished()
            let done = DispatchSemaphore(value: 0)
            track.writer.finishWriting { done.signal() }
            done.wait()
            #expect(track.writer.status == .completed)
        }
        for name in ["early", "late"] {
            let duration = try AVAudioFile(forReading: folder.appendingPathComponent("\(name).m4a")).processingFormat.sampleRate
            #expect(duration == Double(captureSampleRate))
            let file = try AVAudioFile(forReading: folder.appendingPathComponent("\(name).m4a"))
            #expect(abs(Double(file.length) / Double(captureSampleRate) - 3.0) < 0.05)
        }
    }
}
