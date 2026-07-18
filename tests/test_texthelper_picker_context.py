"""Regression tests for per-window picker ownership and viewport caches."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


def _source_path_from_args() -> Path:
    separator = sys.argv.index("--")
    return Path(sys.argv[separator + 1]).resolve()


def _load_package(source: Path):
    spec = importlib.util.spec_from_file_location(
        "TextHelper",
        source / "__init__.py",
        submodule_search_locations=[str(source)],
    )
    package = importlib.util.module_from_spec(spec)
    sys.modules["TextHelper"] = package
    spec.loader.exec_module(package)
    return package


class Pointer:
    def __init__(self, value):
        self.value = value

    def as_pointer(self):
        return self.value


class Context:
    def __init__(self, window, area, region):
        self.window = Pointer(window)
        self.area = Pointer(area)
        self.region = Pointer(region)


class State:
    picker_open = False
    picker_window = ""


def main():
    _load_package(_source_path_from_args())
    from TextHelper.utils.picker_context import (
        ViewportCache,
        claim_picker,
        picker_is_open,
        release_picker,
    )

    first = Context(10, 20, 30)
    split = Context(10, 21, 31)
    second = Context(11, 22, 32)
    state = State()

    claim_picker(state, "picker_open", "picker_window", first)
    assert picker_is_open(state, "picker_open", "picker_window", first)
    assert not picker_is_open(state, "picker_open", "picker_window", second)
    assert not release_picker(
        state,
        "picker_open",
        "picker_window",
        second,
    )
    assert state.picker_open
    assert release_picker(
        state,
        "picker_open",
        "picker_window",
        first,
    )
    assert not state.picker_open

    cache = ViewportCache()
    cache.set(first, "first")
    cache.set(split, "split")
    cache.set(second, "second")
    assert cache.get(first) == "first"
    assert cache.get(split) == "split"
    assert cache.get(second) == "second"
    cache.pop(split)
    assert cache.get(split) is None
    assert cache.get(first) == "first"

    from TextHelper.utils import header_picker_modal
    from TextHelper.utils.picker_context import viewport_key

    header_picker_modal._LAYOUTS.clear()
    header_picker_modal._ACTIVE_REGIONS.clear()
    header_picker_modal._LAYOUTS.set(first, {"picker_type": "FONT"})
    header_picker_modal._LAYOUTS.set(second, {"picker_type": "WEIGHT"})
    first_key = viewport_key(first)
    second_key = viewport_key(second)
    header_picker_modal._ACTIVE_REGIONS.update((first_key, second_key))
    assert header_picker_modal._LAYOUTS.get(first)["picker_type"] == "FONT"
    assert header_picker_modal._LAYOUTS.get(second)["picker_type"] == "WEIGHT"
    assert first_key in header_picker_modal._ACTIVE_REGIONS
    assert second_key in header_picker_modal._ACTIVE_REGIONS
    header_picker_modal._LAYOUTS.pop_key(first_key)
    header_picker_modal._ACTIVE_REGIONS.discard(first_key)
    assert header_picker_modal._LAYOUTS.get(first) is None
    assert header_picker_modal._LAYOUTS.get(second)["picker_type"] == "WEIGHT"
    header_picker_modal._LAYOUTS.clear()
    header_picker_modal._ACTIVE_REGIONS.clear()

    print("TEXTHELPER_PICKER_WINDOW_OWNERSHIP_TEST=PASS")
    print("TEXTHELPER_PICKER_VIEWPORT_CACHE_TEST=PASS")
    print("TEXTHELPER_HEADER_PICKER_WINDOW_CACHE_TEST=PASS")


if __name__ == "__main__":
    main()
