// swift-tools-version: 6.0
import PackageDescription
let package = Package(
    name: "diarexp",
    platforms: [.macOS(.v14)],
    dependencies: [
        .package(url: "https://github.com/FluidInference/FluidAudio.git", revision: "ea500621819cadc46d6212af44624f2b45ab3240")
    ],
    targets: [
        .executableTarget(name: "diarexp", dependencies: [.product(name: "FluidAudio", package: "FluidAudio")])
    ]
)
