import XCTest
import SwiftTerm
import AppKit
@testable import TTermite
@MainActor
final class ReconstructedCommandCaptureTests: XCTestCase {
    func testCommandCycleCapturesTextOutputExitAndStructure() {
        let session = TerminalSession(spec: .localShell(directory: "/tmp"))
        session.ingest(bytes: Array("\u{1b}]133;A\u{7}$ \u{1b}]133;B\u{7}printf json\r\n\u{1b}]133;C\u{7}{\"value\":42}\r\n\u{1b}]133;D;0\u{7}".utf8))
        XCTAssertEqual(session.commandHistory.count, 1)
        guard let record = session.commandHistory.first else { return }
        XCTAssertTrue(record.commandText.contains("printf json"))
        XCTAssertEqual(record.exitCode, 0)
        XCTAssertEqual(record.structured, .json)
        XCTAssertTrue(session.outputText(of: record)?.contains("42") == true)
    }

    func testCommandCyclesWithNoOutputAndPreviousRun() {
        let session = TerminalSession(spec: .localShell(directory: "/tmp"))
        for result in ["first", "second"] {
            session.ingest(bytes: Array("\u{1b}]133;A\u{7}$ \u{1b}]133;B\u{7}echo test\r\n\u{1b}]133;C\u{7}\(result)\r\n\u{1b}]133;D;0\u{7}".utf8))
        }
        XCTAssertEqual(session.commandHistory.count, 2)
        if let last = session.commandHistory.last {
            XCTAssertNotNil(session.previousRun(of: last))
        }
        session.ingest(bytes: Array("\u{1b}]133;A\u{7}$ \u{1b}]133;B\u{7}false\r\n\u{1b}]133;C\u{7}\u{1b}]133;D;1\u{7}".utf8))
        XCTAssertEqual(session.commandHistory.last?.exitCode, 1)
        XCTAssertFalse(session.commandHistory.last?.hasOutput ?? true)
    }

}
