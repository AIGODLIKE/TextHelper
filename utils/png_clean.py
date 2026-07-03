"""PNG helpers: write sRGB-safe images and strip libpng-warning chunks."""

from __future__ import annotations

import os
import struct
import zlib

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_STRIP_CHUNKS = frozenset({b"iCCP", b"cHRM", b"sRGB", b"gAMA", b"pHYs"})


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(tag + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)


def write_solid_png(path: str, width: int, height: int, rgba) -> bool:
    """Write an RGBA PNG without ICC/chroma metadata chunks."""
    w = max(1, int(width))
    h = max(1, int(height))
    r, g, b, a = [max(0, min(255, int(round(channel * 255)))) for channel in rgba]
    row = bytes((r, g, b, a)) * w
    raw_data = b"".join(b"\x00" + row for _ in range(h))
    compressed = zlib.compress(raw_data, 9)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
    png = (
        _PNG_SIGNATURE
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", compressed)
        + _png_chunk(b"IEND", b"")
    )
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(png)
    except OSError:
        return False
    return True


def strip_png_color_profile(path: str) -> bool:
    """Remove ICC/chromaticity chunks so libpng loads previews without warnings."""
    try:
        with open(path, "rb") as handle:
            data = handle.read()
    except OSError:
        return False

    if len(data) < 8 or data[:8] != _PNG_SIGNATURE:
        return False

    out = bytearray(_PNG_SIGNATURE)
    offset = 8
    changed = False

    while offset + 8 <= len(data):
        length = struct.unpack_from(">I", data, offset)[0]
        chunk_type = data[offset + 4 : offset + 8]
        chunk_end = offset + 8 + length + 4
        if chunk_end > len(data):
            return False

        if chunk_type in _STRIP_CHUNKS:
            changed = True
        else:
            out.extend(data[offset:chunk_end])

        offset = chunk_end
        if chunk_type == b"IEND":
            break

    if not changed:
        return True

    try:
        with open(path, "wb") as handle:
            handle.write(out)
    except OSError:
        return False
    return True


def strip_png_dir(directory: str) -> None:
    if not directory or not os.path.isdir(directory):
        return
    for name in os.listdir(directory):
        if name.lower().endswith(".png"):
            strip_png_color_profile(os.path.join(directory, name))
