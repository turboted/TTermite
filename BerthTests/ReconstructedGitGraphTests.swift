import Foundation
import XCTest
@testable import TTermite

final class GitGraphTests: XCTestCase {

    private func commit(_ hash: String, parents: [String], refs: [String] = []) -> GraphCommitInfo {
        GraphCommitInfo(hash: hash, shortHash: hash, parents: parents, author: "a", relativeDate: "now", refs: refs, subject: "s")
    }

    func testLinearHistorySingleLane() {
        let rows = GitGraph.computeRows([
            commit("c", parents: ["b"]),
            commit("b", parents: ["a"]),
            commit("a", parents: []),
        ])
        XCTAssertEqual(rows.map(\.lane), [0, 0, 0])
        XCTAssertEqual(rows.map(\.laneCount), [1, 1, 1])
        XCTAssertFalse(rows[0].hasTopLine)
        XCTAssertTrue(rows[1].hasTopLine)
        XCTAssertTrue(rows[0].continuesDown)
        XCTAssertFalse(rows[2].continuesDown)
    }

    func testMergeCommitOpensSecondLane() {
        // m 是 merge(父 a、b);a、b 各自是根
        let rows = GitGraph.computeRows([
            commit("m", parents: ["a", "b"]),
            commit("b", parents: []),
            commit("a", parents: []),
        ])
        // m 在 0 道,第二父 b 分出到 1 道
        XCTAssertEqual(rows[0].lane, 0)
        XCTAssertEqual(rows[0].branchesOut, [1])
        XCTAssertEqual(rows[0].laneCount, 2)
        // b 落在 1 道且上方有来线
        let rowB = rows.first { $0.commit.hash == "b" }!
        XCTAssertEqual(rowB.lane, 1)
        XCTAssertTrue(rowB.hasTopLine)
        // a 在 0 道
        let rowA = rows.first { $0.commit.hash == "a" }!
        XCTAssertEqual(rowA.lane, 0)
    }

    func testBranchTipJoinsExistingLane() {
        // 两个分支顶端(t1、t2)都指向同一父 p:t2 的首父已被 0 道跟踪 → 并入
        let rows = GitGraph.computeRows([
            commit("t1", parents: ["p"]),
            commit("t2", parents: ["p"]),
            commit("p", parents: []),
        ])
        let rowT2 = rows[1]
        XCTAssertEqual(rowT2.lane, 1)
        XCTAssertEqual(rowT2.branchesOut, [0])
        XCTAssertFalse(rowT2.continuesDown)
        // p 收到两条线,单泳道
        let rowP = rows[2]
        XCTAssertEqual(rowP.lane, 0)
        XCTAssertTrue(rowP.hasTopLine)
    }

    func testParseLogRefs() {
        let line = "abc\u{1f}abc\u{1f}p1 p2\u{1f}zc\u{1f}2 天前\u{1f}HEAD -> main, origin/main, tag: v1.0\u{1f}subject here"
        let commits = GitGraph.parseLog(line)
        XCTAssertEqual(commits.count, 1)
        XCTAssertEqual(commits[0].parents, ["p1", "p2"])
        XCTAssertEqual(commits[0].refs, ["HEAD -> main", "origin/main", "tag: v1.0"])
        XCTAssertEqual(commits[0].subject, "subject here")
    }
}

// Termite cast playback and daemon snapshot tests are outside this port.
// TTermite snapshot and PTY coverage lives in PortedFeatureTests and Tests/CoreIntegrationTests.
