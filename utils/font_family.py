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
    ("-Normal", "Regular", 400),
    (" Normal", "Regular", 400),
    ("Normal", "Regular", 400),
    ("-Roman", "Regular", 400),
    (" Roman", "Regular", 400),
    ("Roman", "Regular", 400),
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


def parse_font_stem(stem: str):
    """Return (family_stem, weight_label, weight_rank)."""
    if not stem:
        return "", "Regular", 400

    legacy = _parse_legacy_windows_stem(stem)
    if legacy is not None:
        return legacy

    for suffix, label, rank in _STEM_SUFFIXES:
        if stem.endswith(suffix):
            family = stem[: -len(suffix)]
            if family:
                return family, label, rank
            break

    return stem, "Regular", 400


def family_key_from_stem(stem: str) -> str:
    family, _label, _rank = parse_font_stem(stem)
    return family.replace("_", "").replace("-", "").replace(" ", "").lower()


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


def variant_from_catalog_item(index: int, item) -> FontWeightVariant:
    basename = os.path.basename(item.filepath or "")
    stem, _ext = os.path.splitext(basename)
    family, weight_label, weight_rank = parse_font_stem(stem)
    return FontWeightVariant(
        catalog_index=index,
        weight_label=weight_label,
        weight_rank=weight_rank,
        filepath=item.filepath,
        display_name=_display_family(family) or item.display_name,
    )


def group_catalog_items(indexed_items):
    """Group (catalog_index, item) pairs into FontFamilyGroup rows."""
    buckets: dict[str, list[FontWeightVariant]] = {}
    display_names: dict[str, str] = {}

    for index, item in indexed_items:
        variant = variant_from_catalog_item(index, item)
        key = family_key_from_stem(os.path.splitext(os.path.basename(item.filepath or ""))[0])
        if not key:
            key = f"__item_{index}"
        buckets.setdefault(key, []).append(variant)
        if key not in display_names:
            display_names[key] = variant.display_name

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


def find_family_variants_in_catalog(catalog, filepath: str) -> tuple[FontWeightVariant, ...]:
    """All catalog entries belonging to the same font family as filepath."""
    if not filepath or catalog is None or len(catalog) == 0:
        return ()
    target_stem = os.path.splitext(os.path.basename(filepath))[0]
    key = family_key_from_stem(target_stem)
    if not key:
        return ()
    variants = []
    for index, item in enumerate(catalog):
        item_path = getattr(item, "filepath", "") or ""
        if not item_path:
            continue
        stem = os.path.splitext(os.path.basename(item_path))[0]
        if family_key_from_stem(stem) == key:
            variants.append(variant_from_catalog_item(index, item))
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
    """HUD button label: actual weight when multiple exist, otherwise Regular."""
    variants = find_family_variants_in_catalog(catalog, filepath) if filepath and catalog else ()
    if len(variants) > 1:
        return weight_label_for_filepath(filepath)
    return "Regular"


def ensure_weight_variants(catalog, filepath: str) -> tuple[FontWeightVariant, ...]:
    """Picker rows; single-weight fonts appear as Regular."""
    if not filepath:
        return ()
    variants = find_family_variants_in_catalog(catalog, filepath) if catalog else ()
    if len(variants) > 1:
        return variants
    family, _label, _rank = parse_font_stem(os.path.splitext(os.path.basename(filepath))[0])
    return (
        FontWeightVariant(
            catalog_index=catalog_index_for_filepath(catalog, filepath),
            weight_label="Regular",
            weight_rank=400,
            filepath=filepath,
            display_name=_display_family(family) or family or "Regular",
        ),
    )


def family_weight_counts(catalog):
    """Map family_key -> number of font files in the full catalog."""
    counts = {}
    if not catalog:
        return counts
    for item in catalog:
        filepath = getattr(item, "filepath", "") or ""
        stem = os.path.splitext(os.path.basename(filepath))[0]
        key = family_key_from_stem(stem)
        if not key:
            continue
        counts[key] = counts.get(key, 0) + 1
    return counts


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
