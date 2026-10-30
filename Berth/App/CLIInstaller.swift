// Adapted from xinghelee/Termite @ 95db043 (GPL-3.0).
import AppKit
import Foundation

/// 安裝使用者自己的命令列入口；不需要管理員權限。
enum CLIInstaller {

    static let scriptBody = """
    #!/bin/sh
    # TTermite CLI:在 TTermite 中打开目录(缺省当前目录)
    exec open -a TTermite "${1:-$PWD}"
    """

    @MainActor
    static func install(to destination: URL = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent(".local/bin/ttermite")) -> String {
        let target = destination.path
        do {
            try FileManager.default.createDirectory(atPath: (target as NSString).deletingLastPathComponent, withIntermediateDirectories: true)
            try scriptBody.write(toFile: target, atomically: true, encoding: .utf8)
            try FileManager.default.setAttributes([.posixPermissions: 0o755], ofItemAtPath: target)
            return String(localized: "已安装:\(target)")
        } catch { return "安裝失敗：\(error.localizedDescription)" }
    }
}
