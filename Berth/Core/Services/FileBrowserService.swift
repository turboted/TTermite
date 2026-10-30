import Foundation

enum FileBrowserService {
    static func load(directory: String, showHidden: Bool) -> [FileEntry] {
        let fm = FileManager.default
        let names = (try? fm.contentsOfDirectory(atPath: directory)) ?? []
        return names
            .filter { showHidden || !$0.hasPrefix(".") }
            .map { name -> FileEntry in
                let path = (directory as NSString).appendingPathComponent(name)
                var isDir: ObjCBool = false
                fm.fileExists(atPath: path, isDirectory: &isDir)
                return FileEntry(name: name, path: path, isDirectory: isDir.boolValue)
            }
            .sorted {
                if $0.isDirectory != $1.isDirectory { return $0.isDirectory }
                return $0.name.localizedStandardCompare($1.name) == .orderedAscending
            }
    }
}

struct FileEntry: Identifiable {
    var id: String { path }
    let name: String
    let path: String
    let isDirectory: Bool
}
