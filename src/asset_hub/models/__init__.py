# 汇总导出，确保 SQLModel.metadata.create_all 能发现所有表模型
from asset_hub.models.asset import Asset, AssetStatus
from asset_hub.models.asset_type import AssetType

__all__ = ["Asset", "AssetStatus", "AssetType"]
