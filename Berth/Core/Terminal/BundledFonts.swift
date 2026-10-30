import AppKit
import CoreText

enum BundledFonts {
    static func register() {
        #if SWIFT_PACKAGE
        let bundle = Bundle.module
        #else
        let bundle = Bundle.main
        #endif
        guard let root = bundle.resourceURL else { return }
        for folder in [root.appendingPathComponent("Resources/Fonts"), root.appendingPathComponent("Fonts"), root] {
            for url in (try? FileManager.default.contentsOfDirectory(at: folder, includingPropertiesForKeys: nil)) ?? [] where url.pathExtension == "ttf" {
                CTFontManagerRegisterFontsForURL(url as CFURL, .process, nil)
            }
        }
    }
}
