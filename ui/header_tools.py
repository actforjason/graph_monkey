# pyright: reportInvalidTypeForm=false
"""
ヘッダーツール表示設定。

Graph Editor / Dope Sheet / その他のタイムエディターのヘッダーに
アドオンが追加するツールの表示・非表示を切り替える。

主な機能:
- Graph Editor: Action管理・スロット、補間タイプ、表示範囲同期
- Dope Sheet: 再生速度コントローラー、再生プレビュー、表示範囲同期
- その他: NLA / Sequencer / Timeline の表示範囲同期

使用例: ヘッダーが混み合う場合に、不要なツールだけ非表示にする
"""

import bpy
from bpy.props import BoolProperty
from bpy.types import PropertyGroup

from ..addon import get_prefs
from ..utils.i18n import _
from ..utils.ui_utils import ic


def redraw_all_windows():
    """全ウィンドウの全エリアを再描画する（設定変更をヘッダーへ即時反映）"""
    window_manager = getattr(bpy.context, "window_manager", None)
    if not window_manager:
        return

    for window in window_manager.windows:
        screen = getattr(window, "screen", None)
        if not screen:
            continue
        for area in screen.areas:
            area.tag_redraw()
            for region in area.regions:
                region.tag_redraw()


def _on_setting_update(self, context):
    redraw_all_windows()


def get_header_tools(context=None):
    """
    アドオン設定の HeaderToolsSettings を取得。

    Args:
        context: Blenderコンテキスト（省略時は bpy.context）

    Returns:
        HeaderToolsSettings | None: 取得できない場合は None
    """
    try:
        return get_prefs(context if context is not None else bpy.context).header_tools
    except Exception:
        return None


def is_header_tool_visible(context, setting_name: str) -> bool:
    """
    指定されたヘッダーツールが表示有効か判定する。

    設定を取得できない場合（アドオン無効化中など）は表示扱いにする。

    Args:
        context: Blenderコンテキスト
        setting_name: HeaderToolsSettings のプロパティ名

    Returns:
        bool: 表示する場合 True
    """
    tools = get_header_tools(context)
    if tools is None:
        return True
    return getattr(tools, setting_name, True)


def get_playback_speed_visible(context) -> bool:
    """
    再生速度コントローラーの表示設定を取得。

    Blender は設定をプロパティ名で保存するため、旧名
    show_dopesheet_playback_speed の値は新名へ自動では移らない。
    旧名だけが保存されている（= 読み込み後に新名が未変更の）場合は
    初回参照時に旧名の値を引き継ぐ。
    """
    tools = get_header_tools(context)
    if tools is None:
        return True
    legacy = tools.show_dopesheet_playback_speed
    if legacy != tools.show_playback_speed:
        tools.show_playback_speed = legacy
        tools.show_dopesheet_playback_speed = legacy
    return tools.show_playback_speed


class HeaderToolsSettings(PropertyGroup):
    """ヘッダーツールの表示切り替え設定"""

    # === Graph Editor ===
    show_graph_action: BoolProperty(
        name="Action Management & Slots",
        description="Show Action management and slots in Graph Editor header",
        default=True,
        update=_on_setting_update,
    )
    show_graph_interpolation: BoolProperty(
        name="Keyframe Interpolation Type",
        description="Show new keyframe interpolation type buttons in Graph Editor header",
        default=True,
        update=_on_setting_update,
    )
    show_graph_sync_visible_range: BoolProperty(
        name="Sync Visible Range",
        description="Show view synchronization toggle in Graph Editor header",
        default=True,
        update=_on_setting_update,
    )

    # === Playback Controls (footer) ===
    show_playback_speed: BoolProperty(
        name="Playback Speed Controller",
        description="Show playback speed controls in the playback controls footer",
        default=True,
        update=_on_setting_update,
    )

    # === Dope Sheet ===
    show_dopesheet_playback_preview: BoolProperty(
        name="Playback Viewport Preview",
        description="Show clean playback preview toggle in Dope Sheet header",
        default=True,
        update=_on_setting_update,
    )
    show_dopesheet_sync_visible_range: BoolProperty(
        name="Sync Visible Range",
        description="Show view synchronization toggle in Dope Sheet header",
        default=True,
        update=_on_setting_update,
    )

    # 旧名。既存設定の値を引き継ぐためだけに残す
    show_dopesheet_playback_speed: BoolProperty(
        name="Playback Speed Controller (Legacy)",
        description="Deprecated alias of show_playback_speed",
        default=True,
        update=_on_setting_update,
    )

    # === Other time-based editors ===
    show_other_sync_visible_range: BoolProperty(
        name="Sync Visible Range",
        description="Show view synchronization toggle in NLA, Sequencer and Timeline headers",
        default=True,
        update=_on_setting_update,
    )

    def draw(self, context, layout):
        # Graph Editor
        col = layout.column(align=True)
        col.label(text=_("HEADER_TOOLS_GRAPH"), icon=ic("GRAPH"))
        box = col.box()
        box.prop(self, "show_graph_action", text=_("HEADER_TOOLS_ACTION"))
        box.prop(self, "show_graph_interpolation", text=_("HEADER_TOOLS_INTERPOLATION"))
        box.prop(
            self, "show_graph_sync_visible_range", text=_("HEADER_TOOLS_SYNC_RANGE")
        )

        # Playback Controls（Dope Sheet / Graph Editor / NLA / Sequencer / Timeline 共通フッター）
        col = layout.column(align=True)
        col.label(text=_("HEADER_TOOLS_PLAYBACK_CONTROLS"), icon=ic("PLAY"))
        box = col.box()
        box.prop(self, "show_playback_speed", text=_("HEADER_TOOLS_PLAYBACK_SPEED"))

        # Dope Sheet
        col = layout.column(align=True)
        col.label(text=_("HEADER_TOOLS_DOPESHEET"), icon=ic("ACTION"))
        box = col.box()
        box.prop(
            self, "show_dopesheet_playback_preview", text=_("HEADER_TOOLS_PLAYBACK_PREVIEW")
        )
        box.prop(
            self, "show_dopesheet_sync_visible_range", text=_("HEADER_TOOLS_SYNC_RANGE")
        )

        # Other editors
        col = layout.column(align=True)
        col.label(text=_("HEADER_TOOLS_OTHER"), icon=ic("TIME"))
        box = col.box()
        box.prop(
            self, "show_other_sync_visible_range", text=_("HEADER_TOOLS_SYNC_RANGE")
        )
