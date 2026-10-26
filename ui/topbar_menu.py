# pyright: reportInvalidTypeForm=false
"""
Topbar Menu Manager
トップバーのFileメニューに個人用機能を追加するモジュール
"""

import bpy

from ..operators.run_text_script import TOPBAR_MT_pluglug_run_scripts
from ..utils.menu_utils import add_menu_draw_func, remove_menu_draw_func


# =============================================================================
# メニュー描画関数
# =============================================================================


def draw_file_menu(self, context):
    """TOPBAR_MT_fileメニューに項目を追加"""
    layout = self.layout

    # スクリプト実行サブメニュー
    layout.menu(TOPBAR_MT_pluglug_run_scripts.bl_idname, icon="PLAY")

    layout.separator()

    # # モーションルーレット（非公開）
    # layout.operator(
    #     "monkey.roulette_spin",
    #     text="Motion Roulette",
    #     icon='MOD_DYNAMICPAINT',
    # )
    #
    # # オーバーレイ表示トグル / リセット
    # result = getattr(context.scene, "roulette_result", None)
    # if result and result.is_confirmed:
    #     icon = 'HIDE_OFF' if result.show_overlay else 'HIDE_ON'
    #     text = "テーマを非表示" if result.show_overlay else "テーマを表示"
    #     layout.operator(
    #         "monkey.roulette_toggle_overlay",
    #         text=text,
    #         icon=icon,
    #     )
    #     layout.operator(
    #         "monkey.roulette_reset",
    #         text="リセット",
    #         icon='LOOP_BACK',
    #     )


# =============================================================================
# 登録
# =============================================================================


def register():
    # Fileメニューの先頭に追加
    add_menu_draw_func(bpy.types.TOPBAR_MT_file, draw_file_menu, prepend=True)


def unregister():
    remove_menu_draw_func(bpy.types.TOPBAR_MT_file, draw_file_menu)
