import XCTest
import AppKit
import SwiftTerm
@testable import TTermite
@MainActor
final class ReconstructedTerminalSearchTests: XCTestCase {
    func testTerminalSearchRegexCaseAndRestoration() {
        let terminal = BerthTerminalView(frame: NSRect(x: 0, y: 0, width: 800, height: 600))
        terminal.feed(text: "alpha 12\r\nALPHA 34\r\nbeta\r\n")
        let model = TerminalSearchModel()
        model.terminalView = terminal
        let original = terminal.allowMouseReporting
        model.activate()
        model.query = "alpha"; model.update()
        XCTAssertEqual(model.matchTotal, 2)
        model.caseSensitive = true; model.update()
        XCTAssertEqual(model.matchTotal, 1)
        model.useRegex = true; model.query = "[0-9]+"; model.update()
        XCTAssertEqual(model.matchTotal, 2)
        model.query = "[invalid"; model.update()
        XCTAssertEqual(model.matchTotal, 0)
        model.close()
        XCTAssertEqual(terminal.allowMouseReporting, original)
    }

}
