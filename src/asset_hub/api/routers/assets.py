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
    asset = svc.register(
        name=body.name,
        type_id=body.type_id,
        serial_number=body.serial_number,
        holder=body.holder,
        location=body.location,
        notes=body.notes,
        custom_data=body.custom_data,
        acquired_at=body.acquired_at,
    )
    return svc.annotate_idle_days([asset])[0]


@router.get("", response_model=list[AssetRead])
def list_assets(
    svc: Annotated[AssetService, Depends(_get_svc)],
    type_id: uuid.UUID | None = None,
    status: AssetStatus | None = None,
    holder: str | None = None,
    q: str | None = None,
    include_retired: bool = False,
    include_disposed: bool = False,
):
    assets = svc.list_assets(
        type_id=type_id,
        status=status,
        holder=holder,
        q=q,
        include_retired=include_retired,
        include_disposed=include_disposed,
    )
    return svc.annotate_idle_days(assets)


@router.get("/{asset_id}", response_model=AssetRead)
def get_asset(
    asset_id: uuid.UUID,
    svc: Annotated[AssetService, Depends(_get_svc)],
):
    asset = svc.get_asset(asset_id)
    return svc.annotate_idle_days([asset])[0]


@router.patch("/{asset_id}", response_model=AssetRead)
def update_asset(
    asset_id: uuid.UUID,
    body: AssetUpdate,
    svc: Annotated[AssetService, Depends(_get_svc)],
):
    """更新资产非状态字段（name/serial_number/notes/custom_data/acquired_at）。

    状态、holder、location 走 POST /api/assets/{id}/transitions。
    """
    asset = svc.update_asset(asset_id, **body.model_dump(exclude_unset=True))
    return svc.annotate_idle_days([asset])[0]


@router.delete("/{asset_id}", status_code=204)
def delete_asset(
    asset_id: uuid.UUID,
    svc: Annotated[AssetService, Depends(_get_svc)],
):
    """删除资产 cascade（StateTransitionRecord + Attachment FS+DB）。"""
    svc.delete_asset(asset_id)
    return Response(status_code=204)
