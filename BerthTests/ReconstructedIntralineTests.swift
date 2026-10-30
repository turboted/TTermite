import XCTest
@testable import TTermite
final class ReconstructedIntralineTests: XCTestCase {
    func testUnicodeGraphemesAndUnchangedText() {
        let result = IntralineDiff.changedRanges(old: "你好👨‍👩‍👧‍👦 alpha", new: "你好👨‍👩‍👧‍👦 beta")
        XCTAssertEqual(result.old, 4..<8)
        XCTAssertEqual(result.new, 4..<7)
        XCTAssertNil(IntralineDiff.changedRanges(old: "same", new: "same").old)
        XCTAssertNil(IntralineDiff.changedRanges(old: "abc", new: "XYZ").new)
    }
}
