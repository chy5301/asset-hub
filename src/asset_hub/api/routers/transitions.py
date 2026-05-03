import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session

from asset_hub.api.deps import get_session
from asset_hub.api.schemas.transition import TransitionCreate, TransitionRead
from asset_hub.services.transition import TransitionService

router = APIRouter()


def _get_svc(session: Annotated[Session, Depends(get_session)]) -> TransitionService:
    return TransitionService(session)


@router.post("/{asset_id}/transitions", status_code=201, response_model=TransitionRead)
def create_transition(
    asset_id: uuid.UUID,
    body: TransitionCreate,
    svc: Annotated[TransitionService, Depends(_get_svc)],
):
    return svc.record_transition(
        asset_id=asset_id,
        kind=body.kind,
        to_holder=body.to_holder,
        to_location=body.to_location,
        note=body.note,
        due_at=body.due_at,
    )


@router.get("/{asset_id}/transitions", response_model=list[TransitionRead])
def list_transitions(
    asset_id: uuid.UUID,
    svc: Annotated[TransitionService, Depends(_get_svc)],
):
    return svc.list_transitions(asset_id)
