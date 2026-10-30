import XCTest
@testable import TTermite
final class ReconstructedSyntaxTests: XCTestCase {
    func testHighlightLargeSourceIsLinear() {
        // 源码视图路径:512KB 上限下的大文件着色
        let line = "func compute(_ input: Int) -> String { let value = input * 42; return \"result \\(value)\" } // note\n"
        let source = String(repeating: line, count: 3000) // ~300KB
        let theme = TerminalTheme.midnight
        let start = Date()
        let out = CodeHighlighter.highlight(source, fileExtension: "swift", theme: theme)
        let elapsed = Date().timeIntervalSince(start)
        print("[perf] ~300KB swift 着色: \(String(format: "%.0f", elapsed * 1000))ms")
        XCTAssertNotNil(out)
        XCTAssertLessThan(elapsed, 2.0, "大文件着色不应是平方复杂度")
    }
}
