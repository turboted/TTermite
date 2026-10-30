import Foundation
import XCTest

final class ReleaseEnvironmentTests: XCTestCase {
    func testNativeAppHostUsesItsDeclaredIsolatedHome() throws {
        let expected = URL(fileURLWithPath: try XCTUnwrap(ProcessInfo.processInfo.environment["TTERMITE_TEST_HOME"])).resolvingSymlinksInPath()
        let actual = URL(fileURLWithPath: NSHomeDirectory()).resolvingSymlinksInPath()
        XCTAssertEqual(actual.path, expected.path, "A changed shell HOME is insufficient for native Foundation isolation.")
        let support = try XCTUnwrap(FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first).resolvingSymlinksInPath()
        XCTAssertTrue(support.path.hasPrefix(expected.path + "/"), "App data must stay inside the explicit test profile.")
    }
}
