// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "TTermite",
    defaultLocalization: "zh-Hans",
    platforms: [.macOS("15.0")],
    products: [.executable(name: "TTermite", targets: ["TTermite"])],
    dependencies: [
        .package(path: "vendor/Citadel"),
        .package(url: "https://github.com/migueldeicaza/SwiftTerm.git", exact: "1.14.0"),
        .package(url: "https://github.com/apple/swift-collections.git", exact: "1.1.4"),
        .package(url: "https://github.com/apple/swift-nio.git", exact: "2.81.0"),
    ],
    targets: [
        .target(name: "PtySupport", path: "Berth/Core/Terminal", sources: ["BerthPtySpawn.c"], publicHeadersPath: "include"),
        .executableTarget(
            name: "TTermite",
            dependencies: ["PtySupport", "Citadel", .product(name: "SwiftTerm", package: "SwiftTerm")],
            path: "Berth",
            exclude: ["Info.plist", "Berth.entitlements", "Core/Terminal/BerthPtySpawn.c", "Core/Terminal/BerthPtySpawn.h", "Core/Terminal/include"],
            resources: [.copy("Resources")],
            linkerSettings: [.linkedLibrary("sqlite3")]
        ),
        .testTarget(name: "TTermiteTests", dependencies: ["TTermite"], path: "BerthTests")
    ],
    swiftLanguageVersions: [.v5]
)
