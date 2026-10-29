# pyright: reportInvalidTypeForm=false
from __future__ import annotations

from typing import Any, List, Set, Tuple, Optional
from time import perf_counter
from collections import deque
from bpy.types import Context, Area


def find_timeline_area(context: Context) -> Area | None:
    """Return an animation area suitable for timeline-like operations.

    Blender 5.0 以降は専用のタイムライン領域が廃止され、再生コントロールは
    Dope Sheet のヘッダーに統合されたため、まず Dope Sheet を優先して返す。
    互換目的で旧 TIMELINE もフォールバックとして探す。
    """
    # 1) Prefer Dope Sheet editor in 5.x+
    for area in context.window.screen.areas:
        if getattr(area, "type", None) == "DOPESHEET_EDITOR":
            return area
    # 2) Fallback: legacy Timeline (pre-5.0)
    for area in context.window.screen.areas:
        if (
            getattr(area, "ui_type", None) == "TIMELINE"
            or getattr(area, "type", None) == "TIMELINE"
        ):
            return area
    return None


def _collect_visible_frames_from_context(
    context: Context,
    start_frame: int,
    end_frame: int,
    allowed_types: Set[str],
) -> Set[int]:
    frames: Set[int] = set()
    visible_fcurves = getattr(context, "visible_fcurves", None)
    if not visible_fcurves:
        return frames
    for fcurve in visible_fcurves:
        for kp in fcurve.keyframe_points:
            if not allowed_types or getattr(kp, "type", None) in allowed_types:
                frame_int = int(round(kp.co.x))
                if start_frame <= frame_int <= end_frame:
                    frames.add(frame_int)
    return frames


def collect_allowed_frames_in_range(
    context: Context,
    start_frame: int,
    end_frame: int,
    allowed_types: Set[str],
) -> List[int]:
    """
    可視Fカーブから許可タイプのフレームを抽出し、昇順のユニークリストを返す。
    1) 現在コンテキスト → 2) タイムライン → 3) 他のアニメーションエリア
    """
    frames: Set[int] = set()

    # 1) 現在のコンテキスト
    frames |= _collect_visible_frames_from_context(
        context, start_frame, end_frame, allowed_types
    )

    # 2) タイムライン
    if not frames:
        timeline_area = find_timeline_area(context)
        if timeline_area:
            with context.temp_override(area=timeline_area):
                frames |= _collect_visible_frames_from_context(
                    context, start_frame, end_frame, allowed_types
                )

    # 3) 他のアニメーションエリア
    if not frames:
        animation_areas = ["DOPESHEET_EDITOR", "GRAPH_EDITOR", "NLA_EDITOR"]
        for area_type in animation_areas:
            for area in context.window.screen.areas:
                if area.type == area_type:
                    with context.temp_override(area=area):
                        frames |= _collect_visible_frames_from_context(
                            context, start_frame, end_frame, allowed_types
                        )
                        if frames:
                            break
            if frames:
                break

    return sorted(frames)


def select_target_frame_from_list(
    frames: List[int], current: int, go_next: bool, allow_loop: bool
) -> int | None:
    if not frames:
        return None
    if go_next:
        for f in frames:
            if f > current:
                return f
        return frames[0] if allow_loop else None
    else:
        for f in reversed(frames):
            if f < current:
                return f
        return frames[-1] if allow_loop else None


# ===========================================
# Small TTL Cache for allowed frames
# ===========================================

_FRAMES_CACHE_CAPACITY = 4
_frames_cache: deque[
    Tuple[Tuple[int, int, Tuple[str, ...], int, int], float, List[int]]
] = deque(maxlen=_FRAMES_CACHE_CAPACITY)


def _make_cache_key(
    context: Context, start_frame: int, end_frame: int, allowed_types: Set[str]
) -> Tuple[int, int, Tuple[str, ...], int, int]:
    screen_ptr = getattr(getattr(context, "window", None), "screen", None)
    try:
        screen_id = int(screen_ptr.as_pointer()) if screen_ptr else 0
    except Exception:
        screen_id = id(screen_ptr) if screen_ptr else 0
    window_obj = getattr(context, "window", None)
    try:
        window_id = int(window_obj.as_pointer()) if window_obj else 0
    except Exception:
        window_id = id(window_obj) if window_obj else 0
    types_tuple = tuple(sorted(str(t).upper() for t in allowed_types))
    return (window_id, screen_id, types_tuple, int(start_frame), int(end_frame))


def get_allowed_frames_in_range_cached(
    context: Context,
    start_frame: int,
    end_frame: int,
    allowed_types: Set[str],
    ttl_seconds: float = 0.1,
) -> List[int]:
    """TTL付きの小規模キャッシュを使って許可フレームを取得。未ヒットなら収集して保存。"""
    key = _make_cache_key(context, start_frame, end_frame, allowed_types)
    now = perf_counter()

    # ヒット検索（最近のものから）
    for i in range(len(_frames_cache) - 1, -1, -1):
        k, ts, frames = _frames_cache[i]
        if k == key and (now - ts) <= ttl_seconds:
            return frames

    # 未ヒット: 収集して保存
    frames = collect_allowed_frames_in_range(
        context, start_frame, end_frame, allowed_types
    )
    _frames_cache.append((key, now, frames))
    return frames


def invalidate_allowed_frames_cache() -> None:
    """キャッシュを明示的に無効化。"""
    _frames_cache.clear()


def get_timeline_remapping_ratio(scene: Any) -> float:
    """フレーム再マッピング倍率を取得（通常時は 1.0）。"""
    render = getattr(scene, "render", None)
    if not render:
        return 1.0
    old = getattr(render, "frame_map_old", 100)
    new = getattr(render, "frame_map_new", 100)
    if old > 0 and new > 0 and old != new:
        return new / old
    return 1.0


def get_remapped_allowed_frames_cached(
    context: Context,
    start_frame: int,
    end_frame: int,
    allowed_types: Set[str],
) -> List[int]:
    """タイムライン再マッピング倍率を考慮した許可フレームリストを取得。"""
    scene = context.scene
    ratio = get_timeline_remapping_ratio(scene)
    if abs(ratio - 1.0) < 1e-4:
        return get_allowed_frames_in_range_cached(
            context, start_frame, end_frame, allowed_types
        )

    raw_start = int(round(start_frame / ratio))
    raw_end = int(round(end_frame / ratio))
    if raw_start > raw_end:
        raw_start, raw_end = raw_end, raw_start

    raw_frames = get_allowed_frames_in_range_cached(
        context, raw_start, raw_end, allowed_types
    )
    if not raw_frames:
        return []

    remapped = {int(round(f * ratio)) for f in raw_frames}
    return sorted(remapped)
