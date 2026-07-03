import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, FloatVectorProperty, IntProperty, StringProperty
from bpy.types import AddonPreferences

from .i18n import _


def _tag_hud_redraw(_self, context):
    from .utils.font_preview import tag_ui_redraw
    from .hud.draw import tag_redraw
    from .utils.text_frame import tag_view3d_redraw

    tag_ui_redraw(context)
    tag_view3d_redraw(context)
    tag_redraw()


def _tag_sidebar_redraw(_self, context):
    from .utils.font_preview import tag_ui_redraw

    tag_ui_redraw(context)


def _invalidate_font_previews(_self, context):
    from .utils.font_preview import invalidate_and_rebuild_font_previews

    invalidate_and_rebuild_font_previews(context, clear_files=True)


class TH_Preferences(AddonPreferences):
    bl_idname = "TextHelper"

    show_floating_toolbar: BoolProperty(
        name="Floating Toolbar",
        description="Show the floating toolbar near selected text in the 3D viewport",
        default=True,
        update=_tag_hud_redraw,
    )
    toolbar_offset: FloatProperty(
        name="Toolbar Offset",
        description="Distance from the top of the 3D viewport to the floating toolbar (pixels)",
        default=100.0,
        min=0.0,
        max=200.0,
        update=_tag_hud_redraw,
    )
    auto_layout_frame: BoolProperty(
        name="Auto Layout Frame",
        description="Create a layout frame automatically when adding new text",
        default=True,
    )
    hud_scale: FloatProperty(
        name="HUD Scale",
        description="Viewport HUD display scale",
        default=1.0,
        min=0.5,
        max=2.0,
        update=_tag_hud_redraw,
    )
    hud_accent_preset: EnumProperty(
        name="Accent Color",
        description="Accent color for the viewport HUD and pickers",
        items=(
            ("GREEN", "Green", "Default green accent"),
            ("BLUE", "Blue", "Blue accent"),
            ("ORANGE", "Orange", "Orange accent"),
            ("PURPLE", "Purple", "Purple accent"),
            ("PINK", "Pink", "Pink accent"),
            ("CYAN", "Cyan", "Cyan accent"),
            ("CUSTOM", "Custom", "Use the custom color below"),
        ),
        default="GREEN",
        update=_tag_hud_redraw,
    )
    hud_accent_custom: FloatVectorProperty(
        name="Custom Accent",
        description="Custom HUD accent color",
        subtype="COLOR",
        size=3,
        min=0.0,
        max=1.0,
        default=(0.12, 0.86, 0.42),
        update=_tag_hud_redraw,
    )
    font_preview_icons: BoolProperty(
        name="Font Preview Icons",
        description="Show rendered font thumbnails beside each name in the font list",
        default=True,
        update=_invalidate_font_previews,
    )
    font_preview_on_select: BoolProperty(
        name="Preview While Browsing",
        description="Apply the highlighted font while hovering or navigating the font list",
        default=True,
        update=_tag_hud_redraw,
    )
    font_preview_sample: StringProperty(
        name="Preview Text",
        description="Characters rendered inside each font thumbnail",
        default="Exploration witnesses courage, open source witnesses glory",
        update=_invalidate_font_previews,
    )
    font_preview_mode: EnumProperty(
        name="Preview Content",
        description="What to render inside the thumbnail",
        items=(
            ("OBJECT", "Text Object", "Use characters from the active text object"),
            ("SAMPLE", "Custom Text", "Use the preview text below"),
            ("NAME", "Font Name", "Use the font file display name"),
        ),
        default="OBJECT",
        update=_invalidate_font_previews,
    )
    font_preview_size: IntProperty(
        name="Preview Font Size",
        description="Maximum point size used when rendering the thumbnail image",
        default=36,
        min=12,
        max=128,
        update=_invalidate_font_previews,
    )
    font_preview_width: IntProperty(
        name="Thumbnail Width",
        description="Generated preview image width in pixels",
        default=512,
        min=120,
        max=640,
        update=_invalidate_font_previews,
    )
    font_preview_height: IntProperty(
        name="Thumbnail Height",
        description="Generated preview image height in pixels",
        default=56,
        min=28,
        max=128,
        update=_invalidate_font_previews,
    )
    font_preview_ui_scale: FloatProperty(
        name="List Preview Scale",
        description="How large each font preview appears in the sidebar list",
        default=3.5,
        min=1.0,
        max=6.0,
        update=_invalidate_font_previews,
    )
    n_panel_textbox_lines: IntProperty(
        name="N-Panel Textbox Lines",
        description="Default visible line count for the N-panel textbox (you can still drag the bottom edge to resize)",
        default=30,
        min=3,
        max=30,
        update=_tag_sidebar_redraw,
    )

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text=_("About"), icon="INFO")
        col = box.column(align=True)
        col.scale_y = 0.85
        col.label(
            text=_("Easy text input & font management with a viewport floating toolbar."),
        )
        for line in (
            _("Multi-line N-panel editor (Blender 5.2+)"),
            _("Floating toolbar near selected text in the viewport"),
            _("Style presets, alignment, and spacing controls"),
            _("Double-click text in the viewport to edit"),
        ):
            row = col.row()
            row.label(text="• " + line)

        layout.separator()
        box = layout.box()
        box.label(text=_("Viewport"), icon="VIEW3D")
        box.prop(self, "show_floating_toolbar")
        box.prop(self, "auto_layout_frame")
        box.prop(self, "toolbar_offset")
        box.prop(self, "hud_scale")
        box.prop(self, "hud_accent_preset")
        if self.hud_accent_preset == "CUSTOM":
            box.prop(self, "hud_accent_custom")

        box = layout.box()
        box.label(text=_("Sidebar"), icon="PREFERENCES")
        box.prop(self, "n_panel_textbox_lines")

        box = layout.box()
        box.label(text=_("Fonts"), icon="FONT_DATA")
        box.prop(self, "font_preview_icons")
        if self.font_preview_icons:
            sub = box.column(align=True)
            sub.prop(self, "font_preview_mode")
            if self.font_preview_mode == "SAMPLE":
                sub.prop(self, "font_preview_sample")
            row = sub.row(align=True)
            row.prop(self, "font_preview_width")
            row.prop(self, "font_preview_height")
            sub.prop(self, "font_preview_size")
            sub.prop(self, "font_preview_ui_scale")
            sub.operator("font.texthelper_regenerate_font_previews", icon="FILE_REFRESH")
        box.prop(self, "font_preview_on_select")


def register():
    from . import ADDON_PACKAGE

    TH_Preferences.bl_idname = ADDON_PACKAGE
    bpy.utils.register_class(TH_Preferences)


def unregister():
    bpy.utils.unregister_class(TH_Preferences)
