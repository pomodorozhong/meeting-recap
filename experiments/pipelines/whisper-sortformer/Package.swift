// swift-tools-version: 6.2
// Builds FluidAudio's fluidaudiocli at the pinned revision (the default diarizer, `sortformer`) and
// `who-diarize`, the optional Desert Ant Labs Who diarizer.
import PackageDescription
let package = Package(
    name: "pipeline-diarizer",
    platforms: [.macOS(.v15)],
    dependencies: [
        .package(url: "https://github.com/FluidInference/FluidAudio.git", revision: "ea500621819cadc46d6212af44624f2b45ab3240"),
        .package(url: "https://github.com/Desert-Ant-Labs/desert-ant-core.git", revision: "1a5efed67f44731b5eb5433aa9be3eebae05e269"),
    ],
    targets: [
        .executableTarget(name: "who-diarize", dependencies: [.product(name: "Who", package: "desert-ant-core")])
    ]
)
