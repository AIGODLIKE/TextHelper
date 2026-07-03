"""Shared poll helpers for Text Helper operators."""

from __future__ import annotations

from .text_format import get_active_text, get_active_text_data


class TextHelperOperatorMixin:
    """Shared RNA translation context for operator labels and tooltips."""

    bl_translation_context = "Operator"


def poll_active_font(context):
    return get_active_text(context) is not None


def poll_active_font_message(cls, context):
    obj = context.active_object
    if obj is None:
        cls.poll_message_set("Select a text object first")
        return False
    if obj.type != "FONT":
        cls.poll_message_set("Active object is not a text object")
        return False
    if not obj.select_get():
        cls.poll_message_set("Select the text object")
        return False
    return True


def poll_active_font_data(context):
    return get_active_text_data(context) is not None


def poll_active_font_data_message(cls, context):
    if not poll_active_font_message(cls, context):
        return False
    if get_active_text_data(context) is None:
        cls.poll_message_set("Text data is unavailable")
        return False
    return True


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
            cls.poll_message_set("Text Helper is not ready yet")
            return False
        return True


class PreferencesPollMixin(TextHelperOperatorMixin):
    """Mixin for operators that open add-on preferences."""

    @classmethod
    def poll(cls, context):
        if context.preferences is None:
            cls.poll_message_set("Preferences unavailable")
            return False
        return True
