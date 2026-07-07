import time

import bpy
from bpy.types import Operator

from ..i18n import _
from ..utils.addon_prefs import get_addon_prefs, prefs_are_editable
from ..utils.operator_poll import ActiveFontPollMixin, TextHelperOperatorMixin
from ..utils.operator_report import flush_pending_report
from ..utils.view3d_context import (
    find_view3d_area_region,
    mouse_in_view3d_ui,
    view3d_override,
    view3d_region_context,
)
from ..utils.text_bounds import point_in_text_screen_bounds
from ..utils.text_frame import tag_view3d_redraw
from ..utils.font_context import enter_text_edit_mode, exit_text_edit_mode, prepare_font_edit_ui, is_font_edit_mode, is_font_edit_mode_value
from ..utils.text_orientation import is_vertical, sync_body_to_vertical_source
from ..hud.draw import tag_redraw
from ..hud.font_picker import (
    close_picker as close_font_picker,
    handle_picker_click as handle_font_picker_click,
    handle_picker_drag,
    handle_picker_hover as handle_font_picker_hover,
    handle_picker_key,
    handle_picker_release,
    handle_picker_wheel,
    handle_search_field_mouse_move,
    hit_test_picker as hit_test_font_picker,
    picker_open as font_picker_open,
    picker_search_blocks_keymap,
    focus_search_field,
)
from ..hud.preset_picker import (
    close_picker as close_preset_picker,
    handle_picker_click as handle_preset_picker_click,
    handle_picker_hover as handle_preset_picker_hover,
    hit_test_picker as hit_test_preset_picker,
    picker_open as preset_picker_open,
)
from ..hud.weight_picker import (
    close_picker as close_weight_picker,
    handle_picker_click as handle_weight_picker_click,
    handle_picker_hover as handle_weight_picker_hover,
    hit_test_picker as hit_test_weight_picker,
    picker_open as weight_picker_open,
)
from ..hud.language_picker import (
    close_picker as close_language_picker,
    handle_picker_click as handle_language_picker_click,
    handle_picker_hover as handle_language_picker_hover,
    hit_test_picker as hit_test_language_picker,
    panel_contains as language_picker_panel_contains,
    picker_open as language_picker_open,
)
from ..hud.hit_test import get_hud_hit_rects, hit_test, hud_enabled
from ..hud.layout import (
    SPACING_SLIDER_IDS,
    slider_reset_hit,
    slider_track_start,
    slider_value_from_mouse,
)
from ..hud.slider_input import (
    clear_slider_value_edit,
    commit_slider_value_edit,
    handle_slider_value_key,
    handle_slider_value_mouse_move,
    handle_slider_value_mouse_release,
    slider_value_blocks_keymap,
    slider_value_editing,
    try_begin_slider_value_edit,
)
from ..utils.text_format import get_active_text, iter_selected_font_objects
from ..utils.undo import push_undo
from ..utils.hud_offset import get_hud_offset, set_hud_offset

_RUNNING = False


def _is_hud_modal_operator(op) -> bool:
    name = (getattr(op, "bl_idname", "") or getattr(type(op), "bl_idname", "")).lower()
    return "texthelper_hud_modal" in name


def _hud_modal_active(context=None) -> bool:
    import bpy

    ctx = context or bpy.context
    window = getattr(ctx, "window", None)
    if window is None:
        return False
    try:
        for op in window.modal_operators:
            if _is_hud_modal_operator(op):
                return True
    except Exception:
        return False
    return False


def sync_modal_running_state(context=None) -> bool:
    """Keep the module flag aligned with Blender's modal operator stack."""
    global _RUNNING
    active = _hud_modal_active(context)
    _RUNNING = active
    return _RUNNING


def modal_running() -> bool:
    return sync_modal_running_state()


_DOUBLE_CLICK_SEC = 0.4
_DOUBLE_CLICK_PX = 15
_POINTER_EVENTS = frozenset(
    {
        "LEFTMOUSE",
        "RIGHTMOUSE",
        "MIDDLEMOUSE",
        "MOUSEMOVE",
        "WHEELUPMOUSE",
        "WHEELDOWNMOUSE",
        "INBETWEEN_MOUSEMOVE",
    }
)


def _hud_override(context, obj):
    area, region = find_view3d_area_region(context.window)
    if area is None:
        return None
    selected = [o for o in iter_selected_font_objects(context)]
    if obj is not None and obj not in selected:
        selected.insert(0, obj)
    kwargs = {
        "window": context.window,
        "screen": context.window.screen,
        "area": area,
        "region": region,
        "space_data": area.spaces.active,
    }
    if obj is not None:
        kwargs["object"] = obj
        kwargs["active_object"] = obj
        kwargs["selected_objects"] = selected
    return context.temp_override(**kwargs)


def _run_hud_op(context, obj, callback, *, undo=False):
    override = _hud_override(context, obj)
    if override is None:
        return
    with override:
        if undo:
            push_undo()
        callback()


def _hud_ui_scale(context):
    prefs = get_addon_prefs(context)
    return max(context.preferences.system.ui_scale, 0.5) * prefs.hud_scale


def _spacing_mode(item_id):
    return {
        "font_size": "SIZE",
        "char_spacing": "CHAR",
        "word_spacing": "WORD",
        "line_height": "LINE",
        "shear": "SHEAR",
        "strike_position": "STRIKE_POS",
    }.get(item_id, "PARA")


def _hud_apply_spacing(context, mode, value, *, undo=False):
    from ..utils.text_format import apply_spacing_value, iter_selected_text_data

    if undo:
        push_undo()
    for text_data in iter_selected_text_data(context):
        apply_spacing_value(text_data, mode, value)
    tag_view3d_redraw(context)


def _hud_reset_format(context, mode, *, undo=False):
    from ..utils.text_format import iter_selected_text_data, reset_format_value

    if undo:
        push_undo()
    for text_data in iter_selected_text_data(context):
        reset_format_value(text_data, mode)
    tag_view3d_redraw(context)


def _hud_handles_pointer(context, event):
    if event.type not in _POINTER_EVENTS:
        return False
    area = context.area
    region = context.region
    if area is not None and region is not None:
        if area.type != "VIEW_3D":
            return False
        if region.type == "UI":
            return False
        if region.type == "WINDOW":
            return True
    window = context.window
    if window is not None and mouse_in_view3d_ui(window, event.mouse_x, event.mouse_y):
        return False
    return False


def _pointer_coords(event):
    return event.mouse_region_x, event.mouse_region_y


def _hud_toolbar_row_hit(rects, mx, my, pad=4.0):
    if not rects:
        return False
    if hit_test(rects, mx, my) is not None:
        return True
    items = [rect for rect in rects if rect.item.kind != "separator"]
    if not items:
        return False
    x0 = min(rect.x for rect in items) - pad
    x1 = max(rect.x + rect.w for rect in items) + pad
    y0 = min(rect.y for rect in items) - pad
    y1 = max(rect.y + rect.h for rect in items) + pad
    return x0 <= mx <= x1 and y0 <= my <= y1

def _safe_state(wm):
    return getattr(wm, "th_state", None)


def _is_double_click(state, mx, my, event):
    if getattr(event, "is_mouse_double_click", False):
        state.th_last_click_time = 0.0
        return True
    now = time.perf_counter()
    dt = now - state.th_last_click_time
    dx = mx - state.th_last_click_x
    dy = my - state.th_last_click_y
    is_double = dt < _DOUBLE_CLICK_SEC and (dx * dx + dy * dy) < (_DOUBLE_CLICK_PX * _DOUBLE_CLICK_PX)
    state.th_last_click_time = now
    state.th_last_click_x = mx
    state.th_last_click_y = my
    return is_double


def _point_on_text(context, obj, mx, my):
    with view3d_region_context(context) as ok:
        if not ok:
            return False
        return point_in_text_screen_bounds(context, obj, mx, my)


def _clear_drag_state(state):
    state.th_hud_hover_id = ""
    state.th_hud_dragging = False
    state.th_hud_drag_id = ""
    state.th_hud_moving = False
    clear_slider_value_edit(state)


def _clear_hover(state):
    if state.th_hud_hover_id:
        state.th_hud_hover_id = ""
        tag_redraw()


def _ensure_text_selected(context, obj):
    if obj is None:
        return
    if not obj.select_get():
        obj.select_set(True)
    if context.view_layer.objects.active != obj:
        context.view_layer.objects.active = obj


def _click_outside_hud_and_text(rects, obj, context, mx, my):
    if _hud_toolbar_row_hit(rects, mx, my):
        return False
    if obj is not None and _point_on_text(context, obj, mx, my):
        return False
    return True


def _cancel_modal(state):
    global _RUNNING
    _clear_drag_state(state)
    _RUNNING = False
    tag_redraw()
    return {"CANCELLED"}


def _close_all_pickers(context):
    if slider_value_editing(context):
        commit_slider_value_edit(context, undo=False)
    close_font_picker(context)
    close_weight_picker(context)
    close_preset_picker(context)
    close_language_picker(context)


def _picker_keep_open_ids():
    return frozenset({"font", "font_weight", "preset"})


def _dismiss_popup_menus(context):
    window = context.window
    if window is None:
        return
    for area in list(window.screen.areas):
        if area.type == "MENU":
            area.tag_close()


def _handle_dropdown(context, obj, item, state):
    _ensure_text_selected(context, obj)
    if item.id == "font" and item.op:
        opmod, opname = item.op.split(".", 1)

        def _toggle_font(opmod=opmod, opname=opname):
            getattr(getattr(bpy.ops, opmod), opname)()

        _run_hud_op(context, obj, _toggle_font)
        return

    if item.id == "preset" and item.op:
        opmod, opname = item.op.split(".", 1)

        def _toggle_preset(opmod=opmod, opname=opname):
            getattr(getattr(bpy.ops, opmod), opname)()

        _run_hud_op(context, obj, _toggle_preset)
        return

    if item.id == "font_weight" and item.op:
        opmod, opname = item.op.split(".", 1)

        def _toggle_weight(opmod=opmod, opname=opname):
            getattr(getattr(bpy.ops, opmod), opname)()

        _run_hud_op(context, obj, _toggle_weight)
        return

    menu_id = item.op
    if not menu_id:
        return

    if getattr(state, "th_hud_open_menu", "") == menu_id:
        state.th_hud_open_menu = ""
        _dismiss_popup_menus(context)
        return

    state.th_hud_open_menu = menu_id
    _run_hud_op(context, obj, lambda mid=menu_id: bpy.ops.wm.call_menu(name=mid))


def _handle_hud_press(context, event, obj, text_data, state, rects):
    rect = hit_test(rects, event.mouse_region_x, event.mouse_region_y)
    if rect is None:
        if slider_value_editing(context):
            commit_slider_value_edit(context, undo=True)
            tag_redraw()
            return {"RUNNING_MODAL"}
        return None

    _ensure_text_selected(context, obj)
    item = rect.item
    if item.kind == "drag":
        state.th_hud_moving = True
        state.th_hud_move_start_x = event.mouse_region_x
        state.th_hud_move_start_y = event.mouse_region_y
        state.th_hud_move_base_x, state.th_hud_move_base_y = get_hud_offset(obj)
        tag_redraw()
        return {"RUNNING_MODAL"}
    if item.kind == "dropdown":
        _handle_dropdown(context, obj, item, state)
        return {"RUNNING_MODAL"}
    if item.kind == "spacing_slider":
        scale = _hud_ui_scale(context)
        if try_begin_slider_value_edit(
            context,
            rect,
            text_data,
            event.mouse_region_x,
            event.mouse_region_y,
            scale,
        ):
            tag_redraw()
            return {"RUNNING_MODAL"}
        if slider_value_editing(context):
            commit_slider_value_edit(context, undo=False)
        if slider_reset_hit(rect, event.mouse_region_x, event.mouse_region_y) and item.reset_mode:
            mode = item.reset_mode
            _hud_reset_format(context, mode, undo=True)
            tag_redraw()
            return {"RUNNING_MODAL"}
        if event.mouse_region_x >= slider_track_start(rect, _hud_ui_scale(context)):
            state.th_hud_dragging = True
            state.th_hud_drag_id = rect.id
            mode = item.op_kwargs.get("mode", _spacing_mode(rect.id))
            val = slider_value_from_mouse(
                rect, event.mouse_region_x, text_data, rect.id, _hud_ui_scale(context)
            )
            _hud_apply_spacing(context, mode, val, undo=True)
            tag_redraw()
        return {"RUNNING_MODAL"}
    if item.kind == "button" and item.op:
        opmod, opname = item.op.split(".", 1)

        def _invoke_button(opmod=opmod, opname=opname):
            getattr(getattr(bpy.ops, opmod), opname)()

        _run_hud_op(context, obj, _invoke_button, undo=True)
        tag_redraw()
        return {"RUNNING_MODAL"}
    if item.op:
        opmod, opname = item.op.split(".", 1)

        def _invoke_op(opmod=opmod, opname=opname, kwargs=dict(item.op_kwargs)):
            getattr(getattr(bpy.ops, opmod), opname)(**kwargs)

        _run_hud_op(context, obj, _invoke_op, undo=True)
    tag_redraw()
    return {"RUNNING_MODAL"}


class _HudPointerEvent:
    __slots__ = ("mouse_region_x", "mouse_region_y")

    def __init__(self, mx, my):
        self.mouse_region_x = mx
        self.mouse_region_y = my

class TH_OT_hud_modal(TextHelperOperatorMixin, Operator):
    bl_idname = "wm.texthelper_hud_modal"
    bl_label = "Text Helper HUD"
    bl_description = "Run the viewport HUD modal handler for toolbar and pickers"
    bl_options = {"INTERNAL"}

    def modal(self, context, event):
        global _RUNNING

        wm = context.window_manager
        state = _safe_state(wm)
        if state is None:
            return {"PASS_THROUGH"}

        handles_pointer = _hud_handles_pointer(context, event)
        mx, my = _pointer_coords(event)
        pointer_event = _HudPointerEvent(mx, my)

        prev_mode = getattr(self, "_th_prev_mode", "")
        mode = context.mode
        if is_font_edit_mode_value(prev_mode) and not is_font_edit_mode(context):
            obj = get_active_text(context)
            if obj is not None and is_vertical(obj.data):
                sync_body_to_vertical_source(obj.data, context=context)
        self._th_prev_mode = mode

        if is_font_edit_mode(context):
            if not is_font_edit_mode_value(prev_mode):
                prepare_font_edit_ui(context)
            _clear_drag_state(state)
            if event.type in _POINTER_EVENTS and not handles_pointer:
                return {"PASS_THROUGH"}
            obj = get_active_text(context)
            if (
                event.type == "LEFTMOUSE"
                and event.value == "PRESS"
                and obj is not None
                and _is_double_click(state, mx, my, event)
                and not _point_on_text(context, obj, mx, my)
            ):
                exit_text_edit_mode(context, obj)
                tag_redraw()
                return {"RUNNING_MODAL"}
            return {"PASS_THROUGH"}

        obj = get_active_text(context)
        if obj is None:
            _close_all_pickers(context)
            return _cancel_modal(state)

        if event.type in _POINTER_EVENTS and not handles_pointer:
            if event.type == "MOUSEMOVE":
                _clear_hover(state)
            return {"PASS_THROUGH"}

        text_data = obj.data
        show_hud = hud_enabled(context, text_data)
        font_picker_active = font_picker_open(context)
        weight_picker_active = weight_picker_open(context)
        preset_picker_active = preset_picker_open(context)
        language_picker_active = language_picker_open(context)
        picker_active = font_picker_active or weight_picker_active or preset_picker_active or language_picker_active
        rects = get_hud_hit_rects(context, obj, text_data) if show_hud else []

        if show_hud and slider_value_editing(context):
            if getattr(event, "is_compose", False):
                tag_redraw()
                return {"RUNNING_MODAL"}
            if handle_slider_value_key(context, event) or slider_value_blocks_keymap(event):
                tag_redraw()
                return {"RUNNING_MODAL"}

        if picker_active:
            search_focused = (
                font_picker_active
                and state is not None
                and getattr(state, "th_font_picker_search_focus", False)
            )
            if search_focused and getattr(event, "is_compose", False):
                tag_redraw()
                return {"PASS_THROUGH"}

            if font_picker_active and search_focused:
                if handle_picker_key(context, event) or picker_search_blocks_keymap(event):
                    tag_redraw()
                    return {"RUNNING_MODAL"}

            if font_picker_active and event.type in {"WHEELUPMOUSE", "WHEELDOWNMOUSE"} and event.value == "PRESS":
                if not language_picker_active:
                    delta = 1 if event.type == "WHEELUPMOUSE" else -1
                    handle_picker_wheel(context, delta)
                tag_redraw()
                return {"RUNNING_MODAL"}

            if event.type == "MOUSEMOVE":
                if (
                    font_picker_active
                    and not language_picker_active
                    and getattr(state, "th_text_field_selecting", False)
                    and search_focused
                ):
                    handle_search_field_mouse_move(context, mx, my)
                elif (
                    font_picker_active
                    and not language_picker_active
                    and getattr(state, "th_font_picker_scroll_drag", False)
                ):
                    handle_picker_drag(context, my)
                else:
                    if language_picker_active:
                        handle_language_picker_hover(context, mx, my)
                    elif weight_picker_active:
                        handle_weight_picker_hover(context, mx, my)
                    elif preset_picker_active:
                        handle_preset_picker_hover(context, mx, my)
                    elif font_picker_active:
                        handle_font_picker_hover(context, mx, my)
                tag_redraw()
                return {"RUNNING_MODAL"}

            if event.type == "LEFTMOUSE" and event.value == "RELEASE":
                if font_picker_active and handle_picker_release(context):
                    tag_redraw()
                    return {"RUNNING_MODAL"}

            if event.type == "ESC" and event.value == "PRESS":
                _close_all_pickers(context)
                tag_redraw()
                return {"RUNNING_MODAL"}

            if event.type == "LEFTMOUSE" and event.value == "PRESS":
                if language_picker_active:
                    language_hit = hit_test_language_picker(context, mx, my)
                    if language_hit is not None:
                        handle_language_picker_click(context, language_hit)
                    elif not language_picker_panel_contains(context, mx, my):
                        close_language_picker(context)
                    tag_redraw()
                    return {"RUNNING_MODAL"}

                if preset_picker_active:
                    preset_hit = hit_test_preset_picker(context, mx, my)
                    if preset_hit is not None:
                        handle_preset_picker_click(context, preset_hit)
                        tag_redraw()
                        return {"RUNNING_MODAL"}

                if weight_picker_active:
                    weight_hit = hit_test_weight_picker(context, mx, my)
                    if weight_hit is not None:
                        handle_weight_picker_click(context, weight_hit)
                        tag_redraw()
                        return {"RUNNING_MODAL"}

                if font_picker_active:
                    font_hit = hit_test_font_picker(context, mx, my)
                    if font_hit is not None:
                        handle_font_picker_click(context, font_hit, mx, my)
                        flush_pending_report(self, state)
                        tag_redraw()
                        return {"RUNNING_MODAL"}

                toolbar_hit = hit_test(rects, mx, my) if rects else None
                if toolbar_hit is not None:
                    _ensure_text_selected(context, obj)
                    if toolbar_hit.item.id not in _picker_keep_open_ids():
                        _close_all_pickers(context)
                    result = _handle_hud_press(context, pointer_event, obj, text_data, state, rects)
                    tag_redraw()
                    return result or {"RUNNING_MODAL"}

                _close_all_pickers(context)
                tag_redraw()
                return {"PASS_THROUGH"}

        if event.type == "MOUSEMOVE":
            if show_hud and slider_value_editing(context) and getattr(state, "th_text_field_selecting", False):
                handle_slider_value_mouse_move(context, mx, _hud_ui_scale(context))
                tag_redraw()
                return {"RUNNING_MODAL"}
            if show_hud and rects:
                rect = hit_test(rects, mx, my)
                state.th_hud_hover_id = rect.id if rect else ""
                if state.th_hud_moving:
                    dx = mx - state.th_hud_move_start_x
                    dy = my - state.th_hud_move_start_y
                    set_hud_offset(
                        obj,
                        state.th_hud_move_base_x + dx,
                        state.th_hud_move_base_y + dy,
                    )
                    tag_redraw()
                    return {"RUNNING_MODAL"}
                if state.th_hud_dragging and state.th_hud_drag_id in SPACING_SLIDER_IDS:
                    drag_rect = next(r for r in rects if r.id == state.th_hud_drag_id)
                    drag_scale = _hud_ui_scale(context)
                    val = slider_value_from_mouse(
                        drag_rect, mx, text_data, state.th_hud_drag_id, drag_scale
                    )
                    mode = _spacing_mode(state.th_hud_drag_id)
                    _hud_apply_spacing(context, mode, val)
                tag_redraw()
            return {"PASS_THROUGH"}

        if event.type == "LEFTMOUSE":
            if event.value == "PRESS":
                if show_hud and rects:
                    result = _handle_hud_press(context, pointer_event, obj, text_data, state, rects)
                    if result is not None:
                        return result
                    if _hud_toolbar_row_hit(rects, mx, my):
                        _ensure_text_selected(context, obj)
                        tag_redraw()
                        return {"RUNNING_MODAL"}

                if slider_value_editing(context):
                    commit_slider_value_edit(context, undo=True)
                    tag_redraw()
                    return {"RUNNING_MODAL"}

                if _click_outside_hud_and_text(rects, obj, context, mx, my):
                    return {"PASS_THROUGH"}

                if obj and _is_double_click(state, mx, my, event) and _point_on_text(context, obj, mx, my):
                    _close_all_pickers(context)
                    if enter_text_edit_mode(context, obj):
                        tag_redraw()
                    return {"RUNNING_MODAL"}

                return {"PASS_THROUGH"}

            if event.value == "RELEASE" and show_hud:
                if slider_value_editing(context) and handle_slider_value_mouse_release(context):
                    tag_redraw()
                    return {"RUNNING_MODAL"}
                if state.th_hud_dragging or state.th_hud_moving:
                    state.th_hud_dragging = False
                    state.th_hud_drag_id = ""
                    state.th_hud_moving = False
                    tag_redraw()
                    return {"RUNNING_MODAL"}

        if show_hud and event.type in {"ESC", "RIGHTMOUSE"} and (state.th_hud_dragging or state.th_hud_moving):
            if state.th_hud_moving:
                set_hud_offset(obj, state.th_hud_move_base_x, state.th_hud_move_base_y)
            state.th_hud_dragging = False
            state.th_hud_drag_id = ""
            state.th_hud_moving = False
            tag_redraw()
            return {"RUNNING_MODAL"}

        return {"PASS_THROUGH"}

    def cancel(self, context):
        global _RUNNING
        _RUNNING = False
        state = _safe_state(context.window_manager)
        if state:
            _clear_drag_state(state)
        tag_redraw()

    def invoke(self, context, event):
        global _RUNNING
        sync_modal_running_state(context)
        if modal_running():
            return {"CANCELLED"}
        obj = get_active_text(context)
        if obj is None:
            return {"CANCELLED"}

        area, region = find_view3d_area_region(context.window)
        if area is None:
            return {"CANCELLED"}

        with context.temp_override(
            window=context.window,
            screen=context.window.screen,
            area=area,
            region=region,
            space_data=area.spaces.active,
        ):
            context.window_manager.modal_handler_add(self)
        _RUNNING = True
        tag_redraw()
        return {"RUNNING_MODAL"}


class TH_OT_hud_ensure_modal(TextHelperOperatorMixin, Operator):
    bl_idname = "wm.texthelper_hud_ensure_modal"
    bl_label = "Ensure HUD Modal"
    bl_description = "Ensure the HUD modal operator is running"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        sync_modal_running_state(context)
        if modal_running() or get_active_text(context) is None:
            return {"FINISHED"}
        override = view3d_override(context)
        if override is None:
            return {"FINISHED"}
        with override:
            bpy.ops.wm.texthelper_hud_modal("INVOKE_DEFAULT")
        return {"FINISHED"}


class TH_OT_hide_hud(ActiveFontPollMixin, Operator):
    bl_idname = "wm.texthelper_hide_hud"
    bl_label = "Hide Floating Toolbar"
    bl_description = "Hide the floating toolbar for this text object"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = get_active_text(context)
        if obj is None:
            return {"CANCELLED"}
        from ..hud.hit_test import set_hud_visibility

        set_hud_visibility(obj.data.text_helper, False)
        tag_redraw()
        return {"FINISHED"}


class TH_OT_show_hud(ActiveFontPollMixin, Operator):
    bl_idname = "wm.texthelper_show_hud"
    bl_label = "Show Floating Toolbar"
    bl_description = "Display the floating text toolbar below the selected text in the 3D viewport"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        if get_active_text(context) is None:
            self.report({"WARNING"}, _("Select a text object first"))
            return {"CANCELLED"}
        prefs = get_addon_prefs(context)
        if prefs is None or not getattr(prefs, "show_floating_toolbar", True):
            self.report({"INFO"}, _("Enable Floating Toolbar in add-on preferences"))
            return {"CANCELLED"}
        obj = get_active_text(context)
        from ..hud.hit_test import set_hud_visibility

        set_hud_visibility(obj.data.text_helper, True)
        bpy.ops.wm.texthelper_hud_ensure_modal()
        tag_redraw()
        self.report({"INFO"}, _("Floating toolbar shown — look below the text in the 3D viewport"))
        return {"FINISHED"}


class TH_OT_toggle_floating_toolbar(TextHelperOperatorMixin, Operator):
    bl_idname = "wm.texthelper_toggle_toolbar"
    bl_label = "Toggle Floating Toolbar"
    bl_description = "Show or hide the floating toolbar in the 3D viewport"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        from ..utils.text_format import get_active_text

        if get_active_text(context) is not None:
            return True
        prefs = get_addon_prefs(context)
        if prefs_are_editable(prefs):
            return True
        cls.poll_message_set(_("Select a text object or open add-on preferences"))
        return False

    def execute(self, context):
        from ..utils.addon_prefs import get_addon_prefs, prefs_are_editable

        prefs = get_addon_prefs(context)
        obj = get_active_text(context)

        if obj is not None:
            if not getattr(prefs, "show_floating_toolbar", True):
                self.report({"INFO"}, _("Enable Floating Toolbar in add-on preferences"))
                return {"CANCELLED"}
            from ..hud.hit_test import hud_enabled, set_hud_visibility

            text_data = obj.data
            visible = not hud_enabled(context, text_data)
            set_hud_visibility(text_data.text_helper, visible)
            if visible:
                bpy.ops.wm.texthelper_hud_ensure_modal()
        else:
            if not prefs_are_editable(prefs):
                return {"CANCELLED"}
            prefs.show_floating_toolbar = not getattr(prefs, "show_floating_toolbar", True)

        tag_view3d_redraw(context)
        tag_redraw()
        return {"FINISHED"}


def register():
    bpy.utils.register_class(TH_OT_hud_modal)
    bpy.utils.register_class(TH_OT_hud_ensure_modal)
    bpy.utils.register_class(TH_OT_hide_hud)
    bpy.utils.register_class(TH_OT_show_hud)
    bpy.utils.register_class(TH_OT_toggle_floating_toolbar)


def unregister():
    global _RUNNING
    _RUNNING = False
    for cls in (
        TH_OT_toggle_floating_toolbar,
        TH_OT_show_hud,
        TH_OT_hide_hud,
        TH_OT_hud_ensure_modal,
        TH_OT_hud_modal,
    ):
        bpy.utils.unregister_class(cls)
