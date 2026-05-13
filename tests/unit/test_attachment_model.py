from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from asset_hub.models.asset import Asset
from asset_hub.models.asset_type import AssetType
from asset_hub.models.attachment import Attachment, AttachmentKind


def _make_asset(
    session: Session, *, name: str = "A", code_prefix: str = "TST"
) -> Asset:
    t = AssetType(name=f"T-{name}", code_prefix=code_prefix, custom_fields=[])
    session.add(t)
    session.flush()
    a = Asset(asset_code=f"{code_prefix}-001", name=name, type_id=t.id, custom_data={})
    session.add(a)
    session.commit()
    session.refresh(a)
    return a


def test_attachment_can_be_persisted(session: Session):
    a = _make_asset(session)
    att = Attachment(
        asset_id=a.id,
        kind=AttachmentKind.PHOTO,
        storage_path="2026/04/abc.jpg",
        sha256="a" * 64,
        size=1024,
        mime_type="image/jpeg",
        original_name="x.jpg",
    )
    session.add(att)
    session.commit()
    session.refresh(att)

    assert att.id is not None
    assert att.kind == AttachmentKind.PHOTO
    assert isinstance(att.uploaded_at, datetime)


def test_unique_constraint_blocks_same_asset_same_sha256(session: Session):
    a = _make_asset(session)
    session.add(
        Attachment(
            asset_id=a.id,
            kind=AttachmentKind.PHOTO,
            storage_path="2026/04/abc.jpg",
            sha256="a" * 64,
            size=1,
            mime_type="image/jpeg",
            original_name="x.jpg",
        )
    )
    session.commit()

    session.add(
        Attachment(
            asset_id=a.id,
            kind=AttachmentKind.PHOTO,
            storage_path="2026/04/abc.jpg",
            sha256="a" * 64,
            size=1,
            mime_type="image/jpeg",
            original_name="x2.jpg",
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_different_assets_can_share_sha256(session: Session):
    a1 = _make_asset(session, name="A1", code_prefix="TSA")
    a2 = _make_asset(session, name="A2", code_prefix="TSB")

    session.add(
        Attachment(
            asset_id=a1.id,
            kind=AttachmentKind.DOC,
            storage_path="2026/04/xxx.pdf",
            sha256="b" * 64,
            size=1,
            mime_type="application/pdf",
            original_name="x.pdf",
        )
    )
    session.add(
        Attachment(
            asset_id=a2.id,
            kind=AttachmentKind.DOC,
            storage_path="2026/04/xxx.pdf",
            sha256="b" * 64,
            size=1,
            mime_type="application/pdf",
            original_name="x.pdf",
        )
    )
    session.commit()  # 不应抛异常：跨资产共享同一物理文件是合法的


def test_enum_values_match_spec():
    assert AttachmentKind.PHOTO.value == "photo"
    assert AttachmentKind.INVOICE.value == "invoice"
    assert AttachmentKind.DOC.value == "doc"
    assert AttachmentKind.OTHER.value == "other"
    assert {k.value for k in AttachmentKind} == {"photo", "invoice", "doc", "other"}
