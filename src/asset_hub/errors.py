# src/asset_hub/errors.py
class AssetHubError(Exception):
    pass


class NotFoundError(AssetHubError):
    pass


class DuplicateError(AssetHubError):
    pass


class ValidationError(AssetHubError):
    pass
