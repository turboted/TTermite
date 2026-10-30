import XCTest
@testable import TTermite
final class ReconstructedStructuredOutputTests: XCTestCase {
    func testQuotedCSVAndInvalidJSON() {
        XCTAssertEqual(StructuredOutput.detect("{\"value\":1}"), .json)
        XCTAssertNil(StructuredOutput.detect("{invalid}"))
        let csv = "name,city,note\nAlice,Taipei,\"a,b\""
        XCTAssertEqual(StructuredOutput.detect(csv), .csv)
        XCTAssertEqual(StructuredOutput.parseDelimited(csv, separator: ",")?.last, ["Alice", "Taipei", "a,b"])
        XCTAssertNil(StructuredOutput.parseDelimited("\"unclosed", separator: ","))
    }
}
