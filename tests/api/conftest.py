import pytest
from sqlmodel import Session, SQLModel, create_engine


@pytest.fixture()
def engine(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSET_HUB_DATA_DIR", str(tmp_path))
    # 触发所有 SQLModel 表注册，否则 create_all 不会建表
    import asset_hub.models  # noqa: F401

    url = f"sqlite:///{tmp_path / 'test.db'}"
    eng = create_engine(url)
    SQLModel.metadata.create_all(eng)
    return eng


@pytest.fixture()
def session(engine):
    with Session(engine) as s:
        yield s


@pytest.fixture()
def client(engine):
    from fastapi.testclient import TestClient

    from asset_hub.api.app import create_app
    from asset_hub.api.deps import get_session

    def _override_session():
        with Session(engine) as s:
            yield s

    app = create_app()
    app.dependency_overrides[get_session] = _override_session
    with TestClient(app) as c:
        yield c


@pytest.fixture
def sample_type_nb_via_api(client):
    resp = client.post("/api/types", json={
        "name": "笔记本电脑", "code_prefix": "NB", "custom_fields": [],
    })
    assert resp.status_code == 201
    return resp.json()["id"]
