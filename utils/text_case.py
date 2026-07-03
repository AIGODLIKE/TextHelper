"""Text case transform (default / uppercase / lowercase)."""

from __future__ import annotations

from .text_orientation import is_vertical

_SYNC_GUARD = False


def _get_editable_raw(text_data) -> str:
    if is_vertical(text_data):
        return getattr(text_data.text_helper, "th_vertical_source", "") or ""
    return text_data.body or ""


def _set_editable_raw(text_data, raw: str) -> None:
    if is_vertical(text_data):
        text_data.text_helper.th_vertical_source = raw
        from .text_orientation import sync_vertical_source_to_body

        sync_vertical_source_to_body(text_data)
        return
    text_data.body = raw
    text_data.update_tag()


def _with_sync_guard(fn):
    global _SYNC_GUARD
    _SYNC_GUARD = True
    try:
        fn()
    finally:
        _SYNC_GUARD = False


def _snapshot_ref(snapshot: str, case: str) -> str:
    return snapshot.upper() if case == "UPPER" else snapshot.lower()


def _update_snapshot_for_edit(text_data, display: str, case: str) -> None:
    """Track default-case text while the user edits under a case lock."""
    snapshot = getattr(text_data.text_helper, "th_text_case_snapshot", "") or ""
    if not snapshot:
        text_data.text_helper.th_text_case_snapshot = (
            display.lower() if case == "UPPER" else display
        )
        return

    ref = _snapshot_ref(snapshot, case)
    if display == ref:
        return

    if display.startswith(ref) and len(display) > len(ref):
        delta = display[len(ref) :]
        if case == "UPPER":
            text_data.text_helper.th_text_case_snapshot = snapshot + delta.lower()
        else:
            text_data.text_helper.th_text_case_snapshot = snapshot + delta
        return

    text_data.text_helper.th_text_case_snapshot = (
        display.lower() if case == "UPPER" else display
    )


def sync_live_text_case(text_data) -> bool:
    """Keep body/source aligned with the active case lock while typing."""
    global _SYNC_GUARD
    if _SYNC_GUARD or text_data is None:
        return False

    case = getattr(text_data.text_helper, "th_text_case", "DEFAULT")
    if case not in {"UPPER", "LOWER"}:
        return False

    raw = _get_editable_raw(text_data)
    transformed = raw.upper() if case == "UPPER" else raw.lower()
    _update_snapshot_for_edit(text_data, transformed, case)

    if transformed == raw:
        return False

    _with_sync_guard(lambda: _set_editable_raw(text_data, transformed))
    return True


def apply_text_case(text_data, case: str) -> None:
    """Apply, switch, or release the case lock."""
    current = getattr(text_data.text_helper, "th_text_case", "DEFAULT")
    raw = _get_editable_raw(text_data)
    snapshot = getattr(text_data.text_helper, "th_text_case_snapshot", "") or ""

    if case == "DEFAULT":
        text = snapshot if snapshot else raw

        def _apply_default():
            _set_editable_raw(text_data, text)

        _with_sync_guard(_apply_default)
        text_data.text_helper.th_text_case = "DEFAULT"
        text_data.text_helper.th_text_case_snapshot = ""
        return

    if current == "DEFAULT" or not snapshot:
        text_data.text_helper.th_text_case_snapshot = raw

    base = text_data.text_helper.th_text_case_snapshot or raw
    text = base.upper() if case == "UPPER" else base.lower()

    def _apply_case():
        _set_editable_raw(text_data, text)

    _with_sync_guard(_apply_case)
    text_data.text_helper.th_text_case = case
