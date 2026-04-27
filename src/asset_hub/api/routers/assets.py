import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlmodel import Session

from asset_hub.api.deps import get_session
from asset_hub.api.schemas.asset import AssetCreate, AssetRead, AssetUpdate
from asset_hub.models.asset import AssetStatus
from asset_hub.services.asset import AssetService

router = APIRouter()


def _get_svc(session: Annotated[Session, Depends(get_session)]) -> AssetService:
    return AssetService(session)


@router.post("", status_code=201, response_model=AssetRead)
def create_asset(
    body: AssetCreate,
    svc: Annotated[AssetService, Depends(_get_svc)],
):
    return svc.register(
        name=body.name,
        type_id=body.type_id,
        serial_number=body.serial_number,
        holder=body.holder,
        location=body.location,
        notes=body.notes,
        custom_data=body.custom_data,
        acquired_at=body.acquired_at,
    )


@router.get("", response_model=list[AssetRead])
def list_assets(
    svc: Annotated[AssetService, Depends(_get_svc)],
    type_id: uuid.UUID | None = None,
    status: AssetStatus | None = None,
    holder: str | None = None,
    q: str | None = None,
):
    return svc.list_assets(type_id=type_id, status=status, holder=holder, q=q)


@router.get("/{asset_id}", response_model=AssetRead)
def get_asset(
    asset_id: uuid.UUID,
    svc: Annotated[AssetService, Depends(_get_svc)],
):
    return svc.get_asset(asset_id)


@router.patch("/{asset_id}", response_model=AssetRead)
def update_asset(
    asset_id: uuid.UUID,
    body: AssetUpdate,
    svc: Annotated[AssetService, Depends(_get_svc)],
):
    """整合编辑 + 状态切换。

    status 字段由 service 层 state_machine 校验合法性，非法转换抛 ValidationError → 422。
    """
    return svc.update_asset(asset_id, **body.model_dump(exclude_unset=True))


@router.delete("/{asset_id}", status_code=204)
def delete_asset(
    asset_id: uuid.UUID,
    svc: Annotated[AssetService, Depends(_get_svc)],
):
    """删除资产 cascade（CheckoutRecord + Attachment FS+DB）。"""
    svc.delete_asset(asset_id)
    return Response(status_code=204)
