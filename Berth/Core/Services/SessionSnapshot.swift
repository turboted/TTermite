import Foundation

struct SessionSnapshot: Codable, Equatable {
    var version = 1
    var selectedTab: Int
    var tabs: [Tab]
    var windowFrame: String?

    struct Tab: Codable, Equatable {
        var root: Node
        var focusedLeaf: UUID
        var title: String?
        var carousel: Bool
        var maximized: Bool
        var remoteDirectories: [UUID: String]?
    }
    indirect enum Node: Codable, Equatable {
        case leaf(id: UUID, hostID: UUID, localDirectory: String?, scrollback: String)
        case split(axis: String, ratio: Double, first: Node, second: Node)
    }
    static var url: URL {
        FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("TTermite/sessions.json")
    }
    static func decode(_ data: Data) throws -> Self {
        guard data.count <= 16 * 1024 * 1024 else { throw SnapshotError.tooLarge }
        let result = try JSONDecoder().decode(Self.self, from: data)
        guard result.version == 1, result.tabs.count <= 100 else { throw SnapshotError.unsupported }
        func validate(_ node: Node, depth: Int = 0) throws {
            guard depth < 32 else { throw SnapshotError.tooLarge }
            if case .split(let axis, let ratio, let a, let b) = node {
                guard ["h", "v"].contains(axis), ratio.isFinite, (0.05...0.95).contains(ratio) else { throw SnapshotError.unsupported }
                try validate(a, depth: depth + 1); try validate(b, depth: depth + 1)
            }
        }
        try result.tabs.forEach { try validate($0.root) }
        return result
    }
    enum SnapshotError: Error { case tooLarge, unsupported }
}
