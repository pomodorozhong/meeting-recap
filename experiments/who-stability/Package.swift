// swift-tools-version: 6.2
// Builds `who-prefixes`, which loads Who once and diarizes growing prefixes of each recording.
// Who is pinned to the same desert-ant-core revision as experiments/pipelines/whisper-sortformer.
import PackageDescription
let package = Package(
    name: "who-stability",
    platforms: [.macOS(.v15)],
    dependencies: [
        .package(url: "https://github.com/Desert-Ant-Labs/desert-ant-core.git", revision: "1a5efed67f44731b5eb5433aa9be3eebae05e269"),
    ],
    targets: [
        .executableTarget(name: "who-prefixes", dependencies: [.product(name: "Who", package: "desert-ant-core")])
    ]
)
