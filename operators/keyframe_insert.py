# pyright: reportInvalidTypeForm=false
from __future__ import annotations

import bpy
from bpy.props import StringProperty, BoolProperty
from bpy.types import Operator, Menu, Context

from ..utils.logging import get_logger
from ..utils.anim_utils import (
    get_timeline_remapping_ratio,
    get_action_fcurves,
    get_context_actions,
    remap_action_keyframes,
)
from ..keymap_manager import KeymapDefinition, keymap_registry

log = get_logger(__name__)


def snapshot_context_transforms(context: Context) -> dict:
    """保存当前视口中正在编辑的物体/骨骼未保存变换值"""
    data = {"objects": {}, "bones": {}}
    targets = set()
    if context.active_object:
        targets.add(context.active_object)
    if getattr(context, "selected_objects", None):
        targets.update(context.selected_objects)

    for obj in targets:
        data["objects"][obj] = (
            tuple(obj.location),
            tuple(obj.rotation_euler),
            tuple(obj.rotation_quaternion),
            tuple(obj.rotation_axis_angle),
            tuple(obj.scale),
        )
        if obj.type == "ARMATURE" and obj.pose:
            for pb in obj.pose.bones:
                data["bones"][pb] = (
                    tuple(pb.location),
                    tuple(pb.rotation_euler),
                    tuple(pb.rotation_quaternion),
                    tuple(pb.rotation_axis_angle),
                    tuple(pb.scale),
                )
    return data


def restore_context_transforms(snapshot: dict) -> None:
    """恢复保存的未保存变换值"""
    for obj, (loc, rot_e, rot_q, rot_aa, scl) in snapshot.get("objects", {}).items():
        try:
            obj.location = loc
            obj.rotation_euler = rot_e
            obj.rotation_quaternion = rot_q
            obj.rotation_axis_angle = rot_aa
            obj.scale = scl
        except Exception:
            pass

    for pb, (loc, rot_e, rot_q, rot_aa, scl) in snapshot.get("bones", {}).items():
        try:
            pb.location = loc
            pb.rotation_euler = rot_e
            pb.rotation_quaternion = rot_q
            pb.rotation_axis_angle = rot_aa
            pb.scale = scl
        except Exception:
            pass


class ANIM_OT_monkey_keyframe_insert(Operator):
    bl_idname = "anim.monkey_keyframe_insert"
    bl_label = "Insert Keyframe (Speed Aware)"
    bl_description = (
        "Insert keyframe matching actual action frame timing under playback speed remapping"
    )
    bl_options = {"UNDO", "REGISTER"}

    type: StringProperty(
        name="Keying Set",
        description="Keying set identifier or type name",
        default="",
    )
    confirm: BoolProperty(
        name="Confirm",
        description="Always prompt menu",
        default=False,
    )

    @classmethod
    def poll(cls, context: Context) -> bool:
        return bool(context.active_object or getattr(context, "selected_objects", None))

    def invoke(self, context: Context, event):
        if self.type and not self.confirm:
            return self.execute(context)

        # アクティブなキーイングセットが設定されている場合は直接実行
        active_ks = getattr(getattr(context.scene, "keying_sets_all", None), "active", None)
        if active_ks and not self.confirm:
            return self.execute(context)

        return bpy.ops.wm.call_menu(name="ANIM_MT_monkey_keyframe_insert_menu")

    def execute(self, context: Context):
        scene = context.scene
        ratio = get_timeline_remapping_ratio(scene)
        cur_frame = scene.frame_current

        # 1. 速度変化がない通常時 (ratio == 1.0)
        if abs(ratio - 1.0) < 1e-4:
            if self.type:
                try:
                    bpy.ops.anim.keyframe_insert_by_name(type=self.type)
                except Exception as e:
                    log.warning(f"keyframe_insert_by_name failed: {e}")
                    bpy.ops.anim.keyframe_insert()
            else:
                active_ks = getattr(
                    getattr(scene, "keying_sets_all", None), "active", None
                )
                if active_ks:
                    bpy.ops.anim.keyframe_insert()
                else:
                    bpy.ops.anim.keyframe_insert_by_name(type="Available")
            return {"FINISHED"}

        # 2. 速度変化中 (ratio != 1.0)
        # 任意速度（0.5x, 2.0x, 0.25x 等）で重なり合っても既存キーフレームを壊さないよう、
        # 视口变换值を退避した上で直接实际帧(actual_frame)へ原生插帧。
        raw_cur = cur_frame / ratio
        actual_frame = int(round(raw_cur))
        aligned_timeline_frame = int(round(actual_frame * ratio))

        # A. 保存当前未插帧的视口变换状态
        snapshot = snapshot_context_transforms(context)

        # B. 临时关闭时间重映射，跳转到动作的真实帧 (actual_frame)
        orig_map_old = scene.render.frame_map_old
        orig_map_new = scene.render.frame_map_new
        scene.render.frame_map_old = 100
        scene.render.frame_map_new = 100

        try:
            scene.frame_set(actual_frame)

            # C. 恢复变换数据到真实帧上
            restore_context_transforms(snapshot)

            # D. 直接在真实帧上执行原生插帧（绝不会触碰或覆盖 cur_frame 上的其他关键帧！）
            if self.type:
                try:
                    bpy.ops.anim.keyframe_insert_by_name(type=self.type)
                except Exception as e:
                    log.warning(f"keyframe_insert_by_name failed: {e}")
                    bpy.ops.anim.keyframe_insert()
            else:
                active_ks = getattr(
                    getattr(scene, "keying_sets_all", None), "active", None
                )
                if active_ks:
                    bpy.ops.anim.keyframe_insert()
                else:
                    bpy.ops.anim.keyframe_insert_by_name(type="Available")
        finally:
            # E. 恢复时间重映射并定位播放头至对齐的重映射时间帧
            scene.render.frame_map_old = orig_map_old
            scene.render.frame_map_new = orig_map_new
            scene.frame_set(aligned_timeline_frame)

        self.report(
            {"INFO"},
            f"Keyframe set to actual frame {actual_frame} (timeline {aligned_timeline_frame})",
        )
        return {"FINISHED"}


class ANIM_OT_monkey_snap_keyframes_to_speed(Operator):
    bl_idname = "anim.monkey_snap_keyframes_to_speed"
    bl_label = "Remap Keyframes to Actual Timing"
    bl_description = (
        "Remap retimed keyframes in the active action back to original integer frame timing"
    )
    bl_options = {"UNDO", "REGISTER"}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return bool(
            context.active_object and getattr(context.active_object, "animation_data", None)
        )

    def execute(self, context: Context):
        scene = context.scene
        ratio = get_timeline_remapping_ratio(scene)
        if abs(ratio - 1.0) < 1e-4:
            self.report({"INFO"}, "Playback speed is 1.0x (no remapping needed)")
            return {"FINISHED"}

        orig_start = scene.get("original_start")
        orig_end = scene.get("original_end")
        if orig_start is None or orig_end is None:
            self.report({"WARNING"}, "Original frame range is not stored")
            return {"CANCELLED"}

        actions = get_context_actions(context)
        total = 0
        for act in actions:
            fcurves = get_action_fcurves(act)
            for fc in fcurves:
                points_to_remap = []
                for p in fc.keyframe_points:
                    raw = p.co[0] / ratio
                    if abs(raw - round(raw)) < 1e-4:
                        actual = int(round(raw))
                        if orig_start <= actual <= orig_end and p.co[0] > orig_end:
                            points_to_remap.append((p.co[0], actual))
                for src_f, tgt_f in points_to_remap:
                    remap_action_keyframes(act, src_f, float(tgt_f))
                    total += 1

        self.report({"INFO"}, f"Remapped {total} keyframe points to actual frames")
        return {"FINISHED"}


class ANIM_MT_monkey_keyframe_insert_menu(Menu):
    bl_idname = "ANIM_MT_monkey_keyframe_insert_menu"
    bl_label = "Insert Keyframe (Speed Aware)"

    def draw(self, context: Context):
        layout = self.layout

        layout.operator(
            "anim.monkey_keyframe_insert", text="Available", icon="KEY_HLT"
        ).type = "Available"
        layout.separator()

        layout.operator(
            "anim.monkey_keyframe_insert", text="Location & Rotation"
        ).type = "BUILTIN_KSI_LocRot"
        layout.operator(
            "anim.monkey_keyframe_insert", text="Location, Rotation & Scale"
        ).type = "LocRotScale"
        layout.separator()

        layout.operator(
            "anim.monkey_keyframe_insert", text="Location"
        ).type = "Location"
        layout.operator(
            "anim.monkey_keyframe_insert", text="Rotation"
        ).type = "Rotation"
        layout.operator(
            "anim.monkey_keyframe_insert", text="Scale"
        ).type = "Scaling"

        if context.mode == "POSE":
            layout.separator()
            layout.operator(
                "anim.monkey_keyframe_insert",
                text="Whole Character (Selected Bones Only)",
            ).type = "WholeCharacterSelected"


class ANIM_MT_monkey_keyframe_insert_pie(Menu):
    bl_idname = "ANIM_MT_monkey_keyframe_insert_pie"
    bl_label = "Insert Keyframe (Speed Aware)"

    def draw(self, _context: Context):
        layout = self.layout
        pie = layout.menu_pie()

        # West: Location
        pie.operator(
            "anim.monkey_keyframe_insert", text="Location"
        ).type = "Location"
        # East: Rotation
        pie.operator(
            "anim.monkey_keyframe_insert", text="Rotation"
        ).type = "Rotation"
        # South: Scale
        pie.operator(
            "anim.monkey_keyframe_insert", text="Scale"
        ).type = "Scaling"
        # North: Available
        pie.operator(
            "anim.monkey_keyframe_insert", text="Available", icon="KEY_HLT"
        ).type = "Available"
        # North-West: Location & Rotation
        pie.operator(
            "anim.monkey_keyframe_insert", text="LocRot"
        ).type = "BUILTIN_KSI_LocRot"
        # North-East: Location, Rotation & Scale
        pie.operator(
            "anim.monkey_keyframe_insert", text="LocRotScale"
        ).type = "LocRotScale"


KEYFRAME_INSERT_KEYMAPS = [
    ("Pose", "EMPTY"),
    ("Object Mode", "EMPTY"),
    ("3D View", "VIEW_3D"),
    ("Dopesheet", "DOPESHEET_EDITOR"),
    ("Graph Editor", "GRAPH_EDITOR"),
]

keymap_definitions = []
for keymap_name, keymap_space_type in KEYFRAME_INSERT_KEYMAPS:
    keymap_definitions.append(
        KeymapDefinition(
            operator_id="anim.monkey_keyframe_insert",
            key="I",
            value="PRESS",
            name=keymap_name,
            space_type=keymap_space_type,
            description="Insert keyframe (speed-aware retiming)",
        )
    )

keymap_registry.register_keymap_group("Keyframe Insert", keymap_definitions)


# ==========================================================
# 撤销/重做时保持当前播放头帧位（防止被快照卷回跳转前的帧）
# ==========================================================

_last_frame_before_undo: int | None = None


def on_undo_pre(scene):
    global _last_frame_before_undo
    _last_frame_before_undo = getattr(scene, "frame_current", None)


def on_undo_post(scene):
    global _last_frame_before_undo
    if _last_frame_before_undo is not None:
        target = _last_frame_before_undo
        _last_frame_before_undo = None
        if getattr(scene, "frame_current", None) != target:
            scene.frame_set(target)


def register():
    if on_undo_pre not in bpy.app.handlers.undo_pre:
        bpy.app.handlers.undo_pre.append(on_undo_pre)
    if on_undo_post not in bpy.app.handlers.undo_post:
        bpy.app.handlers.undo_post.append(on_undo_post)
    if on_undo_pre not in bpy.app.handlers.redo_pre:
        bpy.app.handlers.redo_pre.append(on_undo_pre)
    if on_undo_post not in bpy.app.handlers.redo_post:
        bpy.app.handlers.redo_post.append(on_undo_post)


def unregister():
    if on_undo_pre in bpy.app.handlers.undo_pre:
        bpy.app.handlers.undo_pre.remove(on_undo_pre)
    if on_undo_post in bpy.app.handlers.undo_post:
        bpy.app.handlers.undo_post.remove(on_undo_post)
    if on_undo_pre in bpy.app.handlers.redo_pre:
        bpy.app.handlers.redo_pre.remove(on_undo_pre)
    if on_undo_post in bpy.app.handlers.redo_post:
        bpy.app.handlers.redo_post.remove(on_undo_post)
