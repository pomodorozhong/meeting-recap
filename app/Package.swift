// swift-tools-version:6.2
import PackageDescription

// The app prototype. It depends on nothing in experiments/ (decision 5); the recorder here is its own copy of the
// approach in experiments/capture/record.swift, rebuilt as a library.
let package = Package(
    name: "MeetingRecap",
    platforms: [.macOS(.v26)],
    products: [
        .executable(name: "MeetingRecap", targets: ["MeetingRecap"]),
    ],
    targets: [
        // Real recording: ScreenCaptureKit system audio plus the microphone, written to two lossless files.
        .target(name: "RecorderCore"),
        // SwiftUI shell. Recording is real; transcript and recap come from fixtures (Sources/MeetingRecap/Fixtures.swift).
        .executableTarget(name: "MeetingRecap", dependencies: ["RecorderCore"]),
        .testTarget(name: "RecorderCoreTests", dependencies: ["RecorderCore"]),
    ],
    swiftLanguageModes: [.v5]
)
