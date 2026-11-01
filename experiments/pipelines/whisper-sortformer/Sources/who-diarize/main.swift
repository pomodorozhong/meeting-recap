import Foundation
import Who

// usage: who-diarize <audio> <out.json> <models-dir> [--download]
// Diarizes with Who's int8 weights from <models-dir> and writes one JSON object: the model revision, SDK
// version, load and diarize times, and `segments` (speaker_id, start_seconds, end_seconds), every speaker kept.
// Without --download it refuses to run when <models-dir> holds no weights, so an offline run never fetches them.
// With --download and no audio ("-"), it only fetches and loads the weights.
let args = CommandLine.arguments
guard args.count >= 4 else {
    fputs("usage: who-diarize <audio|-> <out.json|-> <models-dir> [--download]\n", stderr)
    exit(2)
}
let audio = args[1], out = args[2], models = args[3]
let mayDownload = args.dropFirst(4).contains("--download")
// The SDK keeps each variant in its own folder; its metadata file is read at load, so it marks a complete download.
let present = FileManager.default.fileExists(atPath: "\(models)/coreml-int8/who_meta.json")
if !present && !mayDownload {
    fputs("no Who weights in \(models); run `recap.py setup --who` first\n", stderr)
    exit(3)
}

let who = Who(directory: models, variant: .int8)
var start = Date()
try await who.download()  // fetches the weights only when missing, then loads them
let loadSeconds = Date().timeIntervalSince(start)
if audio == "-" {
    print("Who \(WhoModel.revision) int8 ready in \(models)")
    exit(0)
}
start = Date()
let result = try await who.diarize(path: audio)  // decoding and resampling included
let diarizeSeconds = Date().timeIntervalSince(start)

let segments: [[String: Any]] = result.turns.map {
    ["speaker_id": "Who_\($0.speaker)", "start_seconds": $0.start, "end_seconds": $0.end]
}
let record: [String: Any] = [
    "model": "desert-ant-labs/who", "model_revision": WhoModel.revision, "sdk_version": WhoModel.sdkVersion,
    "variant": "int8", "load_seconds": loadSeconds, "diarize_seconds": diarizeSeconds,
    "duration_seconds": result.duration, "speaker_count": result.speakerCount, "segments": segments,
]
try JSONSerialization.data(withJSONObject: record, options: [.prettyPrinted, .sortedKeys])
    .write(to: URL(fileURLWithPath: out))
print("Who \(WhoModel.revision) int8: \(result.turns.count) turns, \(result.speakerCount) speakers, diarized in \(String(format: "%.1f", diarizeSeconds)) s")
