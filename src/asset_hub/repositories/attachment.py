import uuid

from sqlmodel import Session, select

from asset_hub.models.attachment import Attachment


class AttachmentRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, att: Attachment) -> Attachment:
        self.session.add(att)
        self.session.flush()
        return att

    def get(self, attachment_id: uuid.UUID) -> Attachment | None:
        return self.session.get(Attachment, attachment_id)

    def list_by_asset(self, asset_id: uuid.UUID) -> list[Attachment]:
        stmt = (
            select(Attachment)
            .where(Attachment.asset_id == asset_id)
            .order_by(Attachment.uploaded_at.desc(), Attachment.id.desc())
        )
        return list(self.session.exec(stmt).all())

    def find_by_asset_and_sha256(
        self, asset_id: uuid.UUID, sha256: str
    ) -> Attachment | None:
        stmt = (
            select(Attachment)
            .where(Attachment.asset_id == asset_id)
            .where(Attachment.sha256 == sha256)
        )
        return self.session.exec(stmt).first()

    def any_with_sha256(self, sha256: str) -> bool:
        stmt = select(Attachment.id).where(Attachment.sha256 == sha256).limit(1)
        return self.session.exec(stmt).first() is not None

    def delete(self, att: Attachment) -> None:
        self.session.delete(att)
        self.session.flush()
