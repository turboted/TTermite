import Foundation
import XCTest
import Darwin
@testable import TTermite

@MainActor
final class ReconstructedCLIInstallerTests: XCTestCase {
    func testCLIInstallerCreatesExecutableScriptAndReinstalls() throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent("ttermite-cli-\(UUID())")
        defer { try? FileManager.default.removeItem(at: root) }
        let path = root.appendingPathComponent("bin/ttermite")
        _ = CLIInstaller.install(to: path)
        XCTAssertEqual(try String(contentsOf: path, encoding: .utf8), CLIInstaller.scriptBody)
        XCTAssertTrue(FileManager.default.isExecutableFile(atPath: path.path))
        _ = CLIInstaller.install(to: path)
        let process = Process(); process.executableURL = URL(fileURLWithPath: "/bin/sh")
        process.arguments = ["-n", path.path]
        try process.run(); process.waitUntilExit()
        XCTAssertEqual(process.terminationStatus, 0)
    }

}
