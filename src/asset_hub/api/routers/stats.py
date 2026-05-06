"""M3b 看板 stats router — GET /api/stats."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session

from asset_hub.api.deps import get_session
from asset_hub.api.schemas.stats import StatsRead
from asset_hub.services.stats import StatsService, parse_stats_fields

router = APIRouter()


@router.get(
    "",
    response_model=StatsRead,
    response_model_exclude_none=True,
)
def get_stats(
    session: Annotated[Session, Depends(get_session)],
    include_retired: bool = False,
    include_disposed: bool = False,
    fields: str | None = None,
):
    parsed = parse_stats_fields(fields)
    return StatsService(session).get_dashboard_stats(
        include_retired=include_retired,
        include_disposed=include_disposed,
        fields=parsed,
    )
