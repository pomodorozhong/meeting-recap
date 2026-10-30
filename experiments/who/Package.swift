// swift-tools-version: 6.2
import PackageDescription
let package = Package(
    name: "whoexp",
    platforms: [.macOS(.v15)],
    dependencies: [
        .package(url: "https://github.com/Desert-Ant-Labs/desert-ant-core.git", revision: "1a5efed67f44731b5eb5433aa9be3eebae05e269")
    ],
    targets: [
        .executableTarget(name: "whoexp", dependencies: [.product(name: "Who", package: "desert-ant-core")])
    ]
)
