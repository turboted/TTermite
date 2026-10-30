import XCTest
@testable import TTermite
final class ReconstructedShellHooksTests: XCTestCase {
    func testExistingZshConfigurationIsRetained() {
        var environment = ["ZDOTDIR": "/tmp/original-config", "CUSTOM": "preserved"]
        ShellIntegration.apply(to: &environment, shellPath: "/bin/zsh")
        XCTAssertEqual(environment["TERMITE_ORIG_ZDOTDIR"], "/tmp/original-config")
        XCTAssertEqual(environment["CUSTOM"], "preserved")
        XCTAssertEqual(environment["ZDOTDIR"], ShellIntegration.directory.appendingPathComponent("zdotdir").path)
        var bash = [String: String]()
        ShellIntegration.apply(to: &bash, shellPath: "/bin/bash")
        XCTAssertFalse(bash["PROMPT_COMMAND", default: ""].isEmpty)
    }
}
