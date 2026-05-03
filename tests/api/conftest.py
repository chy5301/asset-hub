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


@pytest.fixture
def idle_asset(client, sample_type_nb_via_api):
    """创建一个 IDLE 状态资产，返回 dict 含 id（其他字段也可能用到）。"""
    resp = client.post(
        "/api/assets",
        json={
            "name": "测试笔记本",
            "type_id": sample_type_nb_via_api,
            "custom_data": {},
        },
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture
def retired_asset(client, sample_type_nb_via_api):
    resp = client.post(
        "/api/assets",
        json={"name": "已退役", "type_id": sample_type_nb_via_api, "custom_data": {}},
    )
    assert resp.status_code == 201
    aid = resp.json()["id"]
    r = client.post(f"/api/assets/{aid}/transitions", json={"kind": "RETIRE"})
    assert r.status_code == 201
    return resp.json()


@pytest.fixture
def disposed_asset(client, sample_type_nb_via_api):
    resp = client.post(
        "/api/assets",
        json={"name": "已处置", "type_id": sample_type_nb_via_api, "custom_data": {}},
    )
    assert resp.status_code == 201
    aid = resp.json()["id"]
    r1 = client.post(f"/api/assets/{aid}/transitions", json={"kind": "RETIRE"})
    assert r1.status_code == 201
    r2 = client.post(f"/api/assets/{aid}/transitions", json={"kind": "DISPOSE"})
    assert r2.status_code == 201
    return resp.json()
