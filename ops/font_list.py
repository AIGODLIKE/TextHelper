"""System font list UI and operators."""

import bpy
from bpy.types import Operator, UIList

from ..i18n import _
from ..utils.operator_poll import ActiveFontDataPollMixin, ActiveFontPollMixin, WindowManagerPollMixin
from ..utils.addon_prefs import get_addon_prefs, prefs_are_editable
from ..utils.font_loader import (
    assign_font,
    ensure_font_catalog,
    font_catalog_loading,
    font_catalog_needs_refresh,
    is_current_font,
    queue_font_catalog,
    refresh_font_catalog,
    reset_font_catalog_scan,
)
from ..utils.font_language import catalog_item_passes_language, catalog_item_passes_name, get_language_filter, get_language_label
from ..utils.font_preview import get_font_icon, invalidate_font_previews, queue_font_preview, tag_ui_redraw
from ..utils.text_format import get_active_text_data
from ..utils.text_frame import tag_view3d_redraw
from ..utils.font_glyph import invalidate_glyph_cache
from ..hud.draw import tag_redraw
from ..hud.font_picker import close_picker

_MENU_FONT_ROWS = 8


def _preview_list_scale(prefs):
    return max(1.0, float(getattr(prefs, "font_preview_ui_scale", 3.5)))


def _draw_font_card(layout, context, item, active):
    """Reference-style card: small name row + large preview line below."""
    prefs = get_addon_prefs(context)
    box = layout.box()
    col = box.column(align=True)

    name_row = col.row(align=True)
    name_row.scale_y = 0.78
    if active:
        name_row.label(text="", icon="CHECKMARK")
    op = name_row.operator(
        "font.texthelper_apply_system_font",
        text=item.display_name,
        emboss=False,
        depress=active,
    )
    op.filepath = item.filepath

    if not getattr(prefs, "font_preview_icons", True):
        return

    icon_id = get_font_icon(context, item.filepath, item.display_name)
    if icon_id:
        preview_row = col.row(align=True)
        preview_row.alignment = "LEFT"
        preview_row.template_icon(icon_value=icon_id, scale=_preview_list_scale(prefs))
    else:
        queue_font_preview(context, item.filepath, item.display_name)
        loading = col.row(align=True)
        loading.scale_y = 0.7
        loading.label(text=_("Preview loading…"), icon="TIME")


class TEXTHELPER_UL_system_fonts(UIList):
    bl_idname = "TEXTHELPER_UL_system_fonts"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type == "GRID":
            layout.alignment = "CENTER"
            layout.label(text="", icon="FONT_DATA")
            return

        text_data = get_active_text_data(context)
        active = is_current_font(text_data, item.filepath)
        _draw_font_card(layout, context, item, active)

    def filter_items(self, context, data, propname):
        items = getattr(data, propname)
        state = context.window_manager.th_state
        filter_text = (state.font_filter or "").strip().lower()
        sort_mode = state.font_sort or "NAME_AZ"
        lang = get_language_filter(context.window_manager)

        flt_flags = []
        for item in items:
            if not catalog_item_passes_name(item, filter_text):
                flt_flags.append(0)
            elif not catalog_item_passes_language(item, lang):
                flt_flags.append(0)
            else:
                flt_flags.append(self.bitflag_filter_item)

        indices = list(range(len(items)))
        reverse = sort_mode == "NAME_ZA"
        indices.sort(key=lambda i: items[i].display_name.lower(), reverse=reverse)
        return flt_flags, indices


def _draw_font_list_header(layout, context, wm):
    """Sort + language menu + custom preview phrase."""
    prefs = get_addon_prefs(context)
    state = wm.th_state
    row = layout.row(align=True)
    row.prop(state, "font_sort", text="")
    row.menu(
        "TEXTHELPER_MT_font_language",
        text=_(get_language_label(get_language_filter(wm))),
        icon="NONE",
    )
    if prefs_are_editable(prefs):
        row.prop(
            prefs,
            "font_preview_sample",
            text="",
            icon="FONT_DATA",
            placeholder=_("Enter preview text…"),
        )
    else:
        row.label(text=_("Enter preview text…"), icon="FONT_DATA")


def _draw_font_filter_row(layout, wm):
    row = layout.row(align=True)
    row.prop(wm.th_state, "font_filter", text="", icon="VIEWZOOM", placeholder=_("Search fonts…"))
    row.operator("font.texthelper_refresh_system_fonts", text="", icon="FILE_REFRESH")


def _draw_font_catalog_status(layout, wm):
    if wm.th_state.font_catalog:
        return False
    if font_catalog_loading():
        layout.label(text=_("Loading fonts…"), icon="TIME")
    elif font_catalog_needs_refresh(wm):
        layout.label(text=_("Click refresh to load system fonts"), icon="INFO")
    else:
        layout.label(text=_("Loading fonts…"), icon="TIME")
    return True


def draw_font_picker_popup(layout, context):
    """Compact vertical list for Menu popups (template_list breaks in menus)."""
    wm = context.window_manager
    queue_font_catalog(wm)

    _draw_font_list_header(layout, context, wm)
    _draw_font_filter_row(layout, wm)

    if _draw_font_catalog_status(layout, wm):
        return

    text_data = get_active_text_data(context)
    filt = wm.th_state.font_filter.strip().lower()
    lang = get_language_filter(wm)
    col = layout.column(align=False)
    shown = 0
    for item in wm.th_state.font_catalog:
        if not catalog_item_passes_name(item, filt):
            continue
        if not catalog_item_passes_language(item, lang):
            continue
        if shown >= _MENU_FONT_ROWS:
            col.label(text=_("Type in search to narrow results…"), icon="INFO")
            break
        active = is_current_font(text_data, item.filepath)
        _draw_font_card(col, context, item, active)
        shown += 1
    if shown == 0:
        col.label(text=_("No fonts match filter"), icon="INFO")


def draw_system_font_list(layout, context, rows=6, list_id="th_font_sidebar"):
    wm = context.window_manager
    queue_font_catalog(wm)
    text_data = get_active_text_data(context)

    _draw_font_list_header(layout, context, wm)
    _draw_font_filter_row(layout, wm)

    if _draw_font_catalog_status(layout, wm):
        return

    list_col = layout.column(align=False)
    list_col.template_list(
        "TEXTHELPER_UL_system_fonts",
        list_id,
        wm.th_state,
        "font_catalog",
        wm.th_state,
        "font_index",
        rows=rows,
    )

    # Warm the async preview queue for rows near the current selection.
    if wm.th_state.font_catalog:
        center = max(0, min(wm.th_state.font_index, len(wm.th_state.font_catalog) - 1))
        for i in range(max(0, center - 1), min(len(wm.th_state.font_catalog), center + rows + 1)):
            item = wm.th_state.font_catalog[i]
            queue_font_preview(context, item.filepath, item.display_name)

    if text_data and text_data.font:
        layout.label(text=_("Current: {}").format(text_data.font.name), icon="CHECKMARK")


class TH_OT_refresh_system_fonts(WindowManagerPollMixin, Operator):
    bl_idname = "font.texthelper_refresh_system_fonts"
    bl_label = "Refresh Font List"
    bl_description = "Rescan system font folders"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        reset_font_catalog_scan()
        invalidate_font_previews()
        try:
            from ..utils.font_language import invalidate_font_language_cache

            invalidate_font_language_cache()
        except Exception:
            pass
        try:
            count = refresh_font_catalog(context.window_manager, force=True)
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        tag_ui_redraw(context)
        self.report({"INFO"}, _("Found {:d} fonts").format(count))
        return {"FINISHED"}


class TH_OT_regenerate_font_previews(WindowManagerPollMixin, Operator):
    bl_idname = "font.texthelper_regenerate_font_previews"
    bl_label = "Regenerate Font Previews"
    bl_description = "Clear cached thumbnails and rebuild them with current preview settings"
    bl_options = {"REGISTER"}

    def execute(self, context):
        from ..utils.font_preview import invalidate_and_rebuild_font_previews

        invalidate_and_rebuild_font_previews(context, clear_files=True)
        self.report({"INFO"}, _("Font preview cache cleared — reopen the font list to rebuild"))
        return {"FINISHED"}


class TH_OT_toggle_font_picker(ActiveFontDataPollMixin, Operator):
    bl_idname = "font.texthelper_toggle_font_picker"
    bl_label = "Font Picker"
    bl_description = "Open or close the viewport GPU font picker"
    bl_options = {"REGISTER"}

    def execute(self, context):
        if get_active_text_data(context) is None:
            self.report({"WARNING"}, _("Select a text object first"))
            return {"CANCELLED"}

        wm = context.window_manager
        state = getattr(wm, "th_state", None)
        if state is None:
            return {"CANCELLED"}

        opening = not getattr(state, "th_font_picker_open", False)

        if not opening:
            close_picker(context)
            tag_redraw()
            return {"FINISHED"}

        from ..hud.preset_picker import close_picker as close_preset_picker
        from ..hud.weight_picker import close_picker as close_weight_picker

        close_preset_picker(context)
        close_weight_picker(context)
        state.th_hud_open_menu = ""
        from ..ops.hud_modal import _dismiss_popup_menus

        _dismiss_popup_menus(context)
        state.th_font_picker_open = True
        state.th_font_picker_scroll = 0
        state.th_font_picker_hover = -1

        try:
            ensure_font_catalog(wm)
        except Exception:
            pass
        invalidate_glyph_cache()
        from ..hud.font_picker import _ensure_picker_blf_hooks, focus_search_field, seed_picker_hover_apply

        _ensure_picker_blf_hooks()
        seed_picker_hover_apply(context)
        focus_search_field(context)
        bpy.ops.wm.texthelper_hud_ensure_modal()

        tag_redraw()
        return {"FINISHED"}


class TH_OT_toggle_weight_picker(ActiveFontDataPollMixin, Operator):
    bl_idname = "font.texthelper_toggle_weight_picker"
    bl_label = "Font Weight Picker"
    bl_description = "Open or close the viewport font weight picker"
    bl_options = {"REGISTER"}

    def execute(self, context):
        text_data = get_active_text_data(context)
        if text_data is None:
            self.report({"WARNING"}, _("Select a text object first"))
            return {"CANCELLED"}

        wm = context.window_manager
        state = getattr(wm, "th_state", None)
        if state is None:
            return {"CANCELLED"}

        from ..hud.weight_picker import close_picker as close_weight_picker, seed_picker_hover_apply, variants_for_text
        from ..utils.font_loader import ensure_font_catalog, refresh_font_catalog

        try:
            ensure_font_catalog(wm)
            if len(wm.th_state.font_catalog) == 0:
                refresh_font_catalog(wm, force=True)
        except Exception:
            pass

        opening = not getattr(state, "th_weight_picker_open", False)

        if not opening:
            close_weight_picker(context)
            tag_redraw()
            return {"FINISHED"}

        from ..hud.font_picker import close_picker as close_font_picker
        from ..hud.preset_picker import close_picker as close_preset_picker
        from ..ops.hud_modal import _dismiss_popup_menus

        close_font_picker(context)
        close_preset_picker(context)
        state.th_hud_open_menu = ""
        _dismiss_popup_menus(context)
        state.th_weight_picker_open = True
        if not variants_for_text(context, text_data):
            state.th_weight_picker_open = False
            self.report({"WARNING"}, _("No font weight information available"))
            return {"CANCELLED"}
        seed_picker_hover_apply(context)
        bpy.ops.wm.texthelper_hud_ensure_modal()
        tag_redraw()
        return {"FINISHED"}


class TH_OT_apply_system_font(ActiveFontDataPollMixin, Operator):
    bl_idname = "font.texthelper_apply_system_font"
    bl_label = "Apply Font"
    bl_description = "Apply this font to the selected text"
    bl_options = {"REGISTER", "UNDO"}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    catalog_index: bpy.props.IntProperty(default=-1, options={"HIDDEN"})
    keep_picker_open: bpy.props.BoolProperty(default=False, options={"HIDDEN"})

    def execute(self, context):
        text_data = get_active_text_data(context)
        if text_data is None:
            self.report({"WARNING"}, _("Select a text object first"))
            return {"CANCELLED"}
        try:
            font = assign_font(text_data, self.filepath)
        except FileNotFoundError:
            self.report({"ERROR"}, _("Font file not found"))
            return {"CANCELLED"}
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        if self.catalog_index >= 0:
            from ..props import set_font_catalog_index

            set_font_catalog_index(context.window_manager, self.catalog_index)
        tag_view3d_redraw(context)
        if self.keep_picker_open:
            from ..hud.draw import tag_redraw

            tag_redraw()
        else:
            from ..hud.weight_picker import close_picker as close_weight_picker

            close_weight_picker(context)
            self.report({"INFO"}, _("Font: {}").format(font.name))
        return {"FINISHED"}


classes = (
    TEXTHELPER_UL_system_fonts,
    TH_OT_refresh_system_fonts,
    TH_OT_regenerate_font_previews,
    TH_OT_toggle_font_picker,
    TH_OT_toggle_weight_picker,
    TH_OT_apply_system_font,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
