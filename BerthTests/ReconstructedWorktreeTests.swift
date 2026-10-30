import Foundation
import XCTest
@testable import TTermite
final class ReconstructedWorktreeTests: XCTestCase {
    func testActualCreateOpenAndRemovePreservesBranch() async throws {
        let folder = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        let repo = folder.appendingPathComponent("repo")
        try FileManager.default.createDirectory(at: repo, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: folder) }
        for args in [["init", "-q"], ["-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "base", "--allow-empty"]] {
            let result = await GitService.runResult(args, in: repo.path)
            XCTAssertEqual(result.exitCode, 0, result.output)
        }
        let path = try await WorktreeService.add(near: repo.path, target: .newBranch("feature-test"))
        XCTAssertTrue(FileManager.default.fileExists(atPath: path + "/.git"))
        let same = try await WorktreeService.add(near: repo.path, target: .openWorktree(path: path, branch: "feature-test"))
        XCTAssertEqual(same, path)
        try await WorktreeService.remove(worktreePath: path, force: false)
        XCTAssertFalse(FileManager.default.fileExists(atPath: path))
        let result = await GitService.runResult(["show-ref", "--verify", "refs/heads/feature-test"], in: repo.path)
        XCTAssertEqual(result.exitCode, 0)
    }
}
