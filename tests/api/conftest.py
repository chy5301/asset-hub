import pytest
from sqlmodel import Session, SQLModel, create_engine


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSET_HUB_DATA_DIR", str(tmp_path))

    from fastapi.testclient import TestClient

    from asset_hub.api.app import create_app
    from asset_hub.api.deps import get_session

    url = f"sqlite:///{tmp_path / 'test.db'}"
    engine = create_engine(url)
    SQLModel.metadata.create_all(engine)

    def _override_session():
        with Session(engine) as s:
            yield s

    app = create_app()
    app.dependency_overrides[get_session] = _override_session
    with TestClient(app) as c:
        yield c
