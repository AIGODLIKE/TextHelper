"""Shared poll helpers for Text Helper operators."""

from __future__ import annotations

import bpy

from ..i18n import _
from .text_format import has_selected_font, iter_selected_font_objects


def translate_operator_text(text: str, *, context: str = "Operator") -> str:
    """Resolve operator RNA tooltip/label text from registered locale tables."""
    msgid = (text or "").strip()
    if not msgid:
        return ""
    translated = bpy.app.translations.pgettext(msgid, context)
    if translated and translated != msgid:
        return translated
    if context != "*":
        fallback = bpy.app.translations.pgettext(msgid, "*")
        if fallback and fallback != msgid:
            return fallback
    return msgid


def operator_description_text(operator_cls) -> str:
    raw = getattr(operator_cls, "bl_description", None)
    if raw is None:
        return ""
    if isinstance(raw, tuple):
        parts = [part.strip() for part in raw if isinstance(part, str) and part.strip()]
        text = " ".join(parts)
    elif isinstance(raw, str):
        text = raw.strip()
    else:
        return str(raw)
    if not text:
        return ""
    ctxt = getattr(operator_cls, "bl_translation_context", None) or "Operator"
    return translate_operator_text(text, context=ctxt)


class TextHelperOperatorMixin:
    """Shared RNA translation context for operator labels and tooltips."""

    bl_translation_context = "Operator"

    @classmethod
    def description(cls, context, properties):
        return operator_description_text(cls)


def poll_active_font(context):
    return has_selected_font(context)


def poll_active_font_message(cls, context):
    if not has_selected_font(context):
        cls.poll_message_set(_("Select a text object first"))
        return False
    return True


def poll_active_font_data(context):
    if not has_selected_font(context):
        return False
    for obj in iter_selected_font_objects(context):
        if obj.data is not None:
            return True
    return False


def poll_active_font_data_message(cls, context):
    if not poll_active_font_message(cls, context):
        return False
    for obj in iter_selected_font_objects(context):
        if obj.data is not None:
            return True
    cls.poll_message_set(_("Text data is unavailable"))
    return False


class ActiveFontDataPollMixin(TextHelperOperatorMixin):
    """Mixin for operators that require an active text object's data."""

    @classmethod
    def poll(cls, context):
        return poll_active_font_data_message(cls, context)


class ActiveFontPollMixin(TextHelperOperatorMixin):
    """Mixin for operators that require a selected text object."""

    @classmethod
    def poll(cls, context):
        return poll_active_font_message(cls, context)


class WindowManagerPollMixin(TextHelperOperatorMixin):
    """Mixin for operators that only need Text Helper WM state."""

    @classmethod
    def poll(cls, context):
        wm = context.window_manager
        if wm is None or getattr(wm, "th_state", None) is None:
            cls.poll_message_set(_("Text Helper is not ready yet"))
            return False
        return True


class PreferencesPollMixin(TextHelperOperatorMixin):
    """Mixin for operators that open add-on preferences."""

    @classmethod
    def poll(cls, context):
        if context.preferences is None:
            cls.poll_message_set(_("Preferences unavailable"))
            return False
        return True
