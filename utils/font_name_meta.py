"""Read searchable metadata (name table, PostScript name) from font files."""



from __future__ import annotations



import os

import struct

from dataclasses import dataclass



import bpy



_NAME_IDS = (0, 1, 2, 3, 4, 5, 6, 16, 17, 18, 21)
# Family/face labels only — exclude copyright (0) and other legal/version noise.
_SEARCH_NAME_IDS = (1, 2, 4, 6, 16, 17, 18, 21)





@dataclass(frozen=True)

class _NameRecord:

    name_id: int

    platform_id: int

    language_id: int

    text: str





_RECORDS_CACHE: dict[str, tuple[_NameRecord, ...]] = {}





def _norm_path(filepath: str) -> str:

    return os.path.normcase(bpy.path.abspath(filepath or ""))





def _decode_name_record(data: bytes, offset: int, length: int, *, is_unicode: bool) -> str:

    chunk = data[offset : offset + length]

    if not chunk:

        return ""

    if is_unicode:

        if length % 2:

            chunk = chunk[:-1]

        try:

            return chunk.decode("utf-16-be", errors="ignore")

        except UnicodeDecodeError:

            return ""

    try:

        return chunk.decode("latin-1", errors="ignore")

    except UnicodeDecodeError:

        return ""





def _record_rank(record: _NameRecord) -> tuple[int, int]:

    score = 0

    if record.platform_id == 3:

        score += 100

    elif record.platform_id == 1:

        score += 50

    elif record.platform_id == 0:

        score += 40

    text = record.text

    if any("\u3040" <= char <= "\u9fff" or "\uac00" <= char <= "\ud7af" for char in text):

        score += 30

    elif record.language_id in (0x409, 0x809):

        score += 15

    return score, len(text)





def read_font_name_records(filepath: str) -> tuple[_NameRecord, ...]:
    abs_path = _norm_path(filepath)
    if not abs_path:
        return ()
    cached = _RECORDS_CACHE.get(abs_path)
    if cached is not None:
        return cached
    records: list[_NameRecord] = []
    try:
        with open(abs_path, "rb") as handle:
            header = handle.read(12)
            if len(header) < 12:
                _RECORDS_CACHE[abs_path] = ()
                return ()

            sfnt_offset = 0
            if header[:4] == b"ttcf":
                # TrueType Collection: use the first face for family/search
                # metadata, matching Blender's load behavior for the file.
                num_fonts = struct.unpack_from(">I", header, 8)[0]
                if num_fonts <= 0:
                    _RECORDS_CACHE[abs_path] = ()
                    return ()
                offset_data = handle.read(4)
                if len(offset_data) < 4:
                    _RECORDS_CACHE[abs_path] = ()
                    return ()
                sfnt_offset = struct.unpack(">I", offset_data)[0]
                handle.seek(sfnt_offset)
                header = handle.read(12)
                if len(header) < 12:
                    _RECORDS_CACHE[abs_path] = ()
                    return ()

            num_tables = struct.unpack_from(">H", header, 4)[0]
            name_offset = None
            name_length = 0
            table_dir = handle.read(num_tables * 16)
            for index in range(num_tables):
                record = index * 16
                if record + 16 > len(table_dir):
                    break
                if table_dir[record : record + 4] != b"name":
                    continue
                name_offset, name_length = struct.unpack_from(">II", table_dir, record + 8)
                break

            if name_offset is None or name_length < 6:
                _RECORDS_CACHE[abs_path] = ()
                return ()
            handle.seek(name_offset)
            data = handle.read(name_length)
    except OSError:
        _RECORDS_CACHE[abs_path] = ()
        return ()
    if len(data) < 6:
        _RECORDS_CACHE[abs_path] = ()
        return ()
    _format_version, count, storage_offset = struct.unpack_from(">HHH", data, 0)
    if count <= 0:
        _RECORDS_CACHE[abs_path] = ()
        return ()
    string_base = storage_offset
    for rec in range(count):
        rec_off = 6 + rec * 12
        if rec_off + 12 > len(data):
            break
        platform_id, _encoding_id, language_id, name_id, length, offset = struct.unpack_from(
            ">HHHHHH", data, rec_off
        )
        if length <= 0 or string_base + offset + length > len(data):
            continue
        is_unicode = platform_id in (0, 3)
        text = _decode_name_record(data, string_base + offset, length, is_unicode=is_unicode).strip()
        if text:
            records.append(
                _NameRecord(
                    name_id=int(name_id),
                    platform_id=int(platform_id),
                    language_id=int(language_id),
                    text=text,
                )
            )
    result = tuple(records)
    _RECORDS_CACHE[abs_path] = result
    return result





def read_font_name_id(filepath: str, name_id: int) -> str:

    matches = [record for record in read_font_name_records(filepath) if record.name_id == name_id and record.text]

    if not matches:

        return ""

    return max(matches, key=_record_rank).text





def read_font_name_strings(filepath: str) -> tuple[str, ...]:

    """Return unique non-empty strings from the font name table."""

    records = read_font_name_records(filepath)

    strings = {record.text for record in records if record.text and record.name_id in _NAME_IDS}

    return tuple(sorted(strings, key=lambda value: (len(value), value.lower())))


def read_font_search_name_strings(filepath: str) -> tuple[str, ...]:
    """Name-table strings used for font search (no copyright / license boilerplate)."""
    records = read_font_name_records(filepath)
    strings = {
        record.text
        for record in records
        if record.text and record.name_id in _SEARCH_NAME_IDS and len(record.text) <= 120
    }
    return tuple(sorted(strings, key=lambda value: (len(value), value.lower())))


def invalidate_font_name_cache() -> None:

    _RECORDS_CACHE.clear()


