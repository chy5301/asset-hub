import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session

from asset_hub.api.deps import get_session
from asset_hub.api.schemas.checkout import (
    CheckoutCreate,
    CheckoutRead,
    CheckoutReturn,
)
from asset_hub.services.checkout import CheckoutService

router = APIRouter()


def _get_svc(session: Annotated[Session, Depends(get_session)]) -> CheckoutService:
    return CheckoutService(session)


@router.post("/{asset_id}/checkout", status_code=201, response_model=CheckoutRead)
def checkout_asset(
    asset_id: uuid.UUID,
    body: CheckoutCreate,
    svc: Annotated[CheckoutService, Depends(_get_svc)],
):
    return svc.checkout(
        asset_id=asset_id,
        holder=body.holder,
        location=body.location,
        note=body.note,
    )


@router.post("/{asset_id}/return", response_model=CheckoutRead)
def return_asset(
    asset_id: uuid.UUID,
    body: CheckoutReturn,
    svc: Annotated[CheckoutService, Depends(_get_svc)],
):
    return svc.return_(
        asset_id=asset_id,
        note=body.note,
        return_location=body.return_location,
        return_receiver=body.return_receiver,
    )


@router.get("/{asset_id}/history", response_model=list[CheckoutRead])
def asset_history(
    asset_id: uuid.UUID,
    svc: Annotated[CheckoutService, Depends(_get_svc)],
):
    return svc.history(asset_id=asset_id)
