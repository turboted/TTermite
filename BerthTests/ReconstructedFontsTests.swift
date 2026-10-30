import AppKit
import CoreText
import XCTest
@testable import TTermite

@MainActor
final class ReconstructedFontsTests: XCTestCase {
    func testBundledFacesAndDeveloperGlyphs() throws {
        BundledFonts.register()
        let font = try XCTUnwrap(NSFont(name: FontPrefs.bundledFamily, size: 16))
        XCTAssertEqual(font.familyName, FontPrefs.bundledFamily)
        let resources = try XCTUnwrap(Bundle.main.resourceURL)
        let files = try XCTUnwrap(FileManager.default.enumerator(at: resources, includingPropertiesForKeys: nil))
        let names = files.compactMap { ($0 as? URL)?.lastPathComponent }
        for face in ["Regular", "Bold", "Italic", "BoldItalic"] {
            XCTAssertTrue(names.contains("JetBrainsMonoNerdFont-\(face).ttf"))
        }
        let symbols = try XCTUnwrap(NSFont(name: "SymbolsNF", size: 16))
        var character: UniChar = 0xe0b0
        var glyph: CGGlyph = 0
        XCTAssertTrue(CTFontGetGlyphsForCharacters(symbols as CTFont, &character, &glyph, 1))
        XCTAssertNotEqual(glyph, 0)
    }
}
