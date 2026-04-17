import io
from pathlib import Path
from uuid import uuid4

import pytest
from sqlmodel import Session

from asset_hub.errors import DuplicateError, NotFoundError
from asset_hub.models.attachment import AttachmentKind
from asset_hub.services.asset import AssetService
from asset_hub.services.asset_type import TypeService
from asset_hub.services.attachment import AttachmentService
from asset_hub.storage.local_fs import LocalFSStorage


@pytest.fixture()
def storage(tmp_path: Path) -> LocalFSStorage:
    return LocalFSStorage(root=tmp_path / "attachments")


@pytest.fixture()
def type_svc(session: Session) -> TypeService:
    return TypeService(session)


@pytest.fixture()
def asset_svc(session: Session) -> AssetService:
    return AssetService(session)


@pytest.fixture()
def att_svc(session: Session, storage: LocalFSStorage) -> AttachmentService:
    return AttachmentService(session, storage)


@pytest.fixture()
def simple_type(type_svc: TypeService):
    return type_svc.create_type(name="笔记本", custom_fields=[])


@pytest.fixture()
def asset(asset_svc: AssetService, simple_type):
    return asset_svc.register(name="X1", type_id=simple_type.id, custom_data={})


class TestAdd:
    def test_add_persists_file_and_metadata(
        self,
        att_svc: AttachmentService,
        storage: LocalFSStorage,
        asset,
    ):
        att = att_svc.add(
            asset_id=asset.id,
            kind=AttachmentKind.PHOTO,
            original_name="photo.jpg",
            stream=io.BytesIO(b"fake-jpeg-bytes"),
        )
        assert att.id is not None
        assert att.asset_id == asset.id
        assert att.kind == AttachmentKind.PHOTO
        assert att.size == len(b"fake-jpeg-bytes")
        assert att.original_name == "photo.jpg"
        assert att.mime_type == "image/jpeg"
        assert len(att.sha256) == 64
        assert att.storage_path.endswith(f"{att.sha256}.jpg")

        # 物理文件落盘
        assert (storage.root / att.storage_path).read_bytes() == b"fake-jpeg-bytes"

    def test_add_uses_explicit_mime_type_when_given(
        self, att_svc: AttachmentService, asset
    ):
        att = att_svc.add(
            asset_id=asset.id,
            kind=AttachmentKind.OTHER,
            original_name="whatever.bin",
            stream=io.BytesIO(b"x"),
            mime_type="application/x-custom",
        )
        assert att.mime_type == "application/x-custom"

    def test_add_fallbacks_to_octet_stream_for_unknown_ext(
        self, att_svc: AttachmentService, asset
    ):
        att = att_svc.add(
            asset_id=asset.id,
            kind=AttachmentKind.OTHER,
            original_name="file.mystery",
            stream=io.BytesIO(b"x"),
        )
        assert att.mime_type == "application/octet-stream"

    def test_add_to_nonexistent_asset_raises(self, att_svc: AttachmentService):
        with pytest.raises(NotFoundError):
            att_svc.add(
                asset_id=uuid4(),
                kind=AttachmentKind.OTHER,
                original_name="x.bin",
                stream=io.BytesIO(b"x"),
            )

    def test_add_same_sha256_to_same_asset_raises_duplicate(
        self, att_svc: AttachmentService, asset
    ):
        att_svc.add(
            asset_id=asset.id,
            kind=AttachmentKind.PHOTO,
            original_name="a.jpg",
            stream=io.BytesIO(b"same-bytes"),
        )
        with pytest.raises(DuplicateError, match="已有相同内容"):
            att_svc.add(
                asset_id=asset.id,
                kind=AttachmentKind.PHOTO,
                original_name="b.jpg",  # 不同文件名，但 bytes 相同
                stream=io.BytesIO(b"same-bytes"),
            )

    def test_add_same_sha256_across_different_assets_succeeds(
        self,
        att_svc: AttachmentService,
        asset_svc: AssetService,
        asset,
        simple_type,
    ):
        other = asset_svc.register(name="X2", type_id=simple_type.id, custom_data={})

        first = att_svc.add(
            asset_id=asset.id,
            kind=AttachmentKind.DOC,
            original_name="shared.pdf",
            stream=io.BytesIO(b"shared"),
        )
        second = att_svc.add(
            asset_id=other.id,
            kind=AttachmentKind.DOC,
            original_name="shared.pdf",
            stream=io.BytesIO(b"shared"),
        )
        assert first.sha256 == second.sha256
        assert first.storage_path == second.storage_path
        assert first.id != second.id
