import XCTest
import AppKit
import SwiftTerm
@testable import TTermite
@MainActor
final class ReconstructedCursorTests: XCTestCase {
    func testCursorStopsBlinkingWhenPaneLosesFocus() {
        let terminal = BerthTerminalView(frame: .zero)
        terminal.getTerminal().setCursorStyle(.blinkBar)
        terminal.applyFocusCursorStyle(focused: false)
        XCTAssertEqual(terminal.getTerminal().options.cursorStyle, .steadyBar)
        terminal.applyFocusCursorStyle(focused: true)
        XCTAssertEqual(terminal.getTerminal().options.cursorStyle, .blinkBar)
        terminal.pauseCursorBlinkForInput()
        XCTAssertEqual(terminal.getTerminal().options.cursorStyle, .steadyBar)
    }

}
