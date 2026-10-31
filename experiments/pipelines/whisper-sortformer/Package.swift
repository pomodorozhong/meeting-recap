// swift-tools-version: 6.0
// Builds FluidAudio's fluidaudiocli at the pinned revision; the pipeline runs its `sortformer` command.
import PackageDescription
let package = Package(
    name: "pipeline-diarizer",
    platforms: [.macOS(.v14)],
    dependencies: [
        .package(url: "https://github.com/FluidInference/FluidAudio.git", revision: "ea500621819cadc46d6212af44624f2b45ab3240")
    ],
    targets: []
)
