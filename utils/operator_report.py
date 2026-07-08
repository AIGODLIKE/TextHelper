"""Queue operator status-bar reports for the HUD modal to emit."""

from __future__ import annotations



def queue_operator_report(wm, msgid: str) -> None:
    """Store an English msgid; translate when the modal operator reports it."""
    state = getattr(wm, "th_state", None)
    if state is None:
        return
    text = (msgid or "").strip()
    if text:
        state.th_pending_report = text


def _translate_operator_report(operator, msgid: str) -> str:
    from .operator_poll import translate_operator_text

    ctxt = getattr(operator, "bl_translation_context", None) or "Operator"
    return translate_operator_text(msgid, context=ctxt)


def flush_pending_report(operator, state) -> bool:
    message = (getattr(state, "th_pending_report", "") or "").strip()
    if not message:
        return False
    state.th_pending_report = ""
    operator.report({"INFO"}, _translate_operator_report(operator, message))
    return True
