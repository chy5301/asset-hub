"""共享工具：service 层通用 sentinel / helper。"""

from typing import Final


class UnsetType:
    """部分更新哨兵——区分"未传字段"与"显式传 None（清空）"。

    单例：UnsetType() 多次实例化返回同一对象。
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "UNSET"

    def __bool__(self) -> bool:
        return False


UNSET: Final = UnsetType()
