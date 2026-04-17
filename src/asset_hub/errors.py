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
