from asset_hub.config import Settings
from asset_hub.storage.base import StorageAdapter
from asset_hub.storage.local_fs import LocalFSStorage


def get_default_storage() -> StorageAdapter:
    """构造 v1 默认本地文件系统存储。每次都按当前 Settings 重建以兼容测试环境覆盖。"""
    return LocalFSStorage(root=Settings().attachments_dir)
