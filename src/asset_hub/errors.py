# src/asset_hub/errors.py
class AssetHubError(Exception):
    pass


class NotFoundError(AssetHubError):
    pass


class DuplicateError(AssetHubError):
    pass


class ValidationError(AssetHubError):
    pass


class StateError(AssetHubError):
    """业务规则冲突：对象存在，但当前状态不允许此操作。

    例：对 IN_USE 资产再次派发；对无未归还记录的资产归还。"""
    pass


class ConflictError(AssetHubError):
    """资源被其他对象引用，无法执行删除/修改。

    例：删除仍有资产引用的 AssetType。
    与 StateError 区别：StateError 是单对象生命周期/状态机不允许；
    ConflictError 是跨对象引用关系不允许。"""

    pass


class IllegalTransitionError(Exception):
    """状态机拒绝当前 transition。映射 HTTP 409 Conflict。"""
