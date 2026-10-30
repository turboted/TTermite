import Foundation
import XCTest
import Darwin
@testable import TTermite

@MainActor
final class ReconstructedDirectoryTests: XCTestCase {
    func testFileBrowserListsDirectoriesFirstAndHonorsHiddenFiles() throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent("ttermite-files-\(UUID())")
        try FileManager.default.createDirectory(at: root.appendingPathComponent("folder"), withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        for name in ["file10.txt", "file2.txt", ".hidden"] { try Data().write(to: root.appendingPathComponent(name)) }
        let visible = FileBrowserService.load(directory: root.path, showHidden: false)
        XCTAssertEqual(visible.map(\.name), ["folder", "file2.txt", "file10.txt"])
        XCTAssertTrue(visible[0].isDirectory)
        XCTAssertEqual(FileBrowserService.load(directory: root.path, showHidden: true).count, 4)
        XCTAssertTrue(FileBrowserService.load(directory: root.path + "/missing", showHidden: true).isEmpty)
    }

}
