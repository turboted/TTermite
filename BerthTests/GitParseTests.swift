import XCTest
@testable import TTermite

final class GitParseTests: XCTestCase {

    func testPorcelainV2Basic() {
        let text = """
        # branch.oid abc
        # branch.head main
        1 .M N... 100644 100644 100644 h1 h2 Sources/App.swift
        1 M. N... 100644 100644 100644 h1 h2 README.md
        1 MM N... 100644 100644 100644 h1 h2 Both.swift
        ? Untracked File.txt
        """
        let snapshot = GitParse.porcelainV2(text)
        XCTAssertEqual(snapshot.unstaged.map(\.path).sorted(), ["Both.swift", "Sources/App.swift"])
        XCTAssertEqual(snapshot.staged.map(\.path).sorted(), ["Both.swift", "README.md"])
        XCTAssertEqual(snapshot.untracked.map(\.path), ["Untracked File.txt"])
        XCTAssertEqual(snapshot.totalCount, 5)
    }

    func testPorcelainV2Rename() {
        let text = "2 R. N... 100644 100644 100644 h1 h2 R100 new/name.swift\told/name.swift"
        let snapshot = GitParse.porcelainV2(text)
        XCTAssertEqual(snapshot.staged.first?.path, "new/name.swift")
        XCTAssertEqual(snapshot.staged.first?.statusCode, "R")
    }

    func testNumstat() {
        let counts = GitParse.numstat("12\t3\tSources/App.swift\n-\t-\tImage.png\n")
        XCTAssertEqual(counts["Sources/App.swift"]?.added, 12)
        XCTAssertEqual(counts["Sources/App.swift"]?.removed, 3)
        XCTAssertEqual(counts["Image.png"]?.added, 0)
    }

    func testLog() {
        let commits = GitParse.log("abc123\tzc\t2 hours ago\tfix: something\tweird\n")
        XCTAssertEqual(commits.count, 1)
        XCTAssertEqual(commits[0].hash, "abc123")
        XCTAssertEqual(commits[0].subject, "fix: something\tweird")
    }

    func testNameStatusRename() {
        let entries = GitParse.nameStatus("M\ta.swift\nR100\told.swift\tnew.swift\n")
        XCTAssertEqual(entries[0].code, "M")
        XCTAssertEqual(entries[0].path, "a.swift")
        XCTAssertEqual(entries[1].code, "R")
        XCTAssertEqual(entries[1].path, "new.swift")
    }

    /// 终端里 `git config user.email …` 改完,状态栏得能发现:
    /// 指纹只看配置文件 mtime(零子进程),配置动过就必须变
    func testIdentityStampChangesWhenConfigChanges() throws {
        let root = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent("termite-git-\(UUID().uuidString)")
        let gitDir = root.appendingPathComponent(".git")
        try FileManager.default.createDirectory(at: gitDir, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let config = gitDir.appendingPathComponent("config")
        try "ref: refs/heads/feature/x\n".write(to: gitDir.appendingPathComponent("HEAD"), atomically: true, encoding: .utf8)
        try "[user]\n\temail = a@example.com\n".write(to: config, atomically: true, encoding: .utf8)

        XCTAssertEqual(GitProbe.branch(at: root.path), "feature/x")
        let before = GitProbe.identityStamp(at: root.path)
        XCTAssertEqual(GitProbe.identityStamp(at: root.path), before, "配置没动,指纹不该抖")

        Thread.sleep(forTimeInterval: 0.02) // 拉开 mtime
        try "[user]\n\temail = b@example.com\n".write(to: config, atomically: true, encoding: .utf8)
        XCTAssertNotEqual(GitProbe.identityStamp(at: root.path), before)
    }
}

