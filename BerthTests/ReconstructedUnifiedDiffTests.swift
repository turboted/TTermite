import Foundation
import XCTest
@testable import TTermite

final class UnifiedDiffTests: XCTestCase {

    private let sample = """
    diff --git a/file.swift b/file.swift
    index abc..def 100644
    --- a/file.swift
    +++ b/file.swift
    @@ -10,4 +10,5 @@ func demo() {
     context1
    -removed line
    +added line 1
    +added line 2
     context2
    """

    func testParseHunk() {
        let hunks = UnifiedDiff.parse(sample)
        XCTAssertEqual(hunks.count, 1)
        let hunk = hunks[0]
        XCTAssertEqual(hunk.oldStart, 10)
        XCTAssertEqual(hunk.newStart, 10)
        XCTAssertEqual(hunk.header, "func demo() {")
        XCTAssertEqual(hunk.lines.count, 5)
    }

    func testLineNumbers() {
        let lines = UnifiedDiff.parse(sample)[0].lines
        // context1: old 10 / new 10
        XCTAssertEqual(lines[0].oldNumber, 10)
        XCTAssertEqual(lines[0].newNumber, 10)
        // removed: old 11, new nil
        XCTAssertEqual(lines[1].kind, .removed)
        XCTAssertEqual(lines[1].oldNumber, 11)
        XCTAssertNil(lines[1].newNumber)
        // added 1: new 11
        XCTAssertEqual(lines[2].kind, .added)
        XCTAssertEqual(lines[2].newNumber, 11)
        // context2: old 12 / new 13
        XCTAssertEqual(lines[4].oldNumber, 12)
        XCTAssertEqual(lines[4].newNumber, 13)
    }

    func testStats() {
        let stats = UnifiedDiff.stats(UnifiedDiff.parse(sample))
        XCTAssertEqual(stats.added, 2)
        XCTAssertEqual(stats.removed, 1)
    }

    func testMultipleHunksAndNoNewlineMarker() {
        let text = """
        @@ -1,2 +1,2 @@
        -a
        +b
         c
        @@ -9,1 +9,1 @@
        -x
        +y
        \\ No newline at end of file
        """
        let hunks = UnifiedDiff.parse(text)
        XCTAssertEqual(hunks.count, 2)
        XCTAssertEqual(hunks[1].oldStart, 9)
        XCTAssertEqual(UnifiedDiff.stats(hunks).added, 2)
    }
}

