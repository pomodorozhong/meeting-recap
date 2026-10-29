import FluidAudio
import Foundation

// usage: diarexp <wav> <out.json> [key=value ...]
// keys: num, min, max, thr, minseg, excl, step, mingap, exovl, fa, fb
let args = CommandLine.arguments
let wav = URL(fileURLWithPath: args[1])
let out = URL(fileURLWithPath: args[2])
var config = OfflineDiarizerConfig()
for kv in args.dropFirst(3) {
    let parts = kv.split(separator: "=", maxSplits: 1).map(String.init)
    guard parts.count == 2 else { continue }
    let (k, v) = (parts[0], parts[1])
    switch k {
    case "num": config.clustering.numSpeakers = Int(v)
    case "min": config.clustering.minSpeakers = Int(v)
    case "max": config.clustering.maxSpeakers = Int(v)
    case "thr": config.clustering.threshold = Double(v)!
    case "fa": config.clustering.warmStartFa = Double(v)!
    case "fb": config.clustering.warmStartFb = Double(v)!
    case "minseg": config.embedding.minSegmentDurationSeconds = Double(v)!
    case "exovl": config.embedding.excludeOverlap = (v == "true")
    case "excl": config.postProcessing.exclusiveSegments = (v == "true")
    case "mingap": config.postProcessing.minGapDurationSeconds = Double(v)!
    case "step": config.segmentation.stepRatio = Double(v)!
    default: fputs("unknown key \(k)\n", stderr); exit(2)
    }
}

let manager = OfflineDiarizerManager(config: config)
try await manager.prepareModels()
let start = Date()
let result = try await manager.process(wav)
let elapsed = Date().timeIntervalSince(start)
let records: [[String: Any]] = result.segments.map {
    ["speaker_id": $0.speakerId, "start_seconds": $0.startTimeSeconds, "end_seconds": $0.endTimeSeconds]
}
let data = try JSONSerialization.data(withJSONObject: records, options: [.prettyPrinted, .sortedKeys])
try data.write(to: out)
var totals: [String: Float] = [:]
for s in result.segments { totals[s.speakerId, default: 0] += s.endTimeSeconds - s.startTimeSeconds }
let summary = totals.sorted(by: { $0.key < $1.key }).map { "\($0.key)=\(String(format: "%.0f", $0.value))" }.joined(separator: " ")
print("segments=\(result.segments.count) speakers=\(totals.count) seconds=\(String(format: "%.1f", elapsed)) \(summary)")
