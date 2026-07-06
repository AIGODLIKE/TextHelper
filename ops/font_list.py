"""System font list UI and operators."""

import bpy
from bpy.types import Operator, UIList

from ..i18n import _
from ..utils.addon_prefs import get_addon_prefs, prefs_are_editable
from ..utils.operator_poll import ActiveFontDataPollMixin, ActiveFontPollMixin, WindowManagerPollMixin
from ..utils.font_loader import (
    assign_font,
    ensure_font_catalog,
    font_catalog_loading,
    font_catalog_needs_refresh,
    is_current_font,
    queue_font_catalog,
    refresh_font_catalog,
)
from ..utils.font_catalog_filter import (
    catalog_item_passes_filters,
    dedupe_header_font_filter_items,
    filtered_font_groups,
    font_catalog_filter_state,
    font_filters_differ_from_defaults,
    invalidate_catalog_filter_cache,
    reset_font_catalog_filters,
    sorted_catalog_indices,
    visible_catalog_indices as shared_visible_catalog_indices,
)
from ..utils.font_family import family_weight_counts, header_font_display_label
from ..utils.font_language import catalog_item_passes_language, catalog_item_passes_name, get_language_filter, get_language_label
from ..utils.font_preview import get_font_icon, invalidate_font_previews, queue_font_preview, tag_ui_redraw
from ..utils.text_format import get_active_text_data
from ..utils.text_frame import tag_view3d_redraw
from ..hud.draw import tag_redraw
from ..hud.font_picker import close_picker

_MENU_FONT_ROWS = 8


def _draw_font_favorite_toggle(row, context, filepath, *, keep_picker_open=False, solo_icons=False):
    """Favorite toggle for RNA UI lists."""
    from ..utils.font_favorites import is_family_favorite

    favorited = is_family_favorite(context, filepath)
    fav_cell = row.row(align=True)
    fav_cell.ui_units_x = 1.05
    if solo_icons:
        op = fav_cell.operator(
            "font.texthelper_toggle_font_favorite",
            text="",
            icon="SOLO_ON" if favorited else "SOLO_OFF",
            depress=favorited,
        )
    else:
        op = fav_cell.operator(
            "font.texthelper_toggle_font_favorite",
            text="",
            icon="BOOKMARKS",
            depress=favorited,
        )
    op.filepath = filepath
    op.keep_picker_open = keep_picker_open


def _preview_list_scale(prefs):
    return max(1.0, float(getattr(prefs, "font_preview_ui_scale", 3.5)))


def _draw_font_card(layout, context, item, active, *, catalog_index=-1):
    """Reference-style card: small name row + large preview line below."""
    from ..utils.font_favorites import is_family_favorite
    from ..utils.font_loader import is_builtin_bfont_catalog

    prefs = get_addon_prefs(context)
    wm = context.window_manager
    catalog = wm.th_state.font_catalog if wm and getattr(wm, "th_state", None) else None
    favorited = is_family_favorite(context, item.filepath)
    box = layout.box()
    col = box.column(align=True)

    name_row = col.row(align=True)
    name_row.scale_y = 0.78
    _draw_font_favorite_toggle(name_row, context, item.filepath)
    if active:
        name_row.label(text="", icon="CHECKMARK")
    label = item.display_name
    if catalog is not None and catalog_index >= 0:
        label = header_font_display_label(context, catalog, catalog_index, item)
    op = name_row.operator(
        "font.texthelper_apply_system_font",
        text=label,
        emboss=False,
        depress=active,
    )
    op.filepath = item.filepath

    if not getattr(prefs, "font_preview_icons", True):
        return

    if is_builtin_bfont_catalog(item.filepath):
        note = col.row(align=True)
        note.scale_y = 0.7
        note.label(text=_("Built-in font preview not supported yet"), icon="INFO")
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
        _draw_font_card(layout, context, item, active, catalog_index=index)

    def filter_items(self, context, data, propname):
        return filter_font_catalog_items(self, context, data, propname)


def _font_catalog_filter_state(context):
    return font_catalog_filter_state(context)


def _catalog_item_visible(context, item, *, filters, weight_counts=None):
    return catalog_item_passes_filters(context, item, filters, weight_counts=weight_counts)


def visible_font_catalog_indices(context):
    wm = context.window_manager
    return shared_visible_catalog_indices(context, wm.th_state.font_catalog)


def filter_font_catalog_items(ui_list, context, data, propname):
    items = getattr(data, propname)
    filters = font_catalog_filter_state(context)
    weight_counts = family_weight_counts(items, context) if filters["multi_weight_only"] else None

    flt_flags = []
    for item in items:
        if catalog_item_passes_filters(context, item, filters, weight_counts=weight_counts):
            flt_flags.append(ui_list.bitflag_filter_item)
        else:
            flt_flags.append(0)

    indices = sorted_catalog_indices(items, filters["sort_mode"], context)
    return flt_flags, indices


def filter_header_font_catalog_items(ui_list, context, data, propname):
    flt_flags, indices = filter_font_catalog_items(ui_list, context, data, propname)
    catalog = getattr(data, propname)
    return dedupe_header_font_filter_items(ui_list, catalog, flt_flags, indices)


def _draw_header_font_filter_chips(layout, context, state):
    row = layout.row(align=True)
    row.scale_y = 0.9
    hide = state.th_font_picker_hide_unsupported
    row.prop(
        state,
        "th_font_picker_hide_unsupported",
        text=_("Hide unsupported") if hide else _("Show all fonts"),
        toggle=True,
    )
    multi = state.th_font_picker_multi_weight_only
    row.prop(
        state,
        "th_font_picker_multi_weight_only",
        text=_("Multi-weight only") if multi else _("All font families"),
        toggle=True,
    )
    row = layout.row(align=True)
    row.scale_y = 0.9
    favorites = state.th_font_picker_favorites_only
    row.prop(
        state,
        "th_font_picker_favorites_only",
        text=_("Favorites only") if favorites else _("All favorites"),
        toggle=True,
    )
    variable = state.th_font_picker_variable_only
    row.prop(
        state,
        "th_font_picker_variable_only",
        text=_("Variable fonts") if variable else _("All font types"),
        toggle=True,
    )
    reset_row = row.row(align=True)
    reset_row.operator(
        "font.texthelper_reset_font_filters",
        text="",
        icon="X",
    )


def _draw_header_font_list_header(layout, context, wm):
    """Sort, language, and filter toggles for the header font popover."""
    state = wm.th_state
    row = layout.row(align=True)
    row.prop(state, "font_sort", text="")
    row.menu(
        "TEXTHELPER_MT_font_language",
        text=_(get_language_label(get_language_filter(wm))),
        icon="NONE",
    )
    _draw_header_font_filter_chips(layout, context, state)


def _draw_font_filter_row(layout, wm, context, *, compact_refresh=False):
    row = layout.row(align=True)
    row.prop(wm.th_state, "font_filter", text="", icon="VIEWZOOM", placeholder=_("Search fonts…"))
    row.operator(
        "font.texthelper_refresh_system_fonts",
        text="" if compact_refresh else _("Force Refresh Previews"),
        icon="FILE_REFRESH",
    )


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
    _draw_font_filter_row(layout, wm, context)

    if _draw_font_catalog_status(layout, wm):
        return

    text_data = get_active_text_data(context)
    filters = font_catalog_filter_state(context)
    weight_counts = family_weight_counts(wm.th_state.font_catalog, context) if filters["multi_weight_only"] else None
    col = layout.column(align=False)
    shown = 0
    for item in wm.th_state.font_catalog:
        if not catalog_item_passes_filters(context, item, filters, weight_counts=weight_counts):
            continue
        if shown >= _MENU_FONT_ROWS:
            col.label(text=_("Type in search to narrow results…"), icon="INFO")
            break
        active = is_current_font(text_data, item.filepath)
        _draw_font_card(col, context, item, active)
        shown += 1
    if shown == 0:
        col.label(text=_("No matching fonts. Try turning off filters."), icon="INFO")


def draw_system_font_list(layout, context, rows=6, list_id="th_font_sidebar"):
    wm = context.window_manager
    queue_font_catalog(wm)
    text_data = get_active_text_data(context)

    _draw_font_list_header(layout, context, wm)
    _draw_font_filter_row(layout, wm, context)

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
    bl_label = "Force Refresh Previews"
    bl_description = (
        "Rescan system font folders, clear failed-load caches, "
        "and rebuild font preview thumbnails"
    )
    bl_options = {"REGISTER"}

    def execute(self, context):
        from ..utils.font_refresh import perform_font_system_refresh

        try:
            perform_font_system_refresh(context)
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, _("Font information refreshed"))
        return {"FINISHED"}


class TH_OT_regenerate_font_previews(WindowManagerPollMixin, Operator):
    bl_idname = "font.texthelper_regenerate_font_previews"
    bl_label = "Regenerate Font Previews"
    bl_description = "Clear cached thumbnails and rebuild them with current preview settings"
    bl_options = {"REGISTER"}

    def execute(self, context):
        from ..utils.font_preview import invalidate_and_rebuild_font_previews

        invalidate_and_rebuild_font_previews(context, clear_files=True)
        self.report({"INFO"}, _("Font preview cache cleared — rebuilding thumbnails"))
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
        from ..hud.slider_input import dismiss_slider_value_edit

        dismiss_slider_value_edit(context, undo=False)
        state.th_hud_open_menu = ""
        from ..ops.hud_modal import _dismiss_popup_menus

        _dismiss_popup_menus(context)
        state.th_font_picker_open = True
        state.th_font_picker_scroll = 0
        state.th_font_picker_hover = -1

        queue_font_catalog(wm)
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
        from ..hud.slider_input import dismiss_slider_value_edit

        dismiss_slider_value_edit(context, undo=False)
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
    record_recent: bpy.props.BoolProperty(default=True, options={"HIDDEN"})

    def execute(self, context):
        from ..utils.text_format import iter_selected_text_data

        applied = False
        font = None
        for text_data in iter_selected_text_data(context):
            try:
                font = assign_font(text_data, self.filepath)
            except FileNotFoundError:
                self.report({"ERROR"}, _("Font file not found"))
                return {"CANCELLED"}
            except Exception as exc:
                self.report({"ERROR"}, str(exc))
                return {"CANCELLED"}
            applied = True
        if not applied:
            self.report({"WARNING"}, _("Select a text object first"))
            return {"CANCELLED"}
        if self.catalog_index >= 0:
            from ..props import set_font_catalog_index

            set_font_catalog_index(context.window_manager, self.catalog_index)
        if self.record_recent:
            from ..utils.font_recent import touch_recent_family

            touch_recent_family(context, self.filepath)
        tag_view3d_redraw(context)
        if self.keep_picker_open:
            from ..hud.draw import tag_redraw

            tag_redraw()
        else:
            from ..hud.weight_picker import close_picker as close_weight_picker

            close_weight_picker(context)
            self.report({"INFO"}, _("Font: {}").format(font.name if font else bpy.path.display_name(self.filepath)))
        return {"FINISHED"}


class TH_OT_reset_font_filters(WindowManagerPollMixin, Operator):
    bl_idname = "font.texthelper_reset_font_filters"
    bl_label = "Reset Font Filters"
    bl_description = "Clear search text and restore sort, script filter, and filter chips to defaults"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        from ..i18n import _

        if reset_font_catalog_filters(context):
            message = _("Font filters restored to defaults")
        else:
            message = _("Font filters already at defaults")
        tag_ui_redraw(context)
        tag_redraw()
        self.report({"INFO"}, message)
        return {"FINISHED"}


classes = (
    TEXTHELPER_UL_system_fonts,
    TH_OT_refresh_system_fonts,
    TH_OT_regenerate_font_previews,
    TH_OT_toggle_font_picker,
    TH_OT_toggle_weight_picker,
    TH_OT_apply_system_font,
    TH_OT_reset_font_filters,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
