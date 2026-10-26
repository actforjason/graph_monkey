"""
メニュー・ヘッダー描画関数の登録/解除ユーティリティ。

アドオンリロード時に、リロード前の draw 関数がメニューに残り続ける
「ゴーストコールバック」を防ぐ。Blender の Menu.append() は関数オブジェクトの
同一性で管理するため、リロードで生成し直された関数は remove() では外せない。
ここでは名前とモジュールが一致する古い関数もまとめて除去する。

使用例:
    from ..utils.menu_utils import add_menu_draw_func, remove_menu_draw_func

    def register():
        add_menu_draw_func(GRAPH_MT_editor_menus, draw_func, prepend=True)

    def unregister():
        remove_menu_draw_func(GRAPH_MT_editor_menus, draw_func)
"""

from typing import Callable

from .logging import get_logger

log = get_logger(__name__)


def _get_draw_funcs(menu_cls):
    """メニュークラスが保持する draw 関数リストを取得（未対応なら None）"""
    initializer = getattr(menu_cls, "_dyn_ui_initialize", None)
    if initializer is None:
        return None
    try:
        return initializer()
    except Exception as e:
        log.debug(f"Failed to get draw funcs for {menu_cls.__name__}: {e}")
        return None


def _is_same_draw_func(func, other) -> bool:
    """同一の draw 関数か判定（リロード前の別オブジェクトも一致とみなす）"""
    if func is other:
        return True
    return (
        getattr(func, "__name__", None) == getattr(other, "__name__", None)
        and getattr(func, "__module__", None) == getattr(other, "__module__", None)
    )


def _remove_matching(menu_cls, draw_func: Callable) -> bool:
    """登録済みの同一 draw 関数をすべて解除する"""
    draw_funcs = _get_draw_funcs(menu_cls)
    if draw_funcs is None:
        try:
            menu_cls.remove(draw_func)
            return True
        except Exception:
            return False

    removed = False
    for registered in list(draw_funcs):
        if _is_same_draw_func(registered, draw_func):
            try:
                menu_cls.remove(registered)
                removed = True
            except Exception:
                pass
    return removed


def add_menu_draw_func(menu_cls, draw_func: Callable, prepend: bool = False) -> bool:
    """
    メニューに draw 関数を登録する（冪等）。

    同じ関数（リロード前の残骸を含む）が既に登録されている場合は先に除去する。

    Args:
        menu_cls: 登録先の Menu / Header クラス
        draw_func: 描画関数
        prepend: True なら先頭に挿入

    Returns:
        bool: 登録に成功した場合 True
    """
    _remove_matching(menu_cls, draw_func)

    try:
        if prepend:
            menu_cls.prepend(draw_func)
        else:
            menu_cls.append(draw_func)
        return True
    except Exception as e:
        log.error(f"Failed to add draw func to {menu_cls.__name__}: {e}")
        return False


def remove_menu_draw_func(menu_cls, draw_func: Callable) -> bool:
    """
    メニューから draw 関数を解除する。

    リロードで関数オブジェクトが変わっていても、名前とモジュールが一致すれば除去する。

    Args:
        menu_cls: 解除対象の Menu / Header クラス
        draw_func: 描画関数

    Returns:
        bool: 1 つ以上解除した場合 True
    """
    return _remove_matching(menu_cls, draw_func)
