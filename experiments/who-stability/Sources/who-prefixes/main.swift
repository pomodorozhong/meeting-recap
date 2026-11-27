import AVFoundation
import Foundation
import Who

// usage: who-prefixes <models-dir> <out.json> <step-seconds> <case>=<call.wav> ...
// Loads Who's int8 weights once from <models-dir> (never downloads), then for each recording diarizes the
// prefixes of length step, 2*step, ... below its duration, and finally the whole recording. Writes one JSON
// object: model revision, SDK version, load time, and per case its duration and one entry per prefix with
// `prefix_seconds`, `diarize_seconds` and `segments` (speaker_id, start_seconds, end_seconds).
let args = CommandLine.arguments
guard args.count >= 5, let step = Double(args[3]), step > 0 else {
    fputs("usage: who-prefixes <models-dir> <out.json> <step-seconds> <case>=<call.wav> ...\n", stderr)
    exit(2)
}
let models = args[1], out = args[2]
guard FileManager.default.fileExists(atPath: "\(models)/coreml-int8/who_meta.json") else {
    fputs("no Who weights in \(models); run experiments/who-stability/setup.sh first\n", stderr)
    exit(3)
}

func readMono(_ path: String) throws -> ([Float], Double) {
    let file = try AVAudioFile(forReading: URL(fileURLWithPath: path), commonFormat: .pcmFormatFloat32, interleaved: false)
    let format = file.processingFormat
    guard format.channelCount == 1 else { throw NSError(domain: "who-prefixes", code: 1, userInfo: [NSLocalizedDescriptionKey: "\(path) is not mono"]) }
    let buffer = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: AVAudioFrameCount(file.length))!
    try file.read(into: buffer)
    let samples = Array(UnsafeBufferPointer(start: buffer.floatChannelData![0], count: Int(buffer.frameLength)))
    return (samples, format.sampleRate)
}

let who = Who(directory: models, variant: .int8)
var start = Date()
try await who.download()  // weights are present (checked above), so this only loads them
let loadSeconds = Date().timeIntervalSince(start)

var cases: [String: Any] = [:]
for pair in args.dropFirst(4) {
    let parts = pair.split(separator: "=", maxSplits: 1).map(String.init)
    guard parts.count == 2 else { fputs("expected <case>=<call.wav>, got \(pair)\n", stderr); exit(2) }
    let (samples, rate) = try readMono(parts[1])
    let duration = Double(samples.count) / rate
    var lengths: [Double] = []
    var t = step
    while t < duration - 1e-6 { lengths.append(t); t += step }
    lengths.append(duration)
    var runs: [[String: Any]] = []
    for length in lengths {
        let count = min(samples.count, Int((length * rate).rounded()))
        start = Date()
        let result = try await who.diarize(samples: Array(samples[0..<count]), sampleRate: rate)
        let seconds = Date().timeIntervalSince(start)
        let segments: [[String: Any]] = result.turns.map {
            ["speaker_id": "Who_\($0.speaker)", "start_seconds": $0.start, "end_seconds": $0.end]
        }
        runs.append(["prefix_seconds": length, "diarize_seconds": seconds, "speaker_count": result.speakerCount,
                     "segments": segments])
    }
    cases[parts[0]] = ["duration_seconds": duration, "runs": runs]
    print("\(parts[0]): \(runs.count) prefixes of \(String(format: "%.1f", duration)) s")
}
let record: [String: Any] = [
    "model": "desert-ant-labs/who", "model_revision": WhoModel.revision, "sdk_version": WhoModel.sdkVersion,
    "variant": "int8", "load_seconds": loadSeconds, "step_seconds": step, "cases": cases,
]
try JSONSerialization.data(withJSONObject: record, options: [.prettyPrinted, .sortedKeys])
    .write(to: URL(fileURLWithPath: out))
