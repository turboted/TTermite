import XCTest
import SwiftTerm
import AppKit
import SwiftData
@testable import TTermite
@MainActor
final class ReconstructedSnapshotTests: XCTestCase {
    func testSessionLayoutPersistsAndRestoresThroughSessionManager() throws {
        let url = FileManager.default.temporaryDirectory.appendingPathComponent("ttermite-layout-\(UUID()).json")
        defer { try? FileManager.default.removeItem(at: url) }
        let manager = SessionManager()
        let first = manager.open(spec: .localShell(directory: "/tmp"), autoConnect: false)
        first.ingest(bytes: Array("saved output\r\n".utf8))
        let second = manager.open(spec: .localShell(directory: "/"), autoConnect: false)
        let tab = try XCTUnwrap(manager.selectedTab)
        let splitID = UUID()
        tab.root = .branch(id: splitID, axis: .vertical, first: .leaf(first.id), second: .leaf(second.id))
        tab.focusedID = second.id; tab.customTitle = "restored project"
        tab.isCarousel = true; tab.isMaximized = false; tab.setRatio(0.35, for: splitID)
        // Retain one tab containing both sessions.
        manager.applyRestoredTabs([tab], selectedIndex: 0)
        manager.persistSessionSnapshot(to: url, includingTestSessions: true)
        let snapshot = try SessionSnapshot.decode(Data(contentsOf: url))
        XCTAssertEqual(snapshot.tabs.count, 1)
        let restored = SessionManager()
        let container = try ModelContainer(for: Host.self, HostGroup.self, SSHKeyRecord.self, PortForward.self, Snippet.self, Workspace.self, Trigger.self, configurations: ModelConfiguration(isStoredInMemoryOnly: true))
        XCTAssertTrue(restored.restoreSessionSnapshot(container: container, from: url))
        let restoredTab = try XCTUnwrap(restored.selectedTab)
        XCTAssertEqual(restoredTab.customTitle, "restored project")
        XCTAssertTrue(restoredTab.isCarousel)
        XCTAssertEqual(restoredTab.root.leafIDs().count, 2)
        XCTAssertEqual(restored.selected?.spec.localDirectory, "/")
        if case .branch(let id, let axis, _, _) = restoredTab.root {
            XCTAssertEqual(axis, .vertical)
            XCTAssertEqual(restoredTab.ratio(of: id), 0.35, accuracy: 0.001)
        } else { XCTFail("Split tree was not restored") }
        XCTAssertTrue(restored.sessions.contains { $0.snapshotScrollback().contains("saved output") })
        for item in manager.sessions { item.shutdown() }
        for item in restored.sessions { item.shutdown() }
    }

    func testRemoteSnapshotRetainsSSHIdentityAndRemoteDirectory() throws {
        let target = FileManager.default.temporaryDirectory.appendingPathComponent("ttermite-remote-layout-\(UUID()).json")
        defer { try? FileManager.default.removeItem(at: target) }
        let container = try ModelContainer(for: Host.self, HostGroup.self, SSHKeyRecord.self, PortForward.self, Snippet.self, Workspace.self, Trigger.self, configurations: ModelConfiguration(isStoredInMemoryOnly: true))
        let host = Host(label: "remote snapshot", hostname: "example.invalid", username: "tester")
        container.mainContext.insert(host)
        try container.mainContext.save()
        let manager = SessionManager()
        let session = manager.open(spec: HostSpec(host: host), autoConnect: false)
        session.prepareRestoredDirectory("/srv/project with ' quote")
        manager.persistSessionSnapshot(to: target, includingTestSessions: true)
        let restored = SessionManager()
        XCTAssertTrue(restored.restoreSessionSnapshot(container: container, from: target))
        XCTAssertEqual(restored.selected?.spec.hostname, "example.invalid")
        XCTAssertEqual(restored.selected?.spec.isLocal, false)
        XCTAssertEqual(restored.selected?.currentRemoteDirectory, "/srv/project with ' quote")
    }

}
