#!/usr/bin/env python3
"""Read CRSF RC channels from an ELRS receiver over USB TTL UART.

Read-only diagnostic. Never issues AMR movement commands.
"""
import argparse
import time
from collections import Counter

import serial
from serial.tools import list_ports

CRC_POLY = 0xD5
RC_CHANNELS_PACKED = 0x16
RC_PAYLOAD_SIZE = 22


def crc8_dvb_s2(data: bytes) -> int:
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ CRC_POLY) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def find_pl2303() -> str:
    ports = [
        p for p in list_ports.comports()
        if p.vid == 0x067B and p.pid == 0x2303
    ]
    if len(ports) != 1:
        items = [f"{p.device} [{p.description}]" for p in list_ports.comports()]
        raise SystemExit(
            f"Expected exactly one PL2303 (067B:2303), found {len(ports)}. "
            f"Available: {items}"
        )
    return ports[0].device


def decode_channels(payload: bytes) -> list[int]:
    if len(payload) != RC_PAYLOAD_SIZE:
        raise ValueError("RC payload must be 22 bytes")
    bits = int.from_bytes(payload, "little")
    return [(bits >> (11 * i)) & 0x7FF for i in range(16)]


def extract_frames(buffer: bytearray):
    """Resynchronize on frame boundaries and validate CRC.

    CRSF: sync/address, length, type, payload, CRC.
    Length includes type + payload + CRC.
    """
    while len(buffer) >= 2:
        length = buffer[1]
        if length < 2 or length > 64:
            del buffer[0]
            continue
        total = length + 2
        if len(buffer) < total:
            return
        candidate = bytes(buffer[:total])
        # CRC covers type + payload, not address, length, or CRC itself.
        if crc8_dvb_s2(candidate[2:-1]) != candidate[-1]:
            del buffer[0]
            continue
        del buffer[:total]
        yield candidate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", help="Serial port; default auto-detect 067B:2303")
    parser.add_argument("--baud", type=int, default=230400,
                        help="Must match Nano RX UART Baud (default: 230400 for this experiment)")
    args = parser.parse_args()
    port = args.port or find_pl2303()
    buffer = bytearray()
    last_channels = time.monotonic()
    valid_channels = 0
    frame_types = Counter()

    print(f"CRSF read-only monitor | {port} @ {args.baud} baud")
    print("Move sticks/switches on RadioMaster Pocket. Ctrl+C to stop.")

    try:
        with serial.Serial(port, args.baud, timeout=0.1) as ser:
            while True:
                incoming = ser.read(512)
                if incoming:
                    buffer.extend(incoming)
                    if len(buffer) > 8192:
                        del buffer[:-256]
                for frame in extract_frames(buffer):
                    frame_type = frame[2]
                    frame_types[frame_type] += 1
                    if frame_type == RC_CHANNELS_PACKED and len(frame[3:-1]) == RC_PAYLOAD_SIZE:
                        channels = decode_channels(frame[3:-1])
                        valid_channels += 1
                        last_channels = time.monotonic()
                        print("\r" + " | ".join(
                            f"CH{i + 1:02d}:{value:4d}"
                            for i, value in enumerate(channels)
                        ), end="", flush=True)
                if time.monotonic() - last_channels > 3:
                    print(
                        f"\rWaiting for valid CRSF RC frames... "
                        f"(RC={valid_channels}, other={dict(frame_types)})",
                        end="", flush=True
                    )
                    last_channels = time.monotonic()
    except KeyboardInterrupt:
        print("\nStopped.")
    except serial.SerialException as exc:
        raise SystemExit(f"Serial error: {exc}") from exc


if __name__ == "__main__":
    main()
