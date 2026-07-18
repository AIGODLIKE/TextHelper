import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import PropertyGroup

from .utils.text_format import STYLE_PRESETS
from .utils.text_limits import BLENDER_TEXT_BODY_MAX_LEN
from .utils.font_language import LANGUAGE_FILTER_ITEMS
from .utils.header_sliders import (
    HEADER_CHAR_SPACING_PROP,
    HEADER_LINE_HEIGHT_PROP,
    HEADER_SIZE_PROP,
    HEADER_SHEAR_PROP,
    HEADER_WORD_SPACING_PROP,
)

PRESET_ITEMS = tuple((k, v["label"], v["label"]) for k, v in STYLE_PRESETS.items())

_FONT_INDEX_GUARD = False


def unregister_font_index_deferred():
    """Compatibility hook retained for older register/unregister call sites."""


def set_font_catalog_index(wm, index):
    """Set catalog index without re-triggering font assignment."""
    global _FONT_INDEX_GUARD
    _FONT_INDEX_GUARD = True
    try:
        wm.th_state.font_index = int(index)
    finally:
        _FONT_INDEX_GUARD = False


def _update_vertical_source(self, context):
    from .utils.text_orientation import _VERTICAL_SOURCE_GUARD, sync_vertical_source_to_body
    from .utils.text_case import sync_live_text_case

    if _VERTICAL_SOURCE_GUARD:
        return
    if self.th_text_orientation != "VERTICAL":
        return
    sync_live_text_case(self.id_data)
    sync_vertical_source_to_body(self.id_data, context=context)


def _update_column_order(self, context):
    from .utils.text_orientation import is_vertical, sync_vertical_source_to_body

    if not is_vertical(self.id_data):
        return
    sync_vertical_source_to_body(self.id_data, context=context)


def _update_strike_position(self, context):
    from .utils.text_format import apply_strike_position

    text_data = self.id_data
    if text_data is None:
        return
    apply_strike_position(text_data, self.th_strike_position)
    from .utils.text_frame import tag_view3d_redraw

    tag_view3d_redraw(context)
    try:
        from .hud.draw import tag_redraw

        tag_redraw()
    except Exception:
        pass


def _update_font_index(self, context):
    if _FONT_INDEX_GUARD:
        return
    if context is None:
        return
    from .utils.font_preview import tag_ui_redraw

    tag_ui_redraw(context)


def _update_panel_buf_a(self, context):
    from .utils.ui_textbox import update_panel_buf_a as _impl

    _impl(self, context)


def _update_panel_buf_b(self, context):
    from .utils.ui_textbox import update_panel_buf_b as _impl

    _impl(self, context)


class TH_FontCatalogItem(PropertyGroup):
    display_name: StringProperty(name="Name", default="")
    filepath: StringProperty(name="Path", subtype="FILE_PATH", default="")


class TH_TextCurveProps(PropertyGroup):
    th_preset: EnumProperty(name="Style", items=PRESET_ITEMS, default="BODY")
    th_hud_offset_x: FloatProperty(
        name="HUD Offset X",
        description="Legacy HUD drag offset (migrated to the text object; not used for new data)",
        default=0.0,
        options={"HIDDEN"},
    )
    th_hud_offset_y: FloatProperty(
        name="HUD Offset Y",
        description="Legacy HUD drag offset (migrated to the text object; not used for new data)",
        default=0.0,
        options={"HIDDEN"},
    )
    th_hud_visible: BoolProperty(
        name="Show HUD",
        description="Show the floating toolbar for this text object in the viewport",
        default=True,
    )
    th_hud_user_shown: BoolProperty(
        name="HUD User Shown",
        description="User explicitly enabled the floating toolbar while auto-show is off",
        default=False,
        options={"HIDDEN"},
    )
    th_pre_bold_size: FloatProperty(
        name="Pre Bold Size",
        description="Stored size before faux-bold enlargement",
        default=0.0,
        options={"HIDDEN"},
    )
    th_text_orientation: EnumProperty(
        name="Text Orientation",
        description="Horizontal rows or vertical columns (transposed in body)",
        items=(
            ("HORIZONTAL", "Horizontal", "Horizontal text input"),
            ("VERTICAL", "Vertical", "Vertical text input"),
        ),
        default="HORIZONTAL",
    )
    th_vertical_column_order: EnumProperty(
        name="Column Order",
        description="Where the first typed column appears; Enter adds the next column",
        items=(
            ("RTL", "Right to Left", "First line is rightmost; Enter adds a column to the left"),
            ("LTR", "Left to Right", "First line is leftmost; Enter adds a column to the right"),
        ),
        default="RTL",
        update=_update_column_order,
    )
    th_vertical_source: StringProperty(
        name="Vertical Source",
        description="Horizontal input in N-panel: each line is one vertical column",
        default="",
        maxlen=BLENDER_TEXT_BODY_MAX_LEN,
        update=_update_vertical_source,
    )
    th_text_case: EnumProperty(
        name="Text Case",
        description="Letter case transform for the text content",
        items=(
            ("DEFAULT", "Default", "Original letter casing"),
            ("UPPER", "Uppercase", "All uppercase letters"),
            ("LOWER", "Lowercase", "All lowercase letters"),
        ),
        default="DEFAULT",
    )
    th_text_case_snapshot: StringProperty(
        name="Text Case Snapshot",
        description="Stored original text before case transform",
        default="",
        options={"HIDDEN"},
    )
    th_underline_enabled: BoolProperty(
        name="Underline Enabled",
        description="Logical underline toggle (mutually exclusive with strikethrough)",
        default=False,
    )
    th_strike_enabled: BoolProperty(
        name="Strikethrough Enabled",
        description="Logical strikethrough toggle (mutually exclusive with underline)",
        default=False,
    )
    th_strike_position: FloatProperty(
        name="Strike Pos",
        description="Vertical line position used when strikethrough is enabled",
        default=0.4,
        min=-0.2,
        max=0.8,
        update=_update_strike_position,
    )
    th_panel_buf_a: StringProperty(
        name="Panel Buffer A",
        default="",
        maxlen=BLENDER_TEXT_BODY_MAX_LEN,
        options={"HIDDEN"},
        update=_update_panel_buf_a,
    )
    th_panel_buf_b: StringProperty(
        name="Panel Buffer B",
        default="",
        maxlen=BLENDER_TEXT_BODY_MAX_LEN,
        options={"HIDDEN"},
        update=_update_panel_buf_b,
    )
    th_panel_buf_active: BoolProperty(
        name="Panel Buffer Active",
        default=False,
        options={"HIDDEN"},
    )
    th_panel_buf_lines: IntProperty(
        name="Panel Buffer Lines",
        default=0,
        options={"HIDDEN"},
    )
    th_panel_buf_mode: StringProperty(
        name="Panel Buffer Mode",
        default="",
        options={"HIDDEN"},
    )


class TH_WindowManagerProps(PropertyGroup):
    th_hud_hover_id: StringProperty(default="")
    th_hud_dragging: BoolProperty(default=False)
    th_hud_drag_id: StringProperty(default="")
    th_hud_slider_edit_id: StringProperty(default="")
    th_hud_slider_edit_text: StringProperty(default="")
    th_text_field_cursor: IntProperty(default=0, min=0)
    th_text_field_anchor: IntProperty(default=0, min=0)
    th_text_field_selecting: BoolProperty(default=False)
    th_hud_drag_start: FloatProperty(default=0.0)
    th_hud_moving: BoolProperty(default=False)
    th_hud_move_start_x: FloatProperty(default=0.0)
    th_hud_move_start_y: FloatProperty(default=0.0)
    th_hud_move_base_x: FloatProperty(default=0.0)
    th_hud_move_base_y: FloatProperty(default=0.0)
    th_last_click_time: FloatProperty(default=0.0)
    th_last_click_x: FloatProperty(default=0.0)
    th_last_click_y: FloatProperty(default=0.0)
    th_font_picker_open: BoolProperty(default=False)
    th_font_picker_window: StringProperty(default="", options={"HIDDEN"})
    th_font_picker_scroll: IntProperty(default=0, min=0)
    th_font_picker_hover: IntProperty(default=-1)
    th_font_picker_search_focus: BoolProperty(default=False)
    th_font_picker_preview_focus: BoolProperty(default=False)
    th_font_picker_hide_unsupported: BoolProperty(
        name="Hide Unsupported Fonts",
        description="Only list fonts that contain every non-space character in the preview text",
        default=True,
    )
    th_font_picker_multi_weight_only: BoolProperty(
        name="Multi-Weight Fonts Only",
        description="Only list font families that have more than one weight on disk",
        default=False,
    )
    th_font_picker_favorites_only: BoolProperty(
        name="Favorites Only",
        description="Only list font families marked as favorites",
        default=False,
    )
    th_font_picker_variable_only: BoolProperty(
        name="Variable Fonts Only",
        description="Only list OpenType variable font files",
        default=False,
    )
    th_font_picker_scroll_drag: BoolProperty(default=False)
    th_font_picker_scroll_drag_y: FloatProperty(default=0.0)
    th_font_picker_scroll_drag_base: IntProperty(default=0)
    th_font_picker_chip_hover: StringProperty(default="")
    th_font_picker_chip_press: StringProperty(default="")
    th_font_picker_pointer_x: FloatProperty(default=-1.0)
    th_font_picker_pointer_y: FloatProperty(default=-1.0)
    th_pending_report: StringProperty(default="")
    th_weight_picker_open: BoolProperty(default=False)
    th_weight_picker_window: StringProperty(default="", options={"HIDDEN"})
    th_weight_picker_hover: IntProperty(default=-1)
    th_weight_picker_scroll: IntProperty(default=0, min=0, options={"HIDDEN"})
    th_preset_picker_open: BoolProperty(default=False)
    th_preset_picker_window: StringProperty(default="", options={"HIDDEN"})
    th_preset_picker_hover: StringProperty(default="")
    th_language_picker_open: BoolProperty(default=False)
    th_language_picker_window: StringProperty(default="", options={"HIDDEN"})
    th_language_picker_hover: StringProperty(default="")
    th_hud_open_menu: StringProperty(default="")
    th_hud_expand_id: StringProperty(
        name="HUD Expand Panel",
        description="Expanded slider row below the floating toolbar",
        default="",
    )
    font_catalog: CollectionProperty(type=TH_FontCatalogItem)
    font_index: IntProperty(name="Font Index", default=0, update=_update_font_index)
    font_filter: StringProperty(
        name="Search Fonts",
        description="Filter the system font list",
        default="",
        options={"TEXTEDIT_UPDATE"},
    )
    font_sort: EnumProperty(
        name="Font Sort",
        description="Sort order for the system font list",
        items=(
            ("RECENT", "Recently Used", "Show recently applied font families first"),
            ("NAME_AZ", "Name A-Z", "Sort fonts by name ascending"),
            ("NAME_ZA", "Name Z-A", "Sort fonts by name descending"),
        ),
        default="RECENT",
    )
    font_language: EnumProperty(
        name="Script Filter",
        description="Filter fonts by supported writing system",
        items=LANGUAGE_FILTER_ITEMS,
        default="ALL",
    )
    font_picker_preview: StringProperty(
        name="Font Picker Preview",
        description="Custom preview phrase shown in the viewport font picker",
        default="",
    )
    th_header_size: FloatProperty(**HEADER_SIZE_PROP)
    th_header_char_spacing: FloatProperty(**HEADER_CHAR_SPACING_PROP)
    th_header_word_spacing: FloatProperty(**HEADER_WORD_SPACING_PROP)
    th_header_line_height: FloatProperty(**HEADER_LINE_HEIGHT_PROP)
    th_header_shear: FloatProperty(**HEADER_SHEAR_PROP)


def register():
    bpy.utils.register_class(TH_FontCatalogItem)
    bpy.utils.register_class(TH_TextCurveProps)
    bpy.utils.register_class(TH_WindowManagerProps)
    bpy.types.TextCurve.text_helper = PointerProperty(type=TH_TextCurveProps)
    bpy.types.WindowManager.th_state = PointerProperty(type=TH_WindowManagerProps)


def unregister():
    if hasattr(bpy.types.TextCurve, "text_helper"):
        del bpy.types.TextCurve.text_helper
    if hasattr(bpy.types.WindowManager, "th_state"):
        del bpy.types.WindowManager.th_state
    bpy.utils.unregister_class(TH_WindowManagerProps)
    bpy.utils.unregister_class(TH_TextCurveProps)
    bpy.utils.unregister_class(TH_FontCatalogItem)
