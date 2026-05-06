"""M3b 看板 stats router — GET /api/stats."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session

from asset_hub.api.deps import get_session
from asset_hub.api.schemas.stats import StatsField, StatsRead
from asset_hub.errors import ValidationError
from asset_hub.services.stats import ALL_FIELDS, StatsService

router = APIRouter()


def _parse_fields(raw: str | None) -> set[StatsField] | None:
    """解析 fields query 参数；含未知段时抛 ValidationError（→ 422）。"""
    if raw is None or raw == "":
        return None
    parts = {p.strip() for p in raw.split(",") if p.strip()}
    unknown = parts - ALL_FIELDS
    if unknown:
        raise ValidationError(
            f"fields 含未知段：{sorted(unknown)}；可选：{sorted(ALL_FIELDS)}"
        )
    return parts  # type: ignore[return-value]


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
    parsed = _parse_fields(fields)
    return StatsService(session).get_dashboard_stats(
        include_retired=include_retired,
        include_disposed=include_disposed,
        fields=parsed,
    )
