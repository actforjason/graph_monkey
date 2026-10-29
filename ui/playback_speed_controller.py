# pyright: reportInvalidTypeForm=false
# bl_info = {
#     "name": "Playback Speed Controller",
#     "blender": (2, 80, 0),
#     "category": "Animation",
#     "version": (1, 1, 0),
#     "author": "Pluglug",
#     "description": "Control the playback speed of the animation",
# }

# Control the playback speed of the animation

import bpy
import sys

import bpy.app.handlers as handlers
from bpy.props import FloatProperty
from bpy.types import Operator, Panel, Scene

from ..utils.ui_utils import ic
from .header_tools import get_playback_preview_visible, get_playback_speed_visible
from .playback_preview import draw_playback_preview


DEFAULT_SPEED = 1.0
FRAME_MAP_BASE = 100
FRAME_MAP_MIN = 1
FRAME_MAP_MAX = 900
SPEED_TOLERANCE = 0.01

preset_items = [
    ("0.25", "¼x", ""),
    ("0.5", "½x", ""),
    ("1.0", "1x", ""),
    ("2.0", "2x", ""),
]


# フッター右側（出力 / スナップ / フレーム範囲など）の左にも空きを入れ、
# 中央の再生ボタン列の真ん中あたりに来るよう左右から寄せる
class _CenteredLayoutProxy:
    def __init__(self, layout):
        self._layout = layout
        self._right_done = False

    def __getattr__(self, name):
        return getattr(self._layout, name)

    def row(self, *args, **kwargs):
        # 右側ブロックはスナップ popover の row から始まる
        if (
            kwargs.get("panel") == "TIME_PT_playhead_snapping"
            and not self._right_done
        ):
            self._right_done = True
            self._layout.separator_spacer()
        return self._layout.row(*args, **kwargs)


class PlaybackController:
    _instance = None
    _current_scene = None

    def __new__(cls, scene):
        if cls._instance is None or cls._current_scene != scene:
            cls._instance = super().__new__(cls)
            cls._current_scene = scene
        return cls._instance

    def __init__(self, scene):
        if (
            hasattr(self, "_initialized")
            and getattr(self, "_initialized", False)
            and getattr(self, "scene", None) == scene
        ):
            return

        self.scene = scene
        self._initialized = True

    def store_original_range(self):
        if (
            not hasattr(self.scene, "playback_speed")
            or abs(self.scene.playback_speed - DEFAULT_SPEED) > SPEED_TOLERANCE
        ):
            return

        self.scene["original_start"] = self.scene.frame_start
        self.scene["original_end"] = self.scene.frame_end

    def adjust_range(self, frame_map_old, frame_map_new):
        # original値が存在しない場合は範囲調整をスキップ
        original_start = self.scene.get("original_start")
        original_end = self.scene.get("original_end")

        if original_start is None or original_end is None:
            print("警告: オリジナル範囲が未保存のため、フレーム範囲調整をスキップ")
            return

        ratio = frame_map_new / frame_map_old
        new_start = round(original_start * ratio)
        new_end = round(original_end * ratio)

        self.scene.frame_start = new_start
        self.scene.frame_end = new_end

    def has_valid_original_range(self):
        """オリジナル範囲が適切に保存されているかチェック"""
        original_start = self.scene.get("original_start")
        original_end = self.scene.get("original_end")
        return original_start is not None and original_end is not None

    def is_range_modified(self):
        """現在の範囲がオリジナルから変更されているかチェック"""
        if not self.has_valid_original_range():
            return False

        original_start = self.scene.get("original_start")
        original_end = self.scene.get("original_end")

        start_changed = abs(int(original_start) - self.scene.frame_start) > 0
        end_changed = abs(int(original_end) - self.scene.frame_end) > 0

        return start_changed or end_changed

    def apply_speed(self, playback_speed):
        playback_speed = round(playback_speed, 2)
        frame_map_old = round(playback_speed * FRAME_MAP_BASE)
        frame_map_old = max(FRAME_MAP_MIN, min(FRAME_MAP_MAX, frame_map_old))

        self.scene.render.frame_map_old = frame_map_old
        self.scene.render.frame_map_new = FRAME_MAP_BASE

        self.adjust_range(frame_map_old, self.scene.render.frame_map_new)

    @classmethod
    def get_instance(cls, scene):
        return cls(scene)


# ===== オペレーター =====


class SCENE_OT_store_original_range(Operator):
    bl_idname = "scene.store_original_range"
    bl_label = "Store Original Playback Range"
    bl_description = (
        "Store the original playback range before applying playback speed adjustments"
    )
    bl_options = {"INTERNAL", "UNDO"}

    def execute(self, context):
        controller = PlaybackController.get_instance(context.scene)

        if not hasattr(context.scene, "playback_speed"):
            self.report({"ERROR"}, "Playback speed is not set")
            return {"CANCELLED"}

        # 速度変化中の保存を防ぐ安全策
        if abs(context.scene.playback_speed - DEFAULT_SPEED) > SPEED_TOLERANCE:
            self.report(
                {"WARNING"},
                f"速度変化中（{context.scene.playback_speed:.2f}x）はオリジナル範囲保存不可。"
                "まず速度を1.0xにリセットしてください。",
            )
            return {"CANCELLED"}

        controller.store_original_range()
        # context.scene.playback_speed = 1.0
        return {"FINISHED"}


class SCENE_OT_reset_speed(Operator):
    bl_idname = "scene.reset_speed"
    bl_label = "Reset Playback Speed"
    bl_description = "Reset playback speed and return to original playback range"
    bl_options = {"INTERNAL", "UNDO"}

    def execute(self, context):
        context.scene.playback_speed = 1.0
        return {"FINISHED"}


class SCENE_OT_set_playback_speed_preset(Operator):
    bl_idname = "scene.set_playback_speed_preset"
    bl_label = "Set Playback Speed Preset"
    bl_description = "Set playback speed to preset value"
    bl_options = {"INTERNAL", "UNDO"}

    speed: FloatProperty(
        name="Speed",
        description="Playback speed value",
        default=1.0,
    )

    def execute(self, context):
        context.scene.playback_speed = self.speed
        return {"FINISHED"}


# ===== UI ユーティリティ =====


class PlaybackSpeedUI:
    """再生速度コントロールのUI管理クラス"""

    @staticmethod
    def get_store_button_state(scene):
        """ストアボタンの状態を取得"""
        # original値の存在確認
        original_start = scene.get("original_start")
        original_end = scene.get("original_end")

        # 現在の速度状態をチェック
        is_speed_normal = abs(scene.playback_speed - DEFAULT_SPEED) <= SPEED_TOLERANCE

        # 速度変化中の場合
        if not is_speed_normal:
            if original_start is not None and original_end is not None:
                # オリジナル保存済み + 速度変化中 = 正常利用中（青・無効）
                return "using", True  # (state, enabled)
            else:
                # オリジナル未保存 + 速度変化中 = 警告（赤・無効）
                return "warning", False

        # 速度が通常時（1.0x）の場合
        if original_start is None or original_end is None:
            # 未保存（赤・有効）
            return "need_save", True

        # 現在の範囲とoriginal範囲を比較
        current_start = scene.frame_start
        current_end = scene.frame_end

        start_changed = abs(int(original_start) - current_start) > 0
        end_changed = abs(int(original_end) - current_end) > 0

        if start_changed or end_changed:
            # 変更あり（赤・有効）
            return "need_update", True
        else:
            # 保存済み・変更なし（緑・有効）
            return "saved", True

    @staticmethod
    def get_store_button_icon(button_state):
        """ストアボタンのアイコンを取得"""
        icon_map = {
            "using": ic("SEQUENCE_COLOR_05"),  # Blue - オリジナル範囲利用中
            "warning": ic("SEQUENCE_COLOR_01"),  # Red - 速度変化中だが未保存
            "need_save": ic("SEQUENCE_COLOR_01"),  # Red - 保存が必要
            "need_update": ic("SEQUENCE_COLOR_01"),  # Red - 更新が必要
            "saved": ic("SEQUENCE_COLOR_04"),  # Green - 保存済み・問題なし
        }
        return icon_map.get(button_state, ic("SEQUENCE_COLOR_01"))

    @staticmethod
    def get_reset_button_icon(scene):
        """リセットボタンのアイコンを取得"""
        if scene.playback_speed != 1.00:
            return ic("CANCEL")
        else:
            return ic("PLAY")

    @staticmethod
    def should_block_speed_change(button_state):
        """速度変更をブロックすべきかチェック"""
        return button_state in ["need_save", "need_update"]


# ===== UIレイアウト =====


def draw_speed_slider(layout, scene, enabled=True):
    """速度スライダーを描画"""
    col = layout.column(align=True)
    col.enabled = enabled
    col.prop(scene, "playback_speed", text="", icon=ic("MOD_TIME"))


def draw_preset_buttons(layout, scene, enabled=True):
    """プリセットボタンを描画"""
    col = layout.column(align=True)
    col.enabled = enabled
    col.scale_x = 0.5

    preset_row = col.row(align=True)
    for speed_value, speed_label, _ in preset_items:
        op = preset_row.operator("scene.set_playback_speed_preset", text=speed_label)
        op.speed = float(speed_value)


def draw_control_buttons(layout, scene):
    """制御ボタン（ストア・リセット）を描画"""
    col = layout.column(align=True)
    control_row = col.row(align=True)

    # ストアボタンの状態取得
    button_state, button_enabled = PlaybackSpeedUI.get_store_button_state(scene)
    store_icon = PlaybackSpeedUI.get_store_button_icon(button_state)

    # ストアボタン
    control_row.operator("scene.store_original_range", text="", icon=store_icon)

    # リセットボタン
    reset_icon = PlaybackSpeedUI.get_reset_button_icon(scene)
    control_row.operator("scene.reset_speed", text="", icon=reset_icon)


def draw_ui(self, context):
    """メインのUI描画関数（Header の draw からも、layout を渡す形でも使う）"""
    show_speed = get_playback_speed_visible(context)
    show_preview = get_playback_preview_visible(context)

    if not show_speed and not show_preview:
        return

    # Graph Editor の Drivers モードはフッターがドライバー情報欄になるので出さない
    if getattr(getattr(context, "space_data", None), "mode", None) == "DRIVERS":
        return

    scene = context.scene
    layout = getattr(self, "layout", self)

    row = layout.row(align=True)

    if show_speed:
        # ボタンの状態をチェック
        button_state, _ = PlaybackSpeedUI.get_store_button_state(scene)
        speed_change_blocked = PlaybackSpeedUI.should_block_speed_change(button_state)

        # 速度スライダー
        draw_speed_slider(row, scene, enabled=not speed_change_blocked)

        # プリセットボタン
        draw_preset_buttons(row, scene, enabled=not speed_change_blocked)

        # セパレーター
        row.separator()

        # 制御ボタン
        draw_control_buttons(row, scene)

    if show_preview:
        if show_speed:
            row.separator()
        draw_playback_preview(row, context)


# ===== イベントハンドラー =====


def on_speed_update(scene, context):
    """速度更新時のコールバック"""
    controller = PlaybackController.get_instance(scene)
    controller.apply_speed(scene.playback_speed)


def store_range_on_load(dummy):
    """ファイル読み込み時にオリジナル範囲を保存"""
    controller = PlaybackController.get_instance(bpy.context.scene)
    controller.store_original_range()
    controller.apply_speed(bpy.context.scene.playback_speed)


# bl_ui.space_time.playback_controls は F-Curve エディター系ヘッダーの共通描画関数。
# 先頭に prepend するとヘッダー左端に出てしまうので、Playback ポップオーバーの直後に差し込む。
_ORIGINAL_PLAYBACK_FUNCS = {}  # モジュール名 -> 元の playback_controls
_PATCHED_MODULES = []  # 差し替え済みモジュール名


def _find_playback_controls_modules():
    """playback_controls を呼んでいる bl_ui モジュールを返す"""
    modules = []
    for name, mod in list(sys.modules.items()):
        if name.startswith("bl_ui.") and callable(getattr(mod, "playback_controls", None)):
            modules.append(mod)
    return modules


def _unwrap_playback_controls(func):
    """既存の patched_playback_controls ラッパーを剥がして元関数を取り出す"""
    while getattr(func, "_monkey_playback_patch", False):
        raw = getattr(func, "_monkey_raw_func", None)
        if raw is None or raw is func:
            break
        func = raw
    return func


def _insert_after_playback_popover(module, draw_func):
    """
    bl_ui.space_time.playback_controls を包み、Playback ポップオーバーの直後に
    draw_func を描画する。module 側は同名関数を再エクスポートしているだけなので
    各モジュールの参照も差し替える。何度呼んでも元実装は 1 回しか保持しない。
    """
    module_name = getattr(module, "__name__", "")
    raw_func = _unwrap_playback_controls(module.playback_controls)
    _ORIGINAL_PLAYBACK_FUNCS[module_name] = raw_func

    def patched_playback_controls(layout, context, _orig=raw_func):
        _orig(_CenteredLayoutProxy(_LayoutProxy(layout, draw_func, context)), context)

    patched_playback_controls._monkey_playback_patch = True
    patched_playback_controls._monkey_raw_func = raw_func

    module.playback_controls = patched_playback_controls
    if module_name not in _PATCHED_MODULES:
        _PATCHED_MODULES.append(module_name)


class _LayoutProxy:
    """Playback ポップオーバーの直後に draw_func を描くための layout プロキシ"""

    def __init__(self, layout, draw_func, context):
        self._layout = layout
        self._draw_func = draw_func
        self._context = context
        self._after_playback = False

    def __getattr__(self, name):
        return getattr(self._layout, name)

    def popover(self, *args, **kwargs):
        result = self._layout.popover(*args, **kwargs)
        panel = kwargs.get("panel", args[0] if args else None)
        if panel == "TIME_PT_playback":
            self._after_playback = True
        return result

    def _draw_once(self):
        if not self._after_playback:
            return
        self._after_playback = False
        self._layout.separator_spacer()
        self._draw_func(self._layout, self._context)

    def row(self, *args, **kwargs):
        # popover 直後に来る最初の row() のタイミングで描く
        self._draw_once()
        return self._layout.row(*args, **kwargs)

    def separator_spacer(self):
        self._draw_once()
        return self._layout.separator_spacer()


def register():
    Scene.playback_speed = FloatProperty(
        name="Playback Speed",
        description="Control the playback speed of the animation",
        default=1.0,
        min=0.01,
        max=9.0,
        soft_min=0.1,
        soft_max=2.0,
        step=10,
        precision=2,
        update=on_speed_update,
        subtype="FACTOR",
    )

    # 未ロードの bl_ui モジュールは対象外。失敗しても他の機能は止めない
    for module in _find_playback_controls_modules():
        _insert_after_playback_popover(module, draw_ui)
    handlers.load_post.append(store_range_on_load)


def unregister():
    if hasattr(Scene, "playback_speed"):
        try:
            bpy.context.scene.playback_speed = 1.0
        except Exception:
            pass

    for name in _PATCHED_MODULES:
        module = sys.modules.get(name)
        if module is not None and hasattr(module, "playback_controls"):
            module.playback_controls = _unwrap_playback_controls(module.playback_controls)
    _PATCHED_MODULES.clear()
    _ORIGINAL_PLAYBACK_FUNCS.clear()

    if store_range_on_load in handlers.load_post:
        handlers.load_post.remove(store_range_on_load)

    if hasattr(Scene, "playback_speed"):
        del Scene.playback_speed
