from collections.abc import Generator
from contextlib import contextmanager
from uuid import UUID

from sqlmodel import Session

from asset_hub.db import get_engine


@contextmanager
def cli_session() -> Generator[Session, None, None]:
    with Session(get_engine()) as session:
        yield session


def parse_uuid(raw: str, json_output: bool) -> UUID:
    """解析 UUID 字符串，无效时以 exit_code=2 退出。"""
    try:
        return UUID(raw)
    except ValueError:
        from asset_hub.cli.envelope import print_error

        print_error(f"无效的 UUID: {raw}", json_output, exit_code=2)
        raise  # unreachable — print_error raises SystemExit
