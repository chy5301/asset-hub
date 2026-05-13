"""GET /api/export router. spec §2.1."""

from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlmodel import Session

from asset_hub.api.deps import get_session
from asset_hub.models.asset import AssetStatus
from asset_hub.services.asset import AssetService
from asset_hub.services.asset_type import TypeService
from asset_hub.services.export import ExportService

router = APIRouter()

_CONTENT_TYPES = {
    "csv": "text/csv; charset=utf-8",
    "xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
}


@router.get("")
def export_assets(
    session: Annotated[Session, Depends(get_session)],
    format: Annotated[Literal["csv", "xlsx"], Query()],
    type_id: Annotated[uuid.UUID | None, Query()] = None,
    status: Annotated[AssetStatus | None, Query()] = None,
    holder: Annotated[str | None, Query()] = None,
    q: Annotated[str | None, Query()] = None,
    include_retired: Annotated[bool, Query()] = False,
    include_disposed: Annotated[bool, Query()] = False,
) -> Response:
    """spec §2.1: 单端点 CSV/XLSX 导出. format 必填; filter 复用 list."""
    asset_svc = AssetService(session)
    type_svc = TypeService(session)
    export_svc = ExportService(session, asset_svc, type_svc)

    data, filename = export_svc.export(
        format=format,
        type_id=type_id,
        status=status,
        holder=holder,
        q=q,
        include_retired=include_retired,
        include_disposed=include_disposed,
    )

    return Response(
        content=data,
        media_type=_CONTENT_TYPES[format],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
