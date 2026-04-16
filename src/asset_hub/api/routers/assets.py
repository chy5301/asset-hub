import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session

from asset_hub.api.deps import get_session
from asset_hub.api.schemas.asset import AssetCreate, AssetRead, AssetUpdate
from asset_hub.errors import DuplicateError, NotFoundError, ValidationError
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
    try:
        a = svc.register(
            name=body.name,
            type_id=body.type_id,
            serial_number=body.serial_number,
            holder=body.holder,
            location=body.location,
            notes=body.notes,
            custom_data=body.custom_data,
        )
    except NotFoundError:
        raise HTTPException(404, "类型不存在")
    except DuplicateError as e:
        raise HTTPException(409, str(e))
    except ValidationError as e:
        raise HTTPException(422, str(e))
    return a


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
    try:
        return svc.get_asset(asset_id)
    except NotFoundError:
        raise HTTPException(404, "资产不存在")


@router.patch("/{asset_id}", response_model=AssetRead)
def update_asset(
    asset_id: uuid.UUID,
    body: AssetUpdate,
    svc: Annotated[AssetService, Depends(_get_svc)],
):
    kwargs = body.model_dump(exclude_unset=True)
    try:
        return svc.update_asset(asset_id, **kwargs)
    except NotFoundError:
        raise HTTPException(404, "资产不存在")


@router.delete("/{asset_id}", status_code=204)
def delete_asset(
    asset_id: uuid.UUID,
    svc: Annotated[AssetService, Depends(_get_svc)],
):
    try:
        svc.delete_asset(asset_id)
    except NotFoundError:
        raise HTTPException(404, "资产不存在")
    return Response(status_code=204)
