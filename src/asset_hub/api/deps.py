from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlmodel import Session

from asset_hub.db import get_engine
from asset_hub.services.attachment import AttachmentService
from asset_hub.storage import get_default_storage
from asset_hub.storage.base import StorageAdapter


def get_session() -> Generator[Session, None, None]:
    with Session(get_engine()) as session:
        yield session


def get_storage() -> StorageAdapter:
    return get_default_storage()


def get_attachment_service(
    session: Annotated[Session, Depends(get_session)],
    storage: Annotated[StorageAdapter, Depends(get_storage)],
) -> AttachmentService:
    return AttachmentService(session, storage)
