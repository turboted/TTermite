import Foundation

struct PortEntry: Identifiable, Equatable {
    let pid: Int32
    let command: String
    let port: Int
    let address: String
    var id: String { "\(pid):\(port)" }
}

enum PortMonitor {
    /// lsof 列监听端口(仅当前用户可见的进程)
    static func listeningPorts() async -> [PortEntry] {
        await withCheckedContinuation { continuation in
            DispatchQueue.global(qos: .userInitiated).async {
                let process = Process()
                process.executableURL = URL(fileURLWithPath: "/usr/sbin/lsof")
                process.arguments = ["-nP", "-iTCP", "-sTCP:LISTEN"]
                let pipe = Pipe()
                process.standardOutput = pipe
                process.standardError = Pipe()
                do {
                    try process.run()
                } catch {
                    continuation.resume(returning: [])
                    return
                }
                let data = pipe.fileHandleForReading.readDataToEndOfFile()
                process.waitUntilExit()
                let text = String(data: data, encoding: .utf8) ?? ""
                continuation.resume(returning: parse(text))
            }
        }
    }

    /// lsof 标准表头输出:COMMAND PID USER ... NAME (LISTEN)
    /// NAME 形如 *:3000 / 127.0.0.1:5173 / [::1]:5173,后面还挂着 "(LISTEN)",
    /// 所以取「最后一个含 : 的列」而不是最后一列
    static func parse(_ text: String) -> [PortEntry] {
        var seen: Set<String> = []
        var result: [PortEntry] = []
        for line in text.components(separatedBy: "\n").dropFirst() where !line.isEmpty {
            let columns = line.split(separator: " ", omittingEmptySubsequences: true).map(String.init)
            guard columns.count >= 9,
                  let pid = Int32(columns[1]),
                  let name = columns.last(where: { $0.contains(":") }),
                  let separator = name.lastIndex(of: ":"),
                  let port = Int(name[name.index(after: separator)...]) else { continue }
            let host = String(name[..<separator])
            let address = host == "*" ? "*" : host.trimmingCharacters(in: CharacterSet(charactersIn: "[]"))
            let entry = PortEntry(pid: pid, command: columns[0], port: port, address: address)
            // IPv4/IPv6 各一行,去重
            if seen.insert(entry.id).inserted {
                result.append(entry)
            }
        }
        return result.sorted { $0.port < $1.port }
    }
}
