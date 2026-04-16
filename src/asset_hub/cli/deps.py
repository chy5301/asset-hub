from collections.abc import Generator
from contextlib import contextmanager

from sqlmodel import Session

from asset_hub.db import get_engine


@contextmanager
def cli_session() -> Generator[Session, None, None]:
    with Session(get_engine()) as session:
        yield session
