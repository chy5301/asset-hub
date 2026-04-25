from collections.abc import Generator
from contextlib import contextmanager
from enum import Enum
from typing import overload
from uuid import UUID

from sqlmodel import Session

from asset_hub.cli.envelope import print_error
from asset_hub.db import get_engine


@contextmanager
def cli_session() -> Generator[Session, None, None]:
    with Session(get_engine()) as session:
        yield session


@overload
def parse_uuid(raw: str, json_output: bool) -> UUID: ...
@overload
def parse_uuid(raw: None, json_output: bool) -> None: ...


def parse_uuid(raw: str | None, json_output: bool) -> UUID | None:
    """解析 UUID 字符串，无效时以 exit_code=2 退出。`None` 透传。"""
    if raw is None:
        return None
    try:
        return UUID(raw)
    except ValueError:
        print_error(f"无效的 UUID: {raw}", json_output, exit_code=2)


@overload
def parse_enum[E: Enum](cls: type[E], raw: str, json_output: bool) -> E: ...
@overload
def parse_enum[E: Enum](cls: type[E], raw: None, json_output: bool) -> None: ...


def parse_enum[E: Enum](cls: type[E], raw: str | None, json_output: bool) -> E | None:
    """解析枚举字符串，无效时以 exit_code=2 退出。`None` 透传。"""
    if raw is None:
        return None
    try:
        return cls(raw)
    except ValueError:
        valid = ", ".join(m.value for m in cls)
        print_error(
            f"无效的 {cls.__name__}: {raw}（允许：{valid}）", json_output, exit_code=2
        )
