import Foundation

/// 直读 .git/HEAD 拿当前分支(零子进程):从 path 逐级向上找 .git。
/// 向上不越过家目录,减少对受 TCC 保护目录(文稿/桌面等)的主动触碰。
enum GitProbe {
    static func branch(at path: String) -> String? {
        guard let gitDir = gitDirectory(at: path),
              let head = try? String(contentsOf: gitDir.appendingPathComponent("HEAD"), encoding: .utf8)
                  .trimmingCharacters(in: .whitespacesAndNewlines) else { return nil }
        if head.hasPrefix("ref: refs/heads/") {
            return String(head.dropFirst("ref: refs/heads/".count))
        }
        return String(head.prefix(8)) // detached HEAD:短 hash
    }

    /// 提交身份相关配置文件的 mtime 指纹(仓库级 + 全局):纯 stat,零子进程。
    /// 状态栏拿它判断「要不要再花几个 git config 子进程读身份」
    static func identityStamp(at path: String) -> String {
        let home = FileManager.default.homeDirectoryForCurrentUser
        var files = [
            home.appendingPathComponent(".gitconfig"),
            home.appendingPathComponent(".config/git/config"),
        ]
        if let gitDir = gitDirectory(at: path) {
            files.append(gitDir.appendingPathComponent("config"))
            // 链接 worktree 的 .git 指向 <main>/.git/worktrees/<name>,
            // user.* 落在主仓库的 config 上,顺着 commondir 一并盯住
            if let common = try? String(contentsOf: gitDir.appendingPathComponent("commondir"), encoding: .utf8)
                .trimmingCharacters(in: .whitespacesAndNewlines), !common.isEmpty {
                let resolved = common.hasPrefix("/")
                    ? URL(fileURLWithPath: common)
                    : gitDir.appendingPathComponent(common).standardizedFileURL
                files.append(resolved.appendingPathComponent("config"))
            }
        }
        return files.map { file in
            let attributes = try? FileManager.default.attributesOfItem(atPath: file.path)
            let modified = attributes?[.modificationDate] as? Date
            return "\(file.path):\(modified?.timeIntervalSince1970 ?? 0)"
        }.joined(separator: "|")
    }

    /// 向上找到 cwd 所属仓库的 .git 目录(worktree/submodule 的 gitdir 指针也解析)
    private static func gitDirectory(at path: String) -> URL? {
        let home = FileManager.default.homeDirectoryForCurrentUser.path
        var dir = URL(fileURLWithPath: path)
        for _ in 0..<24 {
            if let gitDir = resolveGitDir(at: dir) { return gitDir }
            // 家目录和根目录是遍历上界(家目录本身极少是仓库,其下受保护目录不再触碰)
            if dir.path == home || dir.path == "/" { return nil }
            let parent = dir.deletingLastPathComponent()
            if parent.path == dir.path { return nil }
            dir = parent
        }
        return nil
    }

    private static func resolveGitDir(at dir: URL) -> URL? {
        let gitPath = dir.appendingPathComponent(".git")
        var isDirectory: ObjCBool = false
        guard FileManager.default.fileExists(atPath: gitPath.path, isDirectory: &isDirectory) else { return nil }
        guard !isDirectory.boolValue else { return gitPath }
        // worktree/submodule:.git 是一个 "gitdir: <path>" 文件
        guard let content = try? String(contentsOf: gitPath, encoding: .utf8),
              let gitdir = content.split(separator: ":").dropFirst().first?
                  .trimmingCharacters(in: .whitespacesAndNewlines) else { return nil }
        return gitdir.hasPrefix("/")
            ? URL(fileURLWithPath: gitdir)
            : dir.appendingPathComponent(gitdir).standardizedFileURL
    }
}

/// 结构化输出格式
enum StructuredOutputFormat: String {
    case json, csv, tsv

    var separator: String { self == .tsv ? "\t" : "," }
    var label: String { self == .json ? "JSON" : String(localized: "表格") }
    var symbol: String { self == .json ? "curlybraces" : "tablecells" }
}

/// 一条完整的命令周期记录(OSC 133 C→D):驱动命令时间线面板
struct CommandRecord: Identifiable, Equatable {
    let id = UUID()
    /// 命令行文本(提示符行..输出起始行的原样内容,含提示符前缀)
    let commandText: String
    /// 提示符所在 scroll-invariant 行(跳转定位用)
    let promptRow: Int?
    /// 输出区间 [outputStart, outputEnd)
    let outputStart: Int
    let outputEnd: Int
    let exitCode: Int?
    let duration: TimeInterval?
    let finishedAt: Date
    /// 输出嗅探出的结构化格式(驱动状态栏「查看」按钮)
    var structured: StructuredOutputFormat?

    var hasOutput: Bool { outputEnd > outputStart }
    var succeeded: Bool { (exitCode ?? 0) == 0 }
}


// Adapted from Termite @ 95db043, GPL-3.0.
enum PaneAttention: Equatable {
    case none
    /// 前台程序停下来等用户(fromBell:程序主动摇铃;否则为静默启发式判定)
    case needsInput(fromBell: Bool)
    /// 长命令在失焦 pane 跑完(failed:退出码非 0)
    case finished(failed: Bool)

    var needsInput: Bool {
        if case .needsInput = self { return true }
        return false
    }

    var isActive: Bool { self != .none }
}

/// 失焦 pane 命令结束时的一次性边框闪烁(绿=成功,红=失败)
struct FinishFlash: Equatable {
    let failed: Bool
    let at: Date
}

/// 静默启发式:TUI(如 Claude Code)不发 OSC 133 提示符标记,无法直接知道它何时停下,
/// 用「持续输出一段时间后突然静默」近似「停下来等输入」。
/// vim 一类打开后就安静的程序不满足持续输出条件,不误报。
struct SilenceHeuristic {
    /// 输出间隔超过该值视为一段新输出(agent 干活时至少每秒都在刷屏)
    var streakGap: TimeInterval = 2
    /// 输出需持续这么久才算「在干活」(短促输出后的静默不算)
    var minStreak: TimeInterval = 5
    /// 静默达到该时长即判定「在等输入」
    var silenceThreshold: TimeInterval = 6

    private(set) var lastOutputAt: Date?
    private(set) var streakStart: Date?

    mutating func recordOutput(at now: Date = Date()) {
        if let last = lastOutputAt, now.timeIntervalSince(last) <= streakGap {
            if streakStart == nil { streakStart = last }
        } else {
            streakStart = now
        }
        lastOutputAt = now
    }

    /// 距静默判定点还差多久(≤0 即已达标;从未有输出返回 nil)
    func remainingSilence(at now: Date = Date()) -> TimeInterval? {
        guard let last = lastOutputAt else { return nil }
        return silenceThreshold - now.timeIntervalSince(last)
    }

    /// 静默前的最后一段输出是否够长(证明之前真在干活)
    func hadBusyStreak() -> Bool {
        guard let start = streakStart, let last = lastOutputAt else { return false }
        return last.timeIntervalSince(start) >= minStreak
    }
}
