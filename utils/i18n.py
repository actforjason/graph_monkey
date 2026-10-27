"""
シンプルな国際化(i18n)モジュール。

Blenderの言語設定に基づいて英語/日本語/中国語を切り替える。

使用例:
    from .utils.i18n import _
    label = _("WASD_DESC")  # 言語に応じたテキストを取得
"""

import bpy

# 翻訳辞書
# キー: 識別子, 値: {"en": 英語, "ja": 日本語, "zh": 中国語}
TRANSLATIONS = {
    # === Addon Description ===
    "ADDON_DESC": {
        "en": "Animation workflow toolkit for Graph Editor.\nKeyboard-driven keyframe editing and channel management.",
        "ja": "Graph Editor用アニメーションワークフローツールキット。\nキーボード操作によるキーフレーム編集とチャンネル管理。",
        "zh": "曲线编辑器动画工作流工具包。\n键盘驱动的关键帧编辑与通道管理。",
    },
    # === Quick Start ===
    "QUICK_START": {
        "en": "Quick Start (Graph Editor)",
        "ja": "クイックスタート (Graph Editor)",
        "zh": "快速上手 (Graph Editor)",
    },
    "QUICK_START_DESC": {
        "en": "Learn the basics in 1 minute:",
        "ja": "1分で基本を覚える:",
        "zh": "1分钟掌握基础操作:",
    },
    "WASD_QUICK": {
        "en": "Alt+WASD: Navigate keyframes/channels",
        "ja": "Alt+WASD: キーフレーム/チャンネル移動",
        "zh": "Alt+WASD: 关键帧/通道导航",
    },
    "NUM_QUICK": {
        "en": "1234: Frame jump (works in 3D View too)",
        "ja": "1234: フレームジャンプ (3D Viewでも使用可)",
        "zh": "1234: 帧跳转 (3D视口中亦可用)",
    },
    "NAV_QUICK": {
        "en": "Y (hold): Channel Navigator",
        "ja": "Y (長押し): Channel Navigator",
        "zh": "Y (长按): 通道导航器",
    },
    "PIE_QUICK": {
        "en": "Shift+T/C: Pie menus",
        "ja": "Shift+T/C: Pieメニュー",
        "zh": "Shift+T/C: 饼状菜单",
    },
    # === Features ===
    "FEATURES": {
        "en": "Features",
        "ja": "機能一覧",
        "zh": "功能列表",
    },
    "FEATURE_WASD": {
        "en": "WASD Navigation - Keyboard-based keyframe editing in Graph Editor",
        "ja": "WASDナビゲーション - Graph Editorでのキーボード操作",
        "zh": "WASD 导航 - 曲线编辑器的键盘化关键帧编辑",
    },
    "FEATURE_NAVIGATOR": {
        "en": "Channel Navigator - Interactive channel switching (Y key hold)",
        "ja": "Channel Navigator - インタラクティブなチャンネル切り替え (Y長押し)",
        "zh": "通道导航器 - 交互式通道切换 (长按 Y 键)",
    },
    "FEATURE_PEEK": {
        "en": "Peek - Preview adjacent keyframes temporarily (Shift+3/4)",
        "ja": "Peek - 隣のキーフレームを一時プレビュー (Shift+3/4)",
        "zh": "Peek - 临时预览相邻关键帧 (Shift+3/4)",
    },
    "FEATURE_PIE": {
        "en": "Pie Menus - Quick access to alignment and transform settings",
        "ja": "Pieメニュー - 整列・変形設定への素早いアクセス",
        "zh": "饼状菜单 - 快速访问对齐与变换设置",
    },
    "FEATURE_PLAYBACK": {
        "en": "Playback Speed Controller - Adjust playback speed with time remapping",
        "ja": "再生速度コントローラー - タイムリマップで再生速度を調整",
        "zh": "播放速度控制器 - 变速播放并自动重映射时间范围",
    },
    "FEATURE_VISUALIZER": {
        "en": "Pose Visualizer - Visualize bone rotation/location changes (V key)",
        "ja": "Pose Visualizer - ボーンの回転/移動量を可視化 (Vキー)",
        "zh": "姿态可视化器 - 视口可视化骨骼旋转与位移量 (V 键)",
    },
    # === Tab Names ===
    "TAB_HOW_TO_USE": {
        "en": "How to use",
        "ja": "使い方",
        "zh": "使用方法",
    },
    "TAB_SETTINGS": {
        "en": "Settings",
        "ja": "設定",
        "zh": "设置",
    },
    "TAB_KEYMAP": {
        "en": "Keymap",
        "ja": "キーマップ",
        "zh": "键位映射",
    },
    # === Settings Labels ===
    "HEADER_TOOLS_SETTINGS": {
        "en": "Header Tools Visibility",
        "ja": "ヘッダーツールの表示",
        "zh": "标题栏工具显示",
    },
    "HEADER_TOOLS_GRAPH": {
        "en": "Graph Editor Header",
        "ja": "Graph Editor ヘッダー",
        "zh": "曲线编辑器标题栏",
    },
    "HEADER_TOOLS_ACTION": {
        "en": "Action Management & Slots",
        "ja": "アクション管理とスロット",
        "zh": "Action 管理与槽位",
    },
    "HEADER_TOOLS_INTERPOLATION": {
        "en": "Keyframe Interpolation Type",
        "ja": "キーフレーム補間タイプ",
        "zh": "新关键帧插值类型",
    },
    "HEADER_TOOLS_DOPESHEET": {
        "en": "Dope Sheet Header",
        "ja": "Dope Sheet ヘッダー",
        "zh": "摄影表标题栏",
    },
    "HEADER_TOOLS_PLAYBACK_CONTROLS": {
        "en": "Playback Controls Footer",
        "ja": "再生コントロールフッター",
        "zh": "播放控制栏",
    },
    "HEADER_TOOLS_PLAYBACK_SPEED": {
        "en": "Playback Speed Controller",
        "ja": "再生速度コントローラー",
        "zh": "播放速度控制器",
    },
    "HEADER_TOOLS_PLAYBACK_PREVIEW": {
        "en": "Playback Viewport Preview",
        "ja": "再生プレビュー",
        "zh": "播放视口预览",
    },
    "HEADER_TOOLS_OTHER": {
        "en": "Other Time Editors Header",
        "ja": "その他のタイムエディター",
        "zh": "其他时间编辑器标题栏",
    },
    "HEADER_TOOLS_SYNC_RANGE": {
        "en": "Sync Visible Range",
        "ja": "表示範囲の同期",
        "zh": "时间范围同步视野",
    },
    "GRAPH_EDITOR_SETTINGS": {
        "en": "Graph Editor",
        "ja": "Graph Editor",
        "zh": "曲线编辑器",
    },
    "CHANNEL_NAV_SETTINGS": {
        "en": "Channel Navigator",
        "ja": "Channel Navigator",
        "zh": "通道导航器",
    },
    "OVERLAY_SETTINGS": {
        "en": "Channel Overlay",
        "ja": "Channel Overlay",
        "zh": "通道覆盖层",
    },
    "POSE_VISUALIZER_SETTINGS": {
        "en": "Pose Visualizer",
        "ja": "Pose Visualizer",
        "zh": "姿态可视化器",
    },
    "PLAYBACK_SETTINGS": {
        "en": "Playback Preview",
        "ja": "再生プレビュー",
        "zh": "播放视口预览",
    },
    "CHANNEL_MOVE": {
        "en": "Channel Movement (Alt+W/S)",
        "ja": "チャンネル移動 (Alt+W/S)",
        "zh": "通道移动 (Alt+W/S)",
    },
    "KEYFRAME_MOVE": {
        "en": "Keyframe Movement (Alt+A/D)",
        "ja": "キーフレーム移動 (Alt+A/D)",
        "zh": "关键帧移动 (Alt+A/D)",
    },
    # === Documentation Link ===
    "DOC_LINK": {
        "en": "See README for full documentation",
        "ja": "詳細はREADMEを参照",
        "zh": "查看 README 了解完整文档",
    },
    "GITHUB_URL": {
        "en": "https://github.com/Pluglug/graph_monkey",
        "ja": "https://github.com/Pluglug/graph_monkey",
        "zh": "https://github.com/Pluglug/graph_monkey",
    },
}


def get_language():
    """Blenderの言語設定を取得（ja/zh/en）"""
    locale = bpy.app.translations.locale
    if locale:
        if locale.startswith("ja"):
            return "ja"
        if locale.startswith("zh"):
            return "zh"
    return "en"


def _(key, **kwargs):
    """
    翻訳テキストを取得する。

    Args:
        key: 翻訳キー
        **kwargs: format()に渡す引数

    Returns:
        翻訳されたテキスト。キーが見つからない場合はキーをそのまま返す。
    """
    lang = get_language()

    if key in TRANSLATIONS:
        text = TRANSLATIONS[key].get(lang, TRANSLATIONS[key].get("en", key))
    else:
        # キーが見つからない場合はそのまま返す
        text = key

    if kwargs:
        text = text.format(**kwargs)

    return text


def get_all_keys():
    """すべての翻訳キーを取得（デバッグ用）"""
    return list(TRANSLATIONS.keys())
