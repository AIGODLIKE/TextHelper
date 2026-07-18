"""Blender-hosted regression tests for Text Helper HUD safe-area insets."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


def _source_path_from_args() -> Path:
    try:
        separator = sys.argv.index("--")
        source = sys.argv[separator + 1]
    except (ValueError, IndexError):
        raise SystemExit("Usage: blender --python test_texthelper_hud_safe_bounds.py -- <source-dir>")
    return Path(source).resolve()


def _load_package(source: Path):
    spec = importlib.util.spec_from_file_location(
        "TextHelper",
        source / "__init__.py",
        submodule_search_locations=[str(source)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load TextHelper package from {source}")
    package = importlib.util.module_from_spec(spec)
    sys.modules["TextHelper"] = package
    spec.loader.exec_module(package)
    return package


class Region:
    def __init__(self, region_type, x, y, width, height):
        self.type = region_type
        self.x = x
        self.y = y
        self.width = width
        self.height = height


class Area:
    def __init__(self, regions):
        self.regions = regions


class Context:
    def __init__(self, window, siblings):
        self.region = window
        self.area = Area([window, *siblings])


def _assert_insets(text_bounds, siblings, expected, *, window=None):
    window = window or Region("WINDOW", 0, 0, 1000, 700)
    actual = text_bounds._window_region_insets(Context(window, siblings))
    assert actual == expected, f"expected {expected}, got {actual}"


def main():
    source = _source_path_from_args()
    _load_package(source)
    from TextHelper.utils import text_bounds

    _assert_insets(text_bounds, [Region("UI", 700, 0, 300, 700)], (0.0, 0.0, 300.0, 0.0))
    _assert_insets(text_bounds, [Region("UI", 0, 0, 300, 700)], (300.0, 0.0, 0.0, 0.0))
    _assert_insets(text_bounds, [Region("TOOLS", 0, 0, 300, 700)], (300.0, 0.0, 0.0, 0.0))
    _assert_insets(text_bounds, [Region("TOOLS", 700, 0, 300, 700)], (0.0, 0.0, 300.0, 0.0))

    _assert_insets(text_bounds, [Region("HEADER", 0, 670, 1000, 30)], (0.0, 0.0, 0.0, 30.0))
    _assert_insets(text_bounds, [Region("HEADER", 0, 0, 1000, 30)], (0.0, 30.0, 0.0, 0.0))
    _assert_insets(text_bounds, [Region("TOOL_HEADER", 0, 670, 1000, 30)], (0.0, 0.0, 0.0, 30.0))
    _assert_insets(text_bounds, [Region("TOOL_HEADER", 0, 0, 1000, 30)], (0.0, 30.0, 0.0, 0.0))

    adjacent_window = Region("WINDOW", 300, 0, 700, 700)
    _assert_insets(
        text_bounds,
        [Region("UI", 0, 0, 300, 700)],
        (0.0, 0.0, 0.0, 0.0),
        window=adjacent_window,
    )

    combined = Context(
        Region("WINDOW", 0, 0, 1000, 700),
        [Region("UI", 0, 0, 300, 700), Region("HEADER", 0, 0, 1000, 30)],
    )
    assert text_bounds._window_region_insets(combined) == (300.0, 30.0, 0.0, 0.0)
    original_get_prefs = text_bounds.get_addon_prefs
    try:
        text_bounds.get_addon_prefs = lambda _context: type("Prefs", (), {"hud_safe_margin": 10.0})()
        assert text_bounds.get_hud_safe_bounds(combined, scale=1.0) == (310.0, 40.0, 990.0, 690.0)
        assert text_bounds.clamp_popup_to_hud_safe_bounds(
            combined, 0.0, 0.0, 300.0, 200.0, 1.0
        ) == (310.0, 40.0)
        assert text_bounds.clamp_popup_to_hud_safe_bounds(
            combined, 900.0, 600.0, 300.0, 200.0, 1.0
        ) == (690.0, 490.0)
    finally:
        text_bounds.get_addon_prefs = original_get_prefs

    print("TEXTHELPER_HUD_SAFE_BOUNDS_TESTS=PASS")


if __name__ == "__main__":
    main()
