import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session

from asset_hub.api.deps import get_session
from asset_hub.api.schemas.asset_type import TypeCreate, TypeRead, TypeUpdate
from asset_hub.services.asset_type import TypeService

router = APIRouter()


def _get_svc(session: Annotated[Session, Depends(get_session)]) -> TypeService:
    return TypeService(session)


@router.post("", status_code=201, response_model=TypeRead)
def create_type(
    body: TypeCreate,
    svc: Annotated[TypeService, Depends(_get_svc)],
):
    return svc.create_type(
        name=body.name,
        code_prefix=body.code_prefix,
        description=body.description,
        custom_fields=[f.model_dump() for f in body.custom_fields],
    )


@router.get("", response_model=list[TypeRead])
def list_types(svc: Annotated[TypeService, Depends(_get_svc)]):
    return svc.list_types()


@router.get("/{type_id}", response_model=TypeRead)
def get_type(
    type_id: uuid.UUID,
    svc: Annotated[TypeService, Depends(_get_svc)],
):
    return svc.get_type(type_id)


@router.delete("/{type_id}", status_code=204)
def delete_type(
    type_id: uuid.UUID,
    svc: Annotated[TypeService, Depends(_get_svc)],
):
    svc.delete_type(type_id)


@router.patch("/{type_id}", response_model=TypeRead)
def update_type(
    type_id: uuid.UUID,
    body: TypeUpdate,
    svc: Annotated[TypeService, Depends(_get_svc)],
):
    """部分更新 type。code_prefix immutable（DTO 已不暴露此字段）。"""
    return svc.update_type(type_id, **body.model_dump(exclude_unset=True))
