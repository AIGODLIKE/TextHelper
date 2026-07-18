"""Window ownership and viewport-local caches for HUD pickers."""

from __future__ import annotations


def _pointer(value):
    if value is None:
        return 0
    try:
        return int(value.as_pointer())
    except (AttributeError, ReferenceError):
        return id(value)


def window_token(context) -> str:
    window = getattr(context, "window", None) if context is not None else None
    pointer = _pointer(window)
    return str(pointer) if pointer else ""


def viewport_key(context):
    """Stable key for one WINDOW region, including split and multi-window UI."""
    if context is None:
        return None
    return (
        _pointer(getattr(context, "window", None)),
        _pointer(getattr(context, "area", None)),
        _pointer(getattr(context, "region", None)),
    )


def picker_is_open(state, open_prop: str, owner_prop: str, context) -> bool:
    if state is None or not bool(getattr(state, open_prop, False)):
        return False
    owner = str(getattr(state, owner_prop, "") or "")
    token = window_token(context)
    # Empty owner supports files/preferences created before 2.3.0.
    return not owner or not token or owner == token


def claim_picker(state, open_prop: str, owner_prop: str, context) -> None:
    setattr(state, open_prop, True)
    setattr(state, owner_prop, window_token(context))


def release_picker(
    state,
    open_prop: str,
    owner_prop: str,
    context,
    *,
    force: bool = False,
) -> bool:
    if state is None:
        return False
    if not force and not picker_is_open(state, open_prop, owner_prop, context):
        return False
    setattr(state, open_prop, False)
    setattr(state, owner_prop, "")
    return True


class ViewportCache:
    """Tiny cache whose entries never leak across split regions or windows."""

    def __init__(self):
        self._values = {}

    def get(self, context, default=None):
        key = viewport_key(context)
        if key is None:
            return default
        return self._values.get(key, default)

    def get_key(self, key, default=None):
        return self._values.get(key, default)

    def set(self, context, value):
        key = viewport_key(context)
        if key is not None:
            self._values[key] = value
        return value

    def pop(self, context):
        key = viewport_key(context)
        if key is not None:
            self._values.pop(key, None)

    def pop_key(self, key):
        if key is not None:
            return self._values.pop(key, None)
        return None

    def clear(self):
        self._values.clear()
