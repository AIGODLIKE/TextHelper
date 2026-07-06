"""Group font files by family and detect weight/style variants."""

from __future__ import annotations

import os
from dataclasses import dataclass

# Longer suffixes first so "Bold Italic" wins over "Italic".
_STEM_SUFFIXES = (
    ("-BoldItalic", "Bold Italic", 710),
    (" Bold Italic", "Bold Italic", 710),
    ("BoldItalic", "Bold Italic", 710),
    ("-Bold-Italic", "Bold Italic", 710),
    ("-Bold Italic", "Bold Italic", 710),
    ("Bold Italic", "Bold Italic", 710),
    ("-ExtraBold", "ExtraBold", 800),
    (" ExtraBold", "ExtraBold", 800),
    (" Extra Bold", "ExtraBold", 800),
    ("ExtraBold", "ExtraBold", 800),
    ("-SemiBold", "SemiBold", 600),
    (" SemiBold", "SemiBold", 600),
    (" Semi Bold", "SemiBold", 600),
    ("SemiBold", "SemiBold", 600),
    ("-DemiBold", "DemiBold", 600),
    (" DemiBold", "DemiBold", 600),
    (" Demi Bold", "DemiBold", 600),
    (" Demi", "DemiBold", 600),
    ("-UltraLight", "UltraLight", 200),
    (" UltraLight", "UltraLight", 200),
    (" Ultra Light", "UltraLight", 200),
    ("-ExtraLight", "ExtraLight", 200),
    (" ExtraLight", "ExtraLight", 200),
    (" Extra Light", "ExtraLight", 200),
    ("-Thin", "Thin", 100),
    (" Thin", "Thin", 100),
    ("Thin", "Thin", 100),
    ("-Light", "Light", 300),
    (" Light", "Light", 300),
    ("Light", "Light", 300),
    ("-Regular", "Regular", 400),
    (" Regular", "Regular", 400),
    ("Regular", "Regular", 400),
    ("-Normal", "Normal", 400),
    (" Normal", "Normal", 400),
    ("Normal", "Normal", 400),
    ("-Roman", "Roman", 400),
    (" Roman", "Roman", 400),
    ("Roman", "Roman", 400),
    ("-Book", "Book", 350),
    (" Book", "Book", 350),
    ("Book", "Book", 350),
    ("-Medium", "Medium", 500),
    (" Medium", "Medium", 500),
    ("Medium", "Medium", 500),
    ("-Bold", "Bold", 700),
    (" Bold", "Bold", 700),
    ("Bold", "Bold", 700),
    ("-Bd", "Bold", 700),
    ("-Heavy", "Heavy", 800),
    (" Heavy", "Heavy", 800),
    ("Heavy", "Heavy", 800),
    ("-Black", "Black", 900),
    (" Black", "Black", 900),
    ("Black", "Black", 900),
    ("-Italic", "Italic", 950),
    (" Italic", "Italic", 950),
    ("Italic", "Italic", 950),
    ("-It", "Italic", 950),
    (" It", "Italic", 950),
)

_LEGACY_WINDOWS_SUFFIXES = (
    ("bi", "Bold Italic", 710),
    ("bd", "Bold", 700),
    ("i", "Italic", 950),
)

# GenYoGothic2 B / GenYoGothic2-EL style single-token weight codes (longer first).
_ABBREV_WEIGHT_CODES = {
    "BL": ("Black", 900),
    "EL": ("ExtraLight", 200),
    "UL": ("UltraLight", 200),
    "XL": ("ExtraLight", 200),
    "SB": ("SemiBold", 600),
    "DB": ("DemiBold", 600),
    "EB": ("ExtraBold", 800),
    "HB": ("Heavy", 800),
    "HL": ("ExtraLight", 200),
    "TH": ("Thin", 100),
    "LT": ("Light", 300),
    "RG": ("Regular", 400),
    "MD": ("Medium", 500),
    "B": ("Bold", 700),
    "L": ("Light", 300),
    "M": ("Medium", 500),
    "H": ("Heavy", 800),
    "R": ("Regular", 400),
    "N": ("Normal", 400),
}

# Appended to _STEM_SUFFIXES after the long names — space/hyphen + abbrev code.
_ABBREV_STEM_SUFFIXES = tuple(
    (f" {code}", label, rank)
    for code, (label, rank) in sorted(
        _ABBREV_WEIGHT_CODES.items(), key=lambda item: (-len(item[0]), item[0])
    )
) + tuple(
    (f"-{code}", label, rank)
    for code, (label, rank) in sorted(
        _ABBREV_WEIGHT_CODES.items(), key=lambda item: (-len(item[0]), item[0])
    )
)


def _display_family(stem: str) -> str:
    return stem.replace("_", " ").replace("-", " ").strip()


def _parse_legacy_windows_stem(stem: str):
    lower = stem.lower()
    for code, label, rank in _LEGACY_WINDOWS_SUFFIXES:
        if lower.endswith(code) and len(stem) > len(code):
            base = stem[: -len(code)]
            if base and base[-1].isalpha():
                return base, label, rank
    return None


def _parse_abbreviated_stem(stem: str):
    for suffix, label, rank in _ABBREV_STEM_SUFFIXES:
        if stem.endswith(suffix):
            family = stem[: -len(suffix)]
            if family:
                return family, label, rank
    return None


def _parse_postscript_parts(filepath: str) -> tuple[str, str]:
    """Return (family_prefix, weight_code) from PostScript name, e.g. GenYoGothic2-B."""
    from .font_name_meta import read_font_name_id

    ps = read_font_name_id(filepath, 6)
    if not ps or "-" not in ps:
        return "", ""
    head, tail = ps.rsplit("-", 1)
    if not head or not tail or len(tail) > 8:
        return "", ""
    return head, tail


def _family_key_from_postscript(filepath: str) -> str:
    head, _tail = _parse_postscript_parts(filepath)
    if head:
        return _normalize_family_key(head)
    from .font_name_meta import read_font_name_id

    ps = read_font_name_id(filepath, 6)
    if ps:
        return _normalize_family_key(ps)
    return ""


def _weight_from_postscript_code(code: str) -> tuple[str, int]:
    if not code:
        return "Regular", 400
    upper = code.upper()
    if upper in _ABBREV_WEIGHT_CODES:
        return _ABBREV_WEIGHT_CODES[upper]
    return code, _rank_from_weight_label(code)


def parse_font_stem(stem: str):
    """Return (family_stem, weight_label, weight_rank)."""
    if not stem:
        return "", "Regular", 400

    legacy = _parse_legacy_windows_stem(stem)
    if legacy is not None:
        return legacy

    abbrev = _parse_abbreviated_stem(stem)
    if abbrev is not None:
        return abbrev

    for suffix, label, rank in _STEM_SUFFIXES:
        if stem.endswith(suffix):
            family = stem[: -len(suffix)]
            if family:
                return family, label, rank
            break

    return stem, "Regular", 400


def family_key_from_stem(stem: str) -> str:
    family, _label, _rank = parse_font_stem(stem)
    return _normalize_family_key(family)


_VF_KEY_SUFFIXES = ("variablefont", "variable", "vf")


def _normalize_family_key(name: str) -> str:
    key = name.replace("_", "").replace("-", "").replace(" ", "").lower()
    for suffix in _VF_KEY_SUFFIXES:
        if key.endswith(suffix) and len(key) > len(suffix) + 1:
            key = key[: -len(suffix)]
            break
    return key


def get_font_family_group_mode(context=None) -> str:
    from .addon_prefs import get_addon_prefs

    if context is None:
        try:
            import bpy

            context = bpy.context
        except ImportError:
            context = None
    prefs = get_addon_prefs(context)
    mode = getattr(prefs, "font_family_group_mode", "AUTO") or "AUTO"
    if mode in {"FILENAME", "OPENTYPE", "AUTO", "POSTSCRIPT"}:
        return mode
    return "AUTO"


def _opentype_family_name(filepath: str) -> str:
    from .font_name_meta import read_font_name_id

    return read_font_name_id(filepath, 16) or read_font_name_id(filepath, 1)


def _opentype_subfamily_name(filepath: str) -> str:
    from .font_name_meta import read_font_name_id

    return read_font_name_id(filepath, 17) or read_font_name_id(filepath, 2)


def family_key_for_filepath(filepath: str, context=None) -> str:
    """Stable family key for grouping weights, favorites, and recent lists."""
    if not filepath:
        return ""
    if str(filepath).startswith("blend://"):
        stem = os.path.splitext(os.path.basename(filepath[8:] or filepath))[0]
        return family_key_from_stem(stem) if stem else ""

    mode = get_font_family_group_mode(context)
    ps_key = _family_key_from_postscript(filepath)

    if mode == "AUTO":
        if ps_key:
            return ps_key
        family = _opentype_family_name(filepath)
        if family:
            return _normalize_family_key(family)
    elif mode == "OPENTYPE":
        family = _opentype_family_name(filepath)
        if family:
            return _normalize_family_key(family)
        if ps_key:
            return ps_key
    elif mode == "POSTSCRIPT":
        if ps_key:
            return ps_key

    stem = os.path.splitext(os.path.basename(filepath))[0]
    return family_key_from_stem(stem)


def _rank_from_weight_label(label: str) -> int:
    if not label:
        return 400
    compact = label.upper().replace(" ", "").replace("-", "")
    if compact in _ABBREV_WEIGHT_CODES:
        return _ABBREV_WEIGHT_CODES[compact][1]
    compact_lower = label.lower().replace(" ", "").replace("-", "")
    for _suffix, known_label, rank in _STEM_SUFFIXES:
        known = known_label.lower().replace(" ", "")
        if compact_lower == known or known in compact_lower or compact_lower in known:
            return rank
    return 400


def weight_label_and_rank_for_filepath(filepath: str, context=None) -> tuple[str, int]:
    if not filepath:
        return "Regular", 400
    if str(filepath).startswith("blend://"):
        stem = os.path.splitext(os.path.basename(filepath[8:] or filepath))[0]
        _family, label, rank = parse_font_stem(stem)
        return label, rank

    mode = get_font_family_group_mode(context)
    if mode in {"OPENTYPE", "AUTO", "POSTSCRIPT"}:
        _head, ps_code = _parse_postscript_parts(filepath)
        if ps_code:
            return _weight_from_postscript_code(ps_code)
        sub = _opentype_subfamily_name(filepath)
        if sub and mode != "POSTSCRIPT":
            return sub, _rank_from_weight_label(sub)

    stem = os.path.splitext(os.path.basename(filepath))[0]
    _family, label, rank = parse_font_stem(stem)
    return label, rank


@dataclass(frozen=True)
class FontWeightVariant:
    catalog_index: int
    weight_label: str
    weight_rank: int
    filepath: str
    display_name: str


@dataclass(frozen=True)
class FontFamilyGroup:
    family_key: str
    display_name: str
    representative_index: int
    variants: tuple[FontWeightVariant, ...]

    @property
    def variant_count(self) -> int:
        return len(self.variants)

    def filepath_set(self):
        return {os.path.normcase(v.filepath) for v in self.variants}


def variant_from_catalog_item(index: int, item, context=None) -> FontWeightVariant:
    filepath = getattr(item, "filepath", "") or ""
    basename = os.path.basename(filepath)
    stem, _ext = os.path.splitext(basename)
    family, _stem_label, _stem_rank = parse_font_stem(stem)
    weight_label, weight_rank = weight_label_and_rank_for_filepath(filepath, context)
    return FontWeightVariant(
        catalog_index=index,
        weight_label=weight_label,
        weight_rank=weight_rank,
        filepath=filepath,
        display_name=_display_family(family) or item.display_name,
    )


def group_catalog_items(indexed_items, context=None):
    """Group (catalog_index, item) pairs into FontFamilyGroup rows."""
    from .font_display import display_name_for_catalog_item

    buckets: dict[str, list[FontWeightVariant]] = {}
    display_names: dict[str, str] = {}

    for index, item in indexed_items:
        variant = variant_from_catalog_item(index, item, context)
        filepath = getattr(item, "filepath", "") or ""
        key = family_key_for_filepath(filepath, context)
        if not key:
            key = f"__item_{index}"
        buckets.setdefault(key, []).append(variant)
        if key not in display_names:
            display_names[key] = display_name_for_catalog_item(item, context)

    groups: list[FontFamilyGroup] = []
    for key, variants in buckets.items():
        ordered = tuple(sorted(variants, key=lambda v: (v.weight_rank, v.weight_label.lower())))
        rep = pick_representative_variant(ordered)
        groups.append(
            FontFamilyGroup(
                family_key=key,
                display_name=display_names.get(key, ordered[0].display_name),
                representative_index=rep.catalog_index,
                variants=ordered,
            )
        )
    return groups


def pick_representative_variant(variants: tuple[FontWeightVariant, ...] | list[FontWeightVariant]):
    if not variants:
        raise ValueError("variants must not be empty")
    for preferred in ("Regular", "Normal", "Roman", "Book", "Medium", "Light"):
        for variant in variants:
            if variant.weight_label == preferred:
                return variant
    return variants[0]


def find_group_for_catalog_index(groups, catalog_index: int):
    for group in groups:
        for variant in group.variants:
            if variant.catalog_index == catalog_index:
                return group
    return None


def find_group_for_filepath(groups, filepath: str):
    if not filepath:
        return None
    target = os.path.normcase(filepath)
    for group in groups:
        for variant in group.variants:
            if os.path.normcase(variant.filepath) == target:
                return group
    return None


def find_family_variants_in_catalog(catalog, filepath: str, context=None) -> tuple[FontWeightVariant, ...]:
    """All catalog entries belonging to the same font family as filepath."""
    if not filepath or catalog is None or len(catalog) == 0:
        return ()
    key = family_key_for_filepath(filepath, context)
    if not key:
        return ()
    variants = []
    for index, item in enumerate(catalog):
        item_path = getattr(item, "filepath", "") or ""
        if not item_path:
            continue
        if family_key_for_filepath(item_path, context) == key:
            variants.append(variant_from_catalog_item(index, item, context))
    if not variants:
        return ()
    return tuple(sorted(variants, key=lambda v: (v.weight_rank, v.weight_label.lower())))


def _norm_filepath(filepath: str) -> str:
    from .font_loader import disk_font_path_from_string

    abs_path = disk_font_path_from_string(filepath)
    return os.path.normcase(abs_path) if abs_path else ""


def catalog_index_for_filepath(catalog, filepath: str) -> int:
    target = _norm_filepath(filepath)
    if not target or catalog is None:
        return -1
    for index, item in enumerate(catalog):
        item_path = getattr(item, "filepath", "") or ""
        if item_path and _norm_filepath(item_path) == target:
            return index
    return -1


def toolbar_weight_label(catalog, filepath: str) -> str:
    """HUD / header button label from the active font filename."""
    return weight_label_for_filepath(filepath)


def ensure_weight_variants(catalog, filepath: str, context=None) -> tuple[FontWeightVariant, ...]:
    """Picker rows; single-weight fonts keep their parsed weight label."""
    if not filepath:
        return ()
    variants = find_family_variants_in_catalog(catalog, filepath, context) if catalog else ()
    if len(variants) > 1:
        return variants
    stem = os.path.splitext(os.path.basename(filepath))[0]
    family, label, rank = parse_font_stem(stem)
    weight_label, weight_rank = weight_label_and_rank_for_filepath(filepath, context)
    return (
        FontWeightVariant(
            catalog_index=catalog_index_for_filepath(catalog, filepath),
            weight_label=weight_label,
            weight_rank=weight_rank,
            filepath=filepath,
            display_name=_display_family(family) or family or label,
        ),
    )


def family_weight_counts(catalog, context=None):
    """Map family_key -> number of font files in the full catalog."""
    counts = {}
    if not catalog:
        return counts
    for item in catalog:
        filepath = getattr(item, "filepath", "") or ""
        key = family_key_for_filepath(filepath, context)
        if not key:
            continue
        counts[key] = counts.get(key, 0) + 1
    return counts


def header_font_display_label(context, catalog, index: int, item) -> str:
    """Family display name with weight count suffix for header font lists."""
    from .font_display import display_name_for_catalog_item

    label = display_name_for_catalog_item(item, context)
    filepath = getattr(item, "filepath", "") or ""
    count = family_weight_counts(catalog, context).get(family_key_for_filepath(filepath, context), 1)
    if count > 1:
        label = f"{label}  · {count}"
    return label


def weight_label_for_filepath(filepath: str) -> str:
    if not filepath:
        return "Regular"
    stem = os.path.splitext(os.path.basename(filepath))[0]
    _family, label, _rank = parse_font_stem(stem)
    return label


def short_weight_label(label: str, max_len: int = 10) -> str:
    compact = {
        "ExtraLight": "XLt",
        "UltraLight": "ULt",
        "ExtraBold": "XBd",
        "SemiBold": "SBd",
        "DemiBold": "DBd",
        "Bold Italic": "BI",
    }
    text = compact.get(label, label)
    if len(text) > max_len:
        return text[: max_len - 1] + "…"
    return text
