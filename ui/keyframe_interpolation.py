"""
Graph Editorのトップバーに新規キーフレーム補間タイプの切り替えボタンを追加。

主な機能:
- CONSTANT/LINEAR/BEZIER補間タイプの素早い切り替え
- アイコンのみ表示でコンパクト

使用例: アニメーション作業中に補間タイプを素早く変更したい時
"""

from bpy.types import GRAPH_MT_editor_menus

from ..utils.menu_utils import add_menu_draw_func, remove_menu_draw_func
from .header_tools import is_header_tool_visible


def draw_keyframe_interpolation_toggle(self, context):
    """GRAPH_MT_editor_menusに補間タイプの切り替えボタンを追加"""
    if not is_header_tool_visible(context, "show_graph_interpolation"):
        return

    layout = self.layout

    prefs = context.preferences

    layout.separator()

    # CONSTANT, LINEAR, BEZIERのみをicon onlyで表示
    layout.prop_enum(
        prefs.edit,
        "keyframe_new_interpolation_type",
        "CONSTANT",
        text="",
        icon="IPO_CONSTANT",
    )
    layout.prop_enum(
        prefs.edit,
        "keyframe_new_interpolation_type",
        "LINEAR",
        text="",
        icon="IPO_LINEAR",
    )
    layout.prop_enum(
        prefs.edit,
        "keyframe_new_interpolation_type",
        "BEZIER",
        text="",
        icon="IPO_BEZIER",
    )

    layout.separator()


def register():
    add_menu_draw_func(GRAPH_MT_editor_menus, draw_keyframe_interpolation_toggle)


def unregister():
    remove_menu_draw_func(GRAPH_MT_editor_menus, draw_keyframe_interpolation_toggle)
