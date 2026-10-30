import AppKit
import SwiftData

extension SessionManager {
    func persistSessionSnapshot(to target: URL = SessionSnapshot.url, includingTestSessions: Bool = false) {
        guard !isRestoringSnapshot else { return }
        if !includingTestSessions {
            guard ProcessInfo.processInfo.environment["BERTH_TRANSIENT_STORE"] != "1",
                  NSClassFromString("XCTestCase") == nil else { return }
        }
        func encode(_ node: PaneNode, tab: PaneTab) -> SessionSnapshot.Node? {
            switch node {
            case .leaf(let id):
                guard let session = session(id), !session.isSerial else { return nil }
                return .leaf(id: id, hostID: session.spec.hostID,
                    localDirectory: session.spec.isLocal ? (session.localWorkingDirectory ?? TerminalSession.localStartDirectory(session.spec.localDirectory)) : nil, scrollback: session.snapshotScrollback())
            case .branch(let id, let axis, let a, let b):
                let first = encode(a, tab: tab), second = encode(b, tab: tab)
                if let first, let second { return .split(axis: axis == .horizontal ? "h" : "v", ratio: tab.ratio(of: id), first: first, second: second) }
                return first ?? second
            }
        }
        let savedTabs = tabs.compactMap { tab -> SessionSnapshot.Tab? in
            guard let node = encode(tab.root, tab: tab) else { return nil }
            let remoteDirectories = Dictionary(uniqueKeysWithValues: tab.root.leafIDs().compactMap { id -> (UUID, String)? in
                guard let session = session(id), !session.spec.isLocal, let directory = session.currentRemoteDirectory else { return nil }
                return (id, directory)
            })
            return .init(root: node, focusedLeaf: tab.focusedID, title: tab.customTitle, carousel: tab.isCarousel, maximized: tab.isMaximized, remoteDirectories: remoteDirectories)
        }
        let frame = NSApp?.windows.first(where: { $0.identifier == MainWindowRaiser.identifier }).map { NSStringFromRect($0.frame) }
        let selectedSavedIndex = tabs.prefix(while: { $0.id != selectedTabID }).filter { tab in
            tab.root.leafIDs().contains { session($0)?.isSerial == false }
        }.count
        let snapshot = SessionSnapshot(selectedTab: min(selectedSavedIndex, max(0, savedTabs.count - 1)), tabs: savedTabs, windowFrame: frame)
        do {
            let data = try JSONEncoder().encode(snapshot)
            guard data.count <= 16 * 1024 * 1024 else { return }
            try FileManager.default.createDirectory(at: target.deletingLastPathComponent(), withIntermediateDirectories: true)
            try data.write(to: target, options: [.atomic])
        } catch { restoreWarning = "工作布局無法保存：\(error.localizedDescription)" }
    }

    func restoreSessionSnapshot(container: ModelContainer, from target: URL = SessionSnapshot.url) -> Bool {
        guard UserDefaults.standard.object(forKey: SettingsKeys.restoreSessions) as? Bool ?? true,
              tabs.isEmpty, let data = try? Data(contentsOf: target) else { return false }
        let snapshot: SessionSnapshot
        do { snapshot = try SessionSnapshot.decode(data) }
        catch { restoreWarning = "先前的布局檔案無法讀取，已使用一般恢復方式。"; return false }
        isRestoringSnapshot = true
        defer { isRestoringSnapshot = false }
        let context = ModelContext(container)
        let hosts = ((try? context.fetch(FetchDescriptor<Host>())) ?? []) + SSHConfigService.shared.mirrorHosts
        var restored: [PaneTab] = []
        for item in snapshot.tabs {
            var identities: [UUID: UUID] = [:], ratios: [UUID: Double] = [:]
            func make(_ node: SessionSnapshot.Node) -> PaneNode? {
                switch node {
                case .leaf(let oldID, let hostID, let localDirectory, let scrollback):
                    let spec: HostSpec
                    if let directory = localDirectory { spec = .localShell(directory: directory) }
                    else if hostID == HostSpec.localShellHostID { spec = .localShell() }
                    else if let host = hosts.first(where: { $0.id == hostID }) { spec = HostSpec.resolve(host, in: hosts) }
                    else { return nil }
                    let session = open(spec: spec, autoConnect: false)
                    if let directory = item.remoteDirectories?[oldID] { session.prepareRestoredDirectory(directory) }
                    session.restoreScrollback(scrollback)
                    identities[oldID] = session.id
                    return .leaf(session.id)
                case .split(let axis, let ratio, let a, let b):
                    let first = make(a), second = make(b)
                    if let first, let second {
                        let id = UUID(); ratios[id] = ratio
                        return .branch(id: id, axis: axis == "h" ? .horizontal : .vertical, first: first, second: second)
                    }
                    return first ?? second
                }
            }
            guard let node = make(item.root) else { continue }
            let tab = PaneTab(sessionID: node.firstLeaf)
            tab.root = node; tab.focusedID = identities[item.focusedLeaf] ?? node.firstLeaf
            tab.customTitle = item.title; tab.isCarousel = item.carousel; tab.isMaximized = item.maximized
            for (id, ratio) in ratios { tab.setRatio(ratio, for: id) }
            restored.append(tab)
        }
        applyRestoredTabs(restored, selectedIndex: snapshot.selectedTab)
        if let frame = snapshot.windowFrame {
            DispatchQueue.main.async {
                if let window = NSApp.windows.first(where: { $0.identifier == MainWindowRaiser.identifier }) {
                    let rect = NSRectFromString(frame)
                    if rect.width >= 760, rect.height >= 520, NSScreen.screens.contains(where: { $0.visibleFrame.intersects(rect) }) { window.setFrame(rect, display: true) }
                }
            }
        }
        return true
    }
}
