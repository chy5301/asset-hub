import mimetypes
import uuid
from pathlib import Path
from typing import BinaryIO

from sqlmodel import Session

from asset_hub.errors import DuplicateError, NotFoundError
from asset_hub.models.attachment import Attachment, AttachmentKind
from asset_hub.repositories.attachment import AttachmentRepository
from asset_hub.services.asset import AssetService
from asset_hub.storage.base import StorageAdapter


class AttachmentService:
    def __init__(self, session: Session, storage: StorageAdapter):
        self.session = session
        self.repo = AttachmentRepository(session)
        self.asset_svc = AssetService(session)
        self.storage = storage

    def add(
        self,
        asset_id: uuid.UUID,
        *,
        kind: AttachmentKind,
        original_name: str,
        stream: BinaryIO,
        mime_type: str | None = None,
    ) -> Attachment:
        # 1. 资产存在性（NotFoundError 会自然冒泡）
        self.asset_svc.get_asset(asset_id)

        # 2. 落盘（边写边算 sha256）
        ext = Path(original_name).suffix.lower()
        stored = self.storage.save(stream, original_ext=ext)

        # 3. 同资产同内容去重（UniqueConstraint 已兜底，此处给出更友好的错误）
        existing = self.repo.find_by_asset_and_sha256(asset_id, stored.sha256)
        if existing is not None:
            raise DuplicateError(
                f"附件已有相同内容: 资产 {asset_id} 已存在 sha256={stored.sha256} "
                f"的附件（id={existing.id}）"
            )

        # 4. MIME 兜底
        if not mime_type:
            guessed, _ = mimetypes.guess_type(original_name)
            mime_type = guessed or "application/octet-stream"

        att = Attachment(
            asset_id=asset_id,
            kind=kind,
            storage_path=stored.storage_path,
            sha256=stored.sha256,
            size=stored.size,
            mime_type=mime_type,
            original_name=original_name,
        )
        self.repo.add(att)
        self.session.commit()
        self.session.refresh(att)
        return att

    def list(self, asset_id: uuid.UUID) -> list[Attachment]:
        self.asset_svc.get_asset(asset_id)
        return self.repo.list_by_asset(asset_id)

    def get(self, attachment_id: uuid.UUID) -> Attachment:
        att = self.repo.get(attachment_id)
        if att is None:
            raise NotFoundError(f"附件不存在: {attachment_id}")
        return att

    def delete(self, attachment_id: uuid.UUID) -> None:
        att = self.get(attachment_id)
        sha256 = att.sha256
        storage_path = att.storage_path

        self.repo.delete(att)
        self.session.commit()

        # 仅当没有其他 Attachment 引用同 sha256 时才删物理文件
        if not self.repo.any_with_sha256(sha256):
            self.storage.delete(storage_path)
