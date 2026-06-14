import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlmodel import Session

from asset_hub.api.deps import (
    filter_list_with_fields,
    get_session,
    parse_fields,
    serialize_with_fields,
)
from asset_hub.api.schemas.transition import TransitionCreate, TransitionRead
from asset_hub.services.transition import TransitionService

router = APIRouter()

# v2.0 §4.4：TransitionRead 合法字段集（fields= 掩码校验用）
_TRANSITION_READ_FIELDS = set(TransitionRead.model_fields.keys())


def _get_svc(session: Annotated[Session, Depends(get_session)]) -> TransitionService:
    return TransitionService(session)


@router.post("/{asset_id}/transitions", status_code=201, response_model=TransitionRead)
def create_transition(
    asset_id: uuid.UUID,
    body: TransitionCreate,
    svc: Annotated[TransitionService, Depends(_get_svc)],
    fields: Annotated[set[str] | None, Depends(parse_fields)] = None,
):
    kwargs = body.model_dump(exclude_unset=True, exclude={"kind"})
    transition = svc.record_transition(asset_id=asset_id, kind=body.kind, **kwargs)
    if fields is None:
        return transition
    read = TransitionRead.model_validate(transition)
    return JSONResponse(
        status_code=201,
        content=serialize_with_fields(read, fields, _TRANSITION_READ_FIELDS),
    )


@router.get("/{asset_id}/transitions", response_model=list[TransitionRead])
def list_transitions(
    asset_id: uuid.UUID,
    svc: Annotated[TransitionService, Depends(_get_svc)],
    fields: Annotated[set[str] | None, Depends(parse_fields)] = None,
):
    transitions = svc.list_transitions(asset_id)
    if fields is None:
        return transitions
    reads = [TransitionRead.model_validate(t) for t in transitions]
    return JSONResponse(
        content=filter_list_with_fields(reads, fields, _TRANSITION_READ_FIELDS)
    )


@router.post("/{asset_id}/transitions/undo", response_model=TransitionRead)
def undo_last_transition(
    asset_id: uuid.UUID,
    svc: Annotated[TransitionService, Depends(_get_svc)],
):
    """撤销该资产最后一条流转记录（物理删除，元操作不进状态机）。
    域异常（NotFoundError/StateError）由 api/app.py 集中映射 404/409。"""
    return svc.undo_last_transition(asset_id)
