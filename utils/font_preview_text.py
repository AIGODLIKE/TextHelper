"""Shared preview phrase for font thumbnails and the viewport picker."""

from .addon_prefs import get_addon_prefs
from .text_format import get_active_text_data

FONT_PICKER_PERF_STANDARD = "STANDARD"
FONT_PICKER_PERF_HIGH = "HIGH"
FONT_PICKER_PERF_ULTRA = "ULTRA"
PERF_HINT_CHAR_THRESHOLD = 200

DEFAULT_SAMPLE = "Exploration witnesses courage, open source witnesses glory"
MAX_COVERAGE_LEN = 2048
# High-performance: never read beyond the head window; probe few unique glyphs only.
HIGH_PERF_HEAD_SCAN = 40
HIGH_PERF_PREVIEW_LEN = 24
HIGH_PERF_COVERAGE_LEN = 10
HIGH_PERF_LINE_SNIPPET = 12
HIGH_PERF_MAX_LINES = 2

_LEGACY_MODES = {
    "BOTH": "OBJECT",
}


def _pref_sample(prefs):
    if prefs is None:
        return DEFAULT_SAMPLE
    return (getattr(prefs, "font_preview_sample", DEFAULT_SAMPLE) or DEFAULT_SAMPLE).strip()


def _inline_sample(context):
    wm = getattr(context, "window_manager", None)
    if wm is None:
        return ""
    state = getattr(wm, "th_state", None)
    if state is None:
        return ""
    return (getattr(state, "font_picker_preview", "") or "").strip()


def _body_head_slice(body: str, limit: int) -> str:
    """Read only the first `limit` codepoints — safe for single-line megabyte text."""
    if not body or limit <= 0:
        return ""
    chunk = body[: limit + 4]
    return chunk.replace("\r\n", "\n").replace("\r", "\n")[:limit]


def _unique_coverage_chars(text: str, *, max_chars: int = MAX_COVERAGE_LEN) -> str:
    """Deduplicated non-newline characters for glyph coverage checks."""
    if not text:
        return ""
    seen = set()
    out = []
    for char in text:
        if char in "\r\n":
            continue
        if char.isspace():
            char = " "
        if char in seen:
            continue
        seen.add(char)
        out.append(char)
        if len(out) >= max_chars:
            break
    return "".join(out)


def _object_sample(context, *, head_limit: int | None = None):
    text_data = get_active_text_data(context)
    if text_data is None:
        return ""
    from .text_orientation import is_vertical, vertical_first_column

    body = text_data.body or ""
    if not body:
        return ""

    if head_limit is not None:
        head = _body_head_slice(body, head_limit)
        if is_vertical(text_data):
            return head.split("\n", 1)[0].strip()
        return head.split("\n", 1)[0].strip()

    if is_vertical(text_data):
        line = vertical_first_column(text_data)
    else:
        body_norm = body.replace("\r\n", "\n").replace("\r", "\n")
        line = body_norm.split("\n", 1)[0].strip()
    return (line or "").strip()


def get_font_picker_performance_mode(context) -> str:
    if context is None:
        return FONT_PICKER_PERF_STANDARD
    prefs = get_addon_prefs(context)
    mode = getattr(prefs, "font_picker_performance_mode", FONT_PICKER_PERF_HIGH)
    if mode in (FONT_PICKER_PERF_STANDARD, FONT_PICKER_PERF_HIGH, FONT_PICKER_PERF_ULTRA):
        return mode
    if getattr(prefs, "font_picker_ultra_high_performance", False):
        return FONT_PICKER_PERF_ULTRA
    if getattr(prefs, "font_picker_high_performance", False):
        return FONT_PICKER_PERF_HIGH
    return FONT_PICKER_PERF_STANDARD


def is_font_picker_high_performance(context) -> bool:
    return get_font_picker_performance_mode(context) in (
        FONT_PICKER_PERF_HIGH,
        FONT_PICKER_PERF_ULTRA,
    )


def is_font_picker_ultra_high_performance(context) -> bool:
    return get_font_picker_performance_mode(context) == FONT_PICKER_PERF_ULTRA


def hud_font_picker_hover_apply_enabled(context) -> bool:
    """Whether HUD font/weight pickers apply fonts while hovering."""
    if context is None:
        return True
    prefs = get_addon_prefs(context)
    if not getattr(prefs, "font_preview_on_select", True):
        return False
    if is_font_picker_ultra_high_performance(context):
        return False
    return True


def _coverage_max_len(context) -> int:
    if is_font_picker_high_performance(context):
        return HIGH_PERF_COVERAGE_LEN
    return MAX_COVERAGE_LEN


def _high_perf_object_source(context) -> str:
    """Deterministic head window — never walks an entire single-line body."""
    text_data = get_active_text_data(context)
    if text_data is None or not text_data.body:
        return ""

    head = _body_head_slice(text_data.body, HIGH_PERF_HEAD_SCAN)
    if not head.strip():
        return ""

    lines = [line.strip() for line in head.split("\n") if line.strip()]
    if not lines:
        return ""

    parts = []
    for line in lines[:HIGH_PERF_MAX_LINES]:
        parts.append(line[:HIGH_PERF_LINE_SNIPPET])
    return "".join(parts)


def _high_perf_coverage_text(context, display_name="") -> str:
    prefs = get_addon_prefs(context)
    mode = _preview_mode(prefs)
    custom = _custom_sample(context, prefs)
    name = (display_name or "").strip()

    if mode == "NAME":
        source = (name or custom or "Aa")[:HIGH_PERF_HEAD_SCAN]
    elif mode == "SAMPLE":
        source = (custom or "Aa")[:HIGH_PERF_HEAD_SCAN]
    else:
        source = _high_perf_object_source(context)
        if not source:
            source = (custom or "Aa")[:HIGH_PERF_HEAD_SCAN]

    return _unique_coverage_chars(source, max_chars=HIGH_PERF_COVERAGE_LEN)


def _object_coverage_text(context):
    text_data = get_active_text_data(context)
    if text_data is None or not text_data.body:
        return ""
    body = text_data.body.replace("\r\n", "\n").replace("\r", "\n")
    return _unique_coverage_chars(body)


def _custom_sample(context, prefs):
    return (_inline_sample(context) or _pref_sample(prefs) or DEFAULT_SAMPLE).strip()


def _preview_mode(prefs):
    mode = getattr(prefs, "font_preview_mode", "OBJECT") if prefs else "OBJECT"
    return _LEGACY_MODES.get(mode, mode)


def font_coverage_is_per_font(context) -> bool:
    if context is None:
        return False
    prefs = get_addon_prefs(context)
    return _preview_mode(prefs) == "NAME"


def get_font_preview_text(context, display_name=""):
    """Resolve preview characters from add-on preferences."""
    if context is None:
        return (DEFAULT_SAMPLE or "Aa")[:MAX_PREVIEW_LEN]

    prefs = get_addon_prefs(context)
    mode = _preview_mode(prefs)
    high = is_font_picker_high_performance(context)
    preview_cap = HIGH_PERF_PREVIEW_LEN if high else MAX_PREVIEW_LEN
    head_limit = HIGH_PERF_HEAD_SCAN if high else None
    custom = _custom_sample(context, prefs)[:preview_cap]
    name = (display_name or "").strip()[:preview_cap]

    if mode == "NAME":
        return name or custom or "Aa"

    if mode == "SAMPLE":
        return custom or "Aa"

    object_text = _object_sample(context, head_limit=head_limit)[:preview_cap]
    if object_text:
        return object_text
    return custom or "Aa"


def get_font_coverage_text(context, display_name=""):
    """All unique characters to test when filtering fonts by glyph support."""
    if context is None:
        return _unique_coverage_chars(DEFAULT_SAMPLE or "Aa")

    if is_font_picker_high_performance(context):
        return _high_perf_coverage_text(context, display_name)

    prefs = get_addon_prefs(context)
    mode = _preview_mode(prefs)
    custom = _custom_sample(context, prefs)
    name = (display_name or "").strip()
    max_chars = _coverage_max_len(context)

    if mode == "NAME":
        return _unique_coverage_chars(name or custom or "Aa", max_chars=max_chars)

    if mode == "SAMPLE":
        return _unique_coverage_chars(custom or "Aa", max_chars=max_chars)

    object_text = _object_coverage_text(context)
    if object_text:
        return object_text
    return _unique_coverage_chars(custom or "Aa", max_chars=max_chars)
