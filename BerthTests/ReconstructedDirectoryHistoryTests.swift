import Foundation
import XCTest
@testable import TTermite
@MainActor
final class ReconstructedDirectoryHistoryTests: XCTestCase {
    func testRemoteHostsRemainSeparateAcrossReload() {
        let key = "directory.history"
        let before = UserDefaults.standard.object(forKey: key)
        defer { if let before { UserDefaults.standard.set(before, forKey: key) } else { UserDefaults.standard.removeObject(forKey: key) } }
        UserDefaults.standard.removeObject(forKey: key)
        let first = DirectoryHistory()
        first.record(path: "/srv/project", hostKey: "a@host:22")
        first.record(path: "/srv/project", hostKey: "b@host:22")
        first.record(path: "/srv/project", hostKey: "a@host:22")
        let reloaded = DirectoryHistory()
        XCTAssertEqual(reloaded.query("project", hostKey: "a@host:22").first?.visits, 2)
        XCTAssertEqual(reloaded.query("project", hostKey: "b@host:22").first?.visits, 1)
        XCTAssertTrue(reloaded.query("project", hostKey: "absent").isEmpty)
    }
}
