# 汇总导出，确保 SQLModel.metadata.create_all 能发现所有表模型
from asset_hub.models.asset import Asset, AssetStatus
from asset_hub.models.asset_type import AssetType
from asset_hub.models.attachment import Attachment, AttachmentKind
from asset_hub.models.state_transition import StateTransitionRecord, TransitionKind

__all__ = [
    "Asset",
    "AssetStatus",
    "AssetType",
    "Attachment",
    "AttachmentKind",
    "StateTransitionRecord",
    "TransitionKind",
]
