"""Manual undo steps for operations invoked from INTERNAL modal handlers."""

from __future__ import annotations

import bpy

_UNDO_LABEL = "Text Helper"


def push_undo(message: str = _UNDO_LABEL) -> None:
    """Push one undo step; nested bpy.ops from modal handlers skip UNDO otherwise."""
    try:
        if message:
            bpy.ops.ed.undo_push(message=message)
        else:
            bpy.ops.ed.undo_push()
    except Exception:
        pass
