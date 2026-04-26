import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session

from asset_hub.api.deps import get_session
from asset_hub.api.schemas.asset_type import TypeCreate, TypeRead
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
