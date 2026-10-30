import Foundation

/// Shared parsing for format detection and the table view (quoted fields included).
enum StructuredOutput {
    static func detect(_ text: String) -> StructuredOutputFormat? {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        if trimmed.first == "{" || trimmed.first == "[",
           let data = trimmed.data(using: .utf8),
           (try? JSONSerialization.jsonObject(with: data)) != nil { return .json }
        for (separator, format, minimum) in [(Character("\t"), StructuredOutputFormat.tsv, 2), (Character(","), .csv, 3)] {
            guard let rows = parseDelimited(trimmed, separator: separator, maxRows: 6), rows.count >= 2,
                  let count = rows.first?.count, count >= minimum,
                  rows.allSatisfy({ $0.count == count }) else { continue }
            return format
        }
        return nil
    }

    static func parseDelimited(_ text: String, separator: Character, maxRows: Int = 201) -> [[String]]? {
        guard maxRows > 0 else { return [] }
        var result: [[String]] = [], row: [String] = [], field = ""
        var quoted = false, afterQuote = false
        var iterator = text.makeIterator()
        var current = iterator.next()
        while let c = current {
            if quoted {
                if c == "\"" {
                    let next = iterator.next()
                    if next == "\"" { field.append("\""); current = iterator.next(); continue }
                    quoted = false; afterQuote = true; current = next; continue
                }
                field.append(c)
            } else if c == "\"", field.isEmpty, !afterQuote {
                quoted = true
            } else if c == separator {
                row.append(field); field = ""; afterQuote = false
            } else if c == "\n" || c == "\r\n" || c == "\r" {
                row.append(field)
                if row.count > 1 || !field.isEmpty { result.append(row) }
                if result.count >= maxRows { return result }
                row = []; field = ""; afterQuote = false
            } else {
                if afterQuote && !c.isWhitespace { return nil }
                if !afterQuote { field.append(c) }
            }
            current = iterator.next()
        }
        guard !quoted else { return nil }
        if !field.isEmpty || !row.isEmpty || afterQuote { row.append(field); result.append(row) }
        return result
    }
}
