import Foundation
import Who

// usage: whoexp <audio> <out.json> [variant=fp16|int8] [models=<dir>]
// Writes `segments` JSON (speaker_id, start_seconds, end_seconds) to <out.json>, every speaker kept,
// and prints one JSON line with the speaker count and the load and diarize times.
let args = CommandLine.arguments
guard args.count >= 3 else {
    fputs("usage: whoexp <audio> <out.json> [variant=fp16|int8] [models=<dir>]\n", stderr)
    exit(2)
}
let audio = args[1]
let out = URL(fileURLWithPath: args[2])
var variant = ModelVariant.fp16
var models: String? = nil
for kv in args.dropFirst(3) {
    let parts = kv.split(separator: "=", maxSplits: 1).map(String.init)
    guard parts.count == 2 else { fputs("bad argument \(kv)\n", stderr); exit(2) }
    switch parts[0] {
    case "variant":
        guard let v = ModelVariant(rawValue: parts[1]) else { fputs("unknown variant \(parts[1])\n", stderr); exit(2) }
        variant = v
    case "models": models = parts[1]
    default: fputs("unknown key \(parts[0])\n", stderr); exit(2)
    }
}

let who = Who(directory: models, variant: variant)
let downloaded = who.isDownloaded()
var start = Date()
try await who.download()  // fetches the model only when missing, then loads it
let loadSeconds = Date().timeIntervalSince(start)
start = Date()
let result = try await who.diarize(path: audio)  // decoding and resampling included
let diarizeSeconds = Date().timeIntervalSince(start)

let records: [[String: Any]] = result.turns.map {
    ["speaker_id": String($0.speaker), "start_seconds": $0.start, "end_seconds": $0.end]
}
try JSONSerialization.data(withJSONObject: records, options: [.prettyPrinted, .sortedKeys]).write(to: out)
var totals: [String: Double] = [:]
for t in result.turns { totals[String(t.speaker), default: 0] += t.duration }
let summary: [String: Any] = [
    "variant": variant.rawValue, "model_revision": WhoModel.revision, "sdk_version": WhoModel.sdkVersion,
    "model_was_downloaded": downloaded, "load_seconds": loadSeconds, "diarize_seconds": diarizeSeconds,
    "duration_seconds": result.duration, "turns": result.turns.count, "speaker_count": result.speakerCount,
    "speaker_seconds": totals,
]
print(String(data: try JSONSerialization.data(withJSONObject: summary, options: [.sortedKeys]), encoding: .utf8)!)
