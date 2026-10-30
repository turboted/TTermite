// Adapted from xinghelee/Termite @ 95db043 (GPL-3.0).
import SwiftUI

/// unified diff 内容:hunk 分隔条 + 双列行号 + 绿增红删(面板与放大 sheet 共用)。
/// 每个 hunk 渲染为单个 AttributedString 文本:行永不换行,靠横向滚动查看,
/// (LazyVStack 在双向 ScrollView 里只给行视口宽度,会把长行折叠成一团)
struct GitDiffContent: View {
    let hunks: [UnifiedDiff.Hunk]
    var fontSize: CGFloat = 11
    /// 自动换行:开 = 纵向滚动内软换行;关 = 横向滚动看原始排版
    var wrap = true

    private var theme: TerminalTheme { ThemeStore.shared.current }

    var body: some View {
        if wrap {
            ScrollView(.vertical) {
                content
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
        } else {
            // 双向 ScrollView 会把比视口窄的内容居中;强制至少视口尺寸 + 左上对齐
            GeometryReader { geo in
                ScrollView([.vertical, .horizontal]) {
                    content
                        .frame(minWidth: geo.size.width, minHeight: geo.size.height, alignment: .topLeading)
                }
            }
        }
    }

    private var content: some View {
        VStack(alignment: .leading, spacing: 4) {
            ForEach(hunks) { hunk in
                hunkHeader(hunk)
                Text(attributedLines(of: hunk))
                    .font(.system(size: fontSize, design: .monospaced))
                    .lineSpacing(1)
                    .textSelection(.enabled)
                    .padding(.horizontal, 10)
                    .frame(maxWidth: wrap ? .infinity : nil, alignment: .leading)
            }
        }
        .padding(.vertical, 8)
    }

    private func hunkHeader(_ hunk: UnifiedDiff.Hunk) -> some View {
        HStack(spacing: 6) {
            Image(systemName: "ellipsis")
                .font(.system(size: 8))
            Text("第 \(hunk.oldStart) → \(hunk.newStart) 行")
            if !hunk.header.isEmpty {
                Text(hunk.header)
                    .lineLimit(1)
                    .truncationMode(.tail)
            }
        }
        .font(.system(size: fontSize - 1, design: .monospaced))
        .foregroundStyle(theme.accentColor.opacity(0.85))
        .padding(.horizontal, 10)
        .padding(.vertical, 3)
        .background(Capsule().fill(theme.accentSoft.opacity(0.5)))
        .padding(.horizontal, 8)
    }

    private func attributedLines(of hunk: UnifiedDiff.Hunk) -> AttributedString {
        // 词级强调:删/增行配对后,真正变化的中段加深底色
        let emphasis = IntralineDiff.emphasis(for: hunk.lines)
        var result = AttributedString()
        for (index, line) in hunk.lines.enumerated() {
            var numbers = AttributedString(pad(line.oldNumber) + " " + pad(line.newNumber) + "  ")
            numbers.foregroundColor = Color.primary.opacity(0.28)

            let marker: String
            let color: Color
            var background: Color?
            var strongBackground: Color?
            switch line.kind {
            case .added:
                marker = "+ "; color = .green
                background = Color.green.opacity(0.13)
                strongBackground = Color.green.opacity(0.34)
            case .removed:
                marker = "− "; color = .red
                background = Color.red.opacity(0.13)
                strongBackground = Color.red.opacity(0.34)
            case .context:
                marker = "  "; color = Color.primary.opacity(0.72)
            }
            var content = AttributedString(marker + (line.text.isEmpty ? " " : line.text))
            content.foregroundColor = color
            if let background {
                numbers.backgroundColor = background
                content.backgroundColor = background
            }
            if let strongBackground, let changed = emphasis[index], !line.text.isEmpty {
                // marker 占 2 字符,把字符区间映射到 AttributedString 索引
                let start = content.index(content.startIndex, offsetByCharacters: min(changed.lowerBound + 2, line.text.count + 2))
                let end = content.index(content.startIndex, offsetByCharacters: min(changed.upperBound + 2, line.text.count + 2))
                if start < end {
                    content[start..<end].backgroundColor = strongBackground
                }
            }
            result += numbers
            result += content
            if index < hunk.lines.count - 1 {
                result += AttributedString("\n")
            }
        }
        return result
    }

    private func pad(_ number: Int?) -> String {
        let text = number.map(String.init) ?? ""
        return String(repeating: " ", count: max(0, 5 - text.count)) + text
    }
}

/// 状态码色点:M 黄 / A·? 绿 / D 红 / R·C 蓝 / U 橙
struct GitStatusDot: View {
    let code: String

    private var color: Color {
        switch code {
        case "M": return .yellow
        case "A", "?": return .green
        case "D": return .red
        case "R", "C": return .blue
        case "U": return .orange
        default: return .gray
        }
    }

    var body: some View {
        Text(code)
            .font(.system(size: 9, weight: .bold, design: .monospaced))
            .foregroundStyle(color)
            .frame(width: 13, height: 13)
            .background(Circle().fill(color.opacity(0.18)))
    }
}
