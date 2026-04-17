import uuid
from collections.abc import Iterator
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile
from fastapi.responses import StreamingResponse

from asset_hub.api.deps import get_attachment_service
from asset_hub.api.schemas.attachment import AttachmentRead
from asset_hub.models.attachment import AttachmentKind
from asset_hub.services.attachment import AttachmentService

router = APIRouter()


def _iter_file(fh, chunk_size: int = 1 << 16) -> Iterator[bytes]:
    try:
        while chunk := fh.read(chunk_size):
            yield chunk
    finally:
        fh.close()


@router.post(
    "/assets/{asset_id}/attachments",
    status_code=201,
    response_model=AttachmentRead,
    tags=["attachments"],
)
def upload_attachment(
    asset_id: uuid.UUID,
    svc: Annotated[AttachmentService, Depends(get_attachment_service)],
    file: Annotated[UploadFile, File()],
    kind: Annotated[AttachmentKind, Form()] = AttachmentKind.OTHER,
):
    filename = file.filename or "unnamed"
    return svc.add(
        asset_id=asset_id,
        kind=kind,
        original_name=filename,
        stream=file.file,
        mime_type=file.content_type or None,
    )


@router.get(
    "/assets/{asset_id}/attachments",
    response_model=list[AttachmentRead],
    tags=["attachments"],
)
def list_attachments(
    asset_id: uuid.UUID,
    svc: Annotated[AttachmentService, Depends(get_attachment_service)],
):
    return svc.list(asset_id=asset_id)


@router.get(
    "/attachments/{attachment_id}",
    response_model=AttachmentRead,
    tags=["attachments"],
)
def get_attachment(
    attachment_id: uuid.UUID,
    svc: Annotated[AttachmentService, Depends(get_attachment_service)],
):
    return svc.get(attachment_id)


@router.get("/attachments/{attachment_id}/content", tags=["attachments"])
def download_attachment(
    attachment_id: uuid.UUID,
    svc: Annotated[AttachmentService, Depends(get_attachment_service)],
):
    att, fh = svc.open_stream(attachment_id)
    # RFC 5987：支持非 ASCII 文件名（中文等），避免 latin-1 头部报错
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(att.original_name)}"
    }
    return StreamingResponse(_iter_file(fh), media_type=att.mime_type, headers=headers)


@router.delete(
    "/attachments/{attachment_id}", status_code=204, tags=["attachments"]
)
def delete_attachment(
    attachment_id: uuid.UUID,
    svc: Annotated[AttachmentService, Depends(get_attachment_service)],
):
    svc.delete(attachment_id)
    return Response(status_code=204)
