# pyright: reportInvalidTypeForm=false
import ctypes

import bpy
from bpy.types import Operator
from bpy.props import BoolProperty

from ..keymap_manager import KeymapDefinition, keymap_registry

# graph.view_selected の垂直余白は 1.1 倍で固定（graph_view.cc）。
# RegionView2D.cur は RNA に出ていないので、表示領域の下端から位置を特定して広げる。
_VERTICAL_MARGIN_SCALE = 1.5
_VIEW2D_CUR_SPAN = 64
_view2d_cur_offset = None


def _view2d_cur(view2d):
    """view2d.cur (xmin, xmax, ymin, ymax) を指す c_float*4。位置不明なら None"""
    global _view2d_cur_offset
    base = view2d.as_pointer()
    if _view2d_cur_offset is None:
        # 表示領域の下端は cur.ymin と一致する
        _, ymin = view2d.region_to_view(0, 0)
        buf = (ctypes.c_float * _VIEW2D_CUR_SPAN).from_address(base)
        hits = [index for index in range(_VIEW2D_CUR_SPAN) if buf[index] == ymin]
        if len(hits) != 1:
            return None
        _view2d_cur_offset = (hits[0] - 2) * ctypes.sizeof(ctypes.c_float)
    try:
        return (ctypes.c_float * 4).from_address(base + _view2d_cur_offset)
    except (ValueError, ctypes.ArgumentError):
        _view2d_cur_offset = None
        return None


def widen_vertical_margin(context, scale=_VERTICAL_MARGIN_SCALE):
    """フォーカス後の表示範囲を垂直方向に広げる。範囲の中心は維持する"""
    area = context.area
    if area is None:
        return
    region = next((r for r in area.regions if r.type == "WINDOW"), None)
    if region is None:
        return
    cur = _view2d_cur(region.view2d)
    if cur is None:
        return
    center = (cur[2] + cur[3]) / 2
    half = (cur[3] - cur[2]) / 2 * scale
    cur[2] = center - half
    cur[3] = center + half
    region.tag_redraw()


class GRAPH_OT_view_selected_curves_range(Operator):
    """再生範囲内の選択中のカーブ全体を表示する"""

    bl_idname = "graph.view_selected_curves_range"
    bl_label = "View Selected Curves Range"
    bl_options = {"REGISTER", "UNDO"}

    include_handles: BoolProperty(
        name="Include Handles",
        default=True,
    )
    use_frame_range: BoolProperty(
        name="Use Frame Range",
        description="再生範囲またはプレビュー範囲内でフォーカスする",
        default=True,
    )

    @classmethod
    def poll(cls, context):
        return (
            context.space_data.type == "GRAPH_EDITOR"
            and context.selected_editable_fcurves
        )

    def execute(self, context):
        scene = context.scene
        selected_curves = context.selected_editable_fcurves

        if not selected_curves:
            self.report({"WARNING"}, "選択中のFカーブがありません")
            return {"CANCELLED"}

        # 再生範囲の取得
        if self.use_frame_range:
            if scene.use_preview_range:
                frame_start = scene.frame_preview_start
                frame_end = scene.frame_preview_end
            else:
                orig_start = scene.get("original_start")
                orig_end = scene.get("original_end")
                frame_start = int(orig_start) if orig_start is not None else scene.frame_start
                frame_end = int(orig_end) if orig_end is not None else scene.frame_end
        else:
            frame_start = float("-inf")
            frame_end = float("inf")

        # 現在の選択状態を保存
        original_selection = {}
        for curve in selected_curves:
            keyframe_states = []
            for kf in curve.keyframe_points:
                keyframe_states.append(
                    {
                        "control": kf.select_control_point,
                        "left": kf.select_left_handle,
                        "right": kf.select_right_handle,
                    }
                )
            original_selection[curve] = keyframe_states

        # 各チャンネルで選択キーが1つずつかどうかを判定
        per_channel_single = True
        for curve in selected_curves:
            selected_count = 0
            for kf in curve.keyframe_points:
                if (
                    kf.select_control_point
                    or kf.select_left_handle
                    or kf.select_right_handle
                ):
                    selected_count += 1
            if selected_count != 1:
                per_channel_single = False
                break

        # キーフレームの選択状態を変更（再生範囲内のすべてのキーフレームを選択）
        # 条件に一致したときのみ一時的に選択を変更する
        if per_channel_single:
            for curve in selected_curves:
                for keyframe in curve.keyframe_points:
                    x = keyframe.co[0]
                    in_range = frame_start <= x <= frame_end
                    keyframe.select_control_point = in_range
                    keyframe.select_left_handle = in_range
                    keyframe.select_right_handle = in_range

        # graph.view_selectedを実行してフォーカス
        bpy.ops.graph.view_selected(include_handles=self.include_handles)
        widen_vertical_margin(context)

        # 元の選択状態に戻す
        # 一時選択を行った場合のみ復元する
        if per_channel_single:
            for curve in selected_curves:
                if curve in original_selection:
                    for i, state in enumerate(original_selection[curve]):
                        if i < len(curve.keyframe_points):
                            kf = curve.keyframe_points[i]
                            kf.select_control_point = state["control"]
                            kf.select_left_handle = state["left"]
                            kf.select_right_handle = state["right"]

        return {"FINISHED"}


keymap_graph_view_selected_curves_range = [
    # フォーカス
    KeymapDefinition(
        operator_id="graph.view_selected_curves_range",
        key="F",
        value="PRESS",
        properties={"use_frame_range": True},
        name="Graph Editor",
        space_type="GRAPH_EDITOR",
        description="選択カーブ範囲にフォーカス",
    ),
    # アンフォーカス（ビルトイン）
    KeymapDefinition(
        operator_id="graph.view_all",
        key="F",
        value="PRESS",
        alt=True,
        name="Graph Editor",
        space_type="GRAPH_EDITOR",
        description="全体表示（ビルトイン）",
    ),
]


keymap_registry.register_keymap_group(
    "Focus Selected Curves", keymap_graph_view_selected_curves_range
)
