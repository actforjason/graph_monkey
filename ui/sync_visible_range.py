"""
タイムベースエディターのヘッダーに表示範囲同期トグルを追加。

主な機能:
- Dope Sheet / Graph Editor / NLA / Sequencer / Timeline 間で表示範囲を同期
- エディター種別ごとに表示・非表示を切り替え可能（HeaderToolsSettings）

使用例: 長いアニメーションで複数エディターの表示範囲を揃えたい時
"""

import bpy
from bpy.app import version as BL_VERSION
from bpy.types import (
    DOPESHEET_MT_editor_menus,
    GRAPH_MT_editor_menus,
    NLA_MT_editor_menus,
    SEQUENCER_MT_editor_menus,
)

from ..utils.logging import get_logger
from ..utils.menu_utils import add_menu_draw_func, remove_menu_draw_func
from ..utils.ui_utils import ic
from .header_tools import is_header_tool_visible

log = get_logger(__name__)

# TODO: チャンネル・Nパネルの同期対応
# C.space_data.show_region_channels
# C.space_data.show_region_ui


def draw_sync_visible_range(self, context):
    if not (context.space_data and hasattr(context.space_data, "show_locked_time")):
        return

    space_type = context.space_data.type
    if space_type == "GRAPH_EDITOR":
        setting_name = "show_graph_sync_visible_range"
    elif space_type == "DOPESHEET_EDITOR":
        setting_name = "show_dopesheet_sync_visible_range"
    else:
        setting_name = "show_other_sync_visible_range"

    if not is_header_tool_visible(context, setting_name):
        return

    layout = self.layout

    sd = context.space_data
    lock_icon = "LOCKVIEW_ON" if sd.show_locked_time else "LOCKVIEW_OFF"

    layout.prop(sd, "show_locked_time", text="", icon=ic(lock_icon))
    layout.separator()


TIME_BASED_EDITOR_MENUS = [
    DOPESHEET_MT_editor_menus,
    GRAPH_MT_editor_menus,
    NLA_MT_editor_menus,
    SEQUENCER_MT_editor_menus,
]


def _get_legacy_time_menu():
    """Blender 5.0 未満の統合タイムラインメニューを取得（存在しなければ None）"""
    if BL_VERSION >= (5, 0, 0):
        return None
    return getattr(bpy.types, "TIME_MT_editor_menus", None)


def register():
    try:
        for menu in TIME_BASED_EDITOR_MENUS:
            add_menu_draw_func(menu, draw_sync_visible_range, prepend=True)
        time_menu = _get_legacy_time_menu()
        if time_menu is not None:
            add_menu_draw_func(time_menu, draw_sync_visible_range)
        log.debug("Sync visible range menus registered successfully")
    except Exception as e:
        log.error(f"Failed to register sync visible range menus: {e}")


def unregister():
    try:
        menus = list(TIME_BASED_EDITOR_MENUS)
        time_menu = getattr(bpy.types, "TIME_MT_editor_menus", None)
        if time_menu is not None:
            menus.append(time_menu)
        for menu in menus:
            remove_menu_draw_func(menu, draw_sync_visible_range)
        log.debug("Sync visible range menus unregistered successfully")
    except Exception as e:
        log.debug(f"Failed to unregister sync visible range menus: {e}")
