import XCTest
import AppKit
import SwiftTerm
@testable import TTermite
@MainActor
final class ReconstructedSerialTests: XCTestCase {
    func testSerialTransportWithPseudoTerminal() throws {
        let master = posix_openpt(O_RDWR | O_NOCTTY | O_NONBLOCK)
        XCTAssertGreaterThanOrEqual(master, 0)
        guard master >= 0 else { return }
        defer { Darwin.close(master) }
        XCTAssertEqual(grantpt(master), 0)
        XCTAssertEqual(unlockpt(master), 0)
        let path = String(cString: try XCTUnwrap(ptsname(master)))
        let slave = try XCTUnwrap(SerialPort.open(path: path, baud: 115200))
        defer { Darwin.close(slave) }
        let data = Array("serial bytes\n".utf8)
        XCTAssertEqual(Darwin.write(master, data, data.count), data.count)
        var pollFD = pollfd(fd: slave, events: Int16(POLLIN), revents: 0)
        XCTAssertEqual(poll(&pollFD, 1, 1000), 1)
        var bytes = [UInt8](repeating: 0, count: 128)
        let count = Darwin.read(slave, &bytes, bytes.count)
        XCTAssertEqual(Array(bytes.prefix(max(0, count))), data)
        let writer = FDWriter(fd: slave, queue: .main)
        writer.write(Data(data))
        var masterPoll = pollfd(fd: master, events: Int16(POLLIN), revents: 0)
        XCTAssertEqual(poll(&masterPoll, 1, 1000), 1)
        let returned = Darwin.read(master, &bytes, bytes.count)
        XCTAssertEqual(Array(bytes.prefix(max(0, returned))), data)
        writer.close()
    }
}
