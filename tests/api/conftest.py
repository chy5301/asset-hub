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
def in_use_asset(client, sample_type_nb_via_api):
    """创建一个 IN_USE 状态资产（checkout 后），返回 dict 含 id。"""
    resp = client.post(
        "/api/assets",
        json={
            "name": "在用笔记本",
            "type_id": sample_type_nb_via_api,
            "custom_data": {},
        },
    )
    assert resp.status_code == 201
    aid = resp.json()["id"]
    r = client.post(
        f"/api/assets/{aid}/transitions",
        json={"kind": "CHECKOUT_INTERNAL", "to_holder": "张三"},
    )
    assert r.status_code == 201
    return client.get(f"/api/assets/{aid}").json()


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


@pytest.fixture
def idle_assets_5(client, sample_type_nb_via_api):
    """创建 5 个 IDLE 状态资产，返回 list of dict（含 id 等字段）。"""
    assets = []
    for i in range(5):
        resp = client.post(
            "/api/assets",
            json={
                "name": f"空闲笔记本-{i + 1}",
                "type_id": sample_type_nb_via_api,
                "custom_data": {},
            },
        )
        assert resp.status_code == 201
        assets.append(resp.json())
    return assets


@pytest.fixture
def populated_db(client, sample_type_nb_via_api):
    """创若干资产（含 IDLE/IN_USE/RETIRED）用于 stats 测试。

    共 4 个资产：2 IDLE / 1 IN_USE / 1 RETIRED。
    """
    type_id = sample_type_nb_via_api

    # a1, a2 保持 IDLE
    a1 = client.post(
        "/api/assets",
        json={"name": "Stats笔记本-1", "type_id": type_id, "custom_data": {}},
    ).json()
    assert "id" in a1

    a2 = client.post(
        "/api/assets",
        json={"name": "Stats笔记本-2", "type_id": type_id, "holder": "张三", "custom_data": {}},
    ).json()
    assert "id" in a2

    # a3 → IN_USE
    a3_resp = client.post(
        "/api/assets",
        json={"name": "Stats笔记本-3", "type_id": type_id, "custom_data": {}},
    )
    assert a3_resp.status_code == 201
    a3 = a3_resp.json()
    r = client.post(
        f"/api/assets/{a3['id']}/transitions",
        json={"kind": "CHECKOUT_INTERNAL", "to_holder": "李四"},
    )
    assert r.status_code == 201

    # a4 → RETIRED
    a4_resp = client.post(
        "/api/assets",
        json={"name": "Stats笔记本-4", "type_id": type_id, "custom_data": {}},
    )
    assert a4_resp.status_code == 201
    a4 = a4_resp.json()
    r = client.post(f"/api/assets/{a4['id']}/transitions", json={"kind": "RETIRE"})
    assert r.status_code == 201

    return [a1, a2, a3, a4]
