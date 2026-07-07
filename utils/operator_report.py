"""Queue operator status-bar reports for the HUD modal to emit."""

from __future__ import annotations


def queue_operator_report(wm, msgid: str, *, value: int = -1) -> None:
    """Store an English msgid; translate when the modal operator reports it."""
    state = getattr(wm, "th_state", None)
    if state is None:
        return
    text = (msgid or "").strip()
    if text:
        state.th_pending_report = text
        state.th_pending_report_value = value


def _translate_operator_report(operator, msgid: str) -> str:
    from .operator_poll import translate_operator_text

    ctxt = getattr(operator, "bl_translation_context", None) or "Operator"
    return translate_operator_text(msgid, context=ctxt)


def flush_pending_report(operator, state) -> bool:
    message = (getattr(state, "th_pending_report", "") or "").strip()
    if not message:
        return False
    value = int(getattr(state, "th_pending_report_value", -1) or -1)
    state.th_pending_report = ""
    state.th_pending_report_value = -1
    text = _translate_operator_report(operator, message)
    if value >= 0:
        try:
            text = text.format(value)
        except Exception:
            text = message.format(value)
    operator.report({"INFO"}, text)
    return True

