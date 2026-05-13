from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Query
from pydantic import BaseModel
from sqlmodel import Session

from asset_hub.db import get_engine
from asset_hub.errors import ValidationError
from asset_hub.services.attachment import AttachmentService
from asset_hub.storage import get_default_storage
from asset_hub.storage.base import StorageAdapter


def get_session() -> Generator[Session, None, None]:
    with Session(get_engine()) as session:
        yield session


def get_storage() -> StorageAdapter:
    return get_default_storage()


def get_attachment_service(
    session: Annotated[Session, Depends(get_session)],
    storage: Annotated[StorageAdapter, Depends(get_storage)],
) -> AttachmentService:
    return AttachmentService(session, storage)


# ---------------- v2.0 §4.4 字段掩码（agent token 节省） ----------------


def parse_fields(fields: str | None = Query(default=None)) -> set[str] | None:
    """解析 ?fields=a,b,c → {'a','b','c'}。空/None 返回 None（表示无过滤）。

    白空格在两端 strip；空 token 丢弃。

    注意：未知字段不在此校验——交给下游 `serialize_with_fields` /
    `filter_list_with_fields` 在拿到 allowed 集后再 raise。"""
    if fields is None:
        return None
    parsed = {f.strip() for f in fields.split(",") if f.strip()}
    return parsed or None


def _raise_unknown_fields(unknown: set[str], allowed: set[str]) -> None:
    raise ValidationError(
        f"未知字段: {', '.join(sorted(unknown))}",
        fields_invalid={f: "未知字段" for f in unknown},
        hint=f"合法字段：{', '.join(sorted(allowed))}",
    )


def serialize_with_fields(
    model: BaseModel,
    fields: set[str] | None,
    allowed: set[str],
) -> dict:
    """按 fields filter 单个 Pydantic model 的 model_dump。

    - fields=None: 返回全字段 model_dump(mode='json')
    - fields 非 None 但含未知字段: raise ValidationError（hint 列合法字段）
    - 否则: model_dump(mode='json', include=fields)
    """
    if fields is None:
        return model.model_dump(mode="json")
    unknown = fields - allowed
    if unknown:
        _raise_unknown_fields(unknown, allowed)
    return model.model_dump(mode="json", include=fields)


def filter_list_with_fields(
    models: list[BaseModel],
    fields: set[str] | None,
    allowed: set[str],
) -> list[dict]:
    """list 版字段掩码：unknown 字段只校验一次，避免每行重复 raise。"""
    if fields is None:
        return [m.model_dump(mode="json") for m in models]
    unknown = fields - allowed
    if unknown:
        _raise_unknown_fields(unknown, allowed)
    return [m.model_dump(mode="json", include=fields) for m in models]
