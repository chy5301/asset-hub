from fastapi.testclient import TestClient


def _create_type(
    client: TestClient,
    name: str = "笔记本电脑",
    code_prefix: str = "NB",
    fields: list | None = None,
) -> str:
    body = {"name": name, "code_prefix": code_prefix}
    if fields:
        body["custom_fields"] = fields
    r = client.post("/api/types", json=body)
    return r.json()["id"]


class TestCreateAsset:
    def test_create_minimal(self, client: TestClient):
        type_id = _create_type(client)
        resp = client.post("/api/assets", json={
            "name": "ThinkPad X1",
            "type_id": type_id,
            "custom_data": {},
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "ThinkPad X1"
        assert data["status"] == "IDLE"

    def test_create_with_custom_data(self, client: TestClient):
        type_id = _create_type(
            client,
            fields=[{"key": "brand", "label": "品牌", "type": "string", "required": True}],
        )
        resp = client.post("/api/assets", json={
            "name": "ThinkPad X1",
            "type_id": type_id,
            "custom_data": {"brand": "Lenovo"},
        })
        assert resp.status_code == 201
        assert resp.json()["custom_data"]["brand"] == "Lenovo"

    def test_create_bad_type_404(self, client: TestClient):
        from uuid import uuid4
        resp = client.post("/api/assets", json={
            "name": "X",
            "type_id": str(uuid4()),
            "custom_data": {},
        })
        assert resp.status_code == 404

    def test_create_validation_error_422(self, client: TestClient):
        type_id = _create_type(
            client,
            fields=[{"key": "brand", "label": "品牌", "type": "string", "required": True}],
        )
        resp = client.post("/api/assets", json={
            "name": "X",
            "type_id": type_id,
            "custom_data": {},
        })
        assert resp.status_code == 422


class TestListAssets:
    def test_list_empty(self, client: TestClient):
        resp = client.get("/api/assets")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_with_query_params(self, client: TestClient):
        type_id = _create_type(client)
        client.post("/api/assets", json={"name": "A", "type_id": type_id, "custom_data": {}})
        client.post("/api/assets", json={"name": "B", "type_id": type_id, "custom_data": {}})
        resp = client.get("/api/assets")
        assert len(resp.json()) == 2

        resp_q = client.get("/api/assets", params={"q": "A"})
        assert len(resp_q.json()) == 1


class TestGetAsset:
    def test_get_existing(self, client: TestClient):
        type_id = _create_type(client)
        r = client.post("/api/assets", json={"name": "X1", "type_id": type_id, "custom_data": {}})
        asset_id = r.json()["id"]
        resp = client.get(f"/api/assets/{asset_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "X1"

    def test_get_nonexistent_404(self, client: TestClient):
        from uuid import uuid4
        resp = client.get(f"/api/assets/{uuid4()}")
        assert resp.status_code == 404


class TestUpdateAsset:
    def test_update_fields(self, client: TestClient):
        type_id = _create_type(client)
        r = client.post("/api/assets", json={"name": "X1", "type_id": type_id, "custom_data": {}})
        asset_id = r.json()["id"]
        resp = client.patch(f"/api/assets/{asset_id}", json={
            "name": "X2",
            "serial_number": "SN-001",
            "notes": "新备注",
            "acquired_at": "2025-02-01",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "X2"
        assert body["serial_number"] == "SN-001"
        assert body["notes"] == "新备注"
        assert body["acquired_at"] == "2025-02-01"


class TestDeleteAsset:
    def test_delete_existing(self, client: TestClient):
        type_id = _create_type(client)
        r = client.post("/api/assets", json={"name": "X1", "type_id": type_id, "custom_data": {}})
        asset_id = r.json()["id"]
        resp = client.delete(f"/api/assets/{asset_id}")
        assert resp.status_code == 204

        check = client.get(f"/api/assets/{asset_id}")
        assert check.status_code == 404

    def test_delete_nonexistent_404(self, client: TestClient):
        from uuid import uuid4
        resp = client.delete(f"/api/assets/{uuid4()}")
        assert resp.status_code == 404


def test_get_asset_returns_type_name(client, sample_type_nb_via_api):
    """通过 API POST 创建 asset，GET 详情 → 响应里 type_name 已填"""
    create_resp = client.post("/api/assets", json={
        "name": "X1", "type_id": str(sample_type_nb_via_api), "custom_data": {},
    })
    assert create_resp.status_code == 201
    asset_id = create_resp.json()["id"]

    get_resp = client.get(f"/api/assets/{asset_id}")
    body = get_resp.json()
    assert body["type_name"] == "笔记本电脑"
    assert body["asset_code"].startswith("NB-")


def test_delete_asset_cascade(client, sample_type_nb_via_api):
    create = client.post("/api/assets", json={
        "name": "X1", "type_id": sample_type_nb_via_api, "custom_data": {},
    })
    asset_id = create.json()["id"]
    client.post(f"/api/assets/{asset_id}/checkout", json={"holder": "张三"})
    client.post(f"/api/assets/{asset_id}/return", json={})

    resp = client.delete(f"/api/assets/{asset_id}")
    assert resp.status_code == 204

    # 二次 DELETE → 404
    resp2 = client.delete(f"/api/assets/{asset_id}")
    assert resp2.status_code == 404


def test_post_asset_with_acquired_at(client, sample_type_nb_via_api):
    resp = client.post("/api/assets", json={
        "name": "X1", "type_id": sample_type_nb_via_api,
        "custom_data": {}, "acquired_at": "2025-01-15",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["acquired_at"] == "2025-01-15"
    assert body["asset_code"].startswith("NB-")


def test_list_assets_response_contains_idle_days(client, idle_asset):
    """IDLE 资产的 list 响应必须含 idle_days，且为非负整数."""
    res = client.get("/api/assets")
    assert res.status_code == 200
    body = res.json()
    idle_entries = [a for a in body if a["status"] == "IDLE"]
    assert len(idle_entries) > 0
    for a in idle_entries:
        assert isinstance(a["idle_days"], int)
        assert a["idle_days"] >= 0


def test_in_use_asset_idle_days_is_null(client, in_use_asset):
    """非 IDLE 资产 idle_days 必须为 null."""
    res = client.get(f"/api/assets/{in_use_asset['id']}")
    assert res.status_code == 200
    assert res.json()["idle_days"] is None


def test_list_assets_with_idle_filter_and_limit(client, idle_assets_5):
    """验 sort_by/limit/include_retired 等参数透传到 service（不断 sort 顺序——
    单测 fixture 不支持精确断顺序，sort 顺序由 service 层 unit 测试覆盖）."""
    res = client.get("/api/assets?status=IDLE&sort_by=idle_days&sort_order=desc&limit=3")
    assert res.status_code == 200
    body = res.json()
    assert len(body) == 3


def test_list_assets_unknown_sort_by_returns_422(client):
    res = client.get("/api/assets?sort_by=foo")
    assert res.status_code == 422


def test_list_assets_limit_over_max_returns_422(client):
    res = client.get("/api/assets?limit=2000")
    assert res.status_code == 422


def test_list_assets_negative_offset_returns_422(client):
    res = client.get("/api/assets?offset=-1")
    assert res.status_code == 422


def test_get_asset_response_contains_type_name(client, idle_asset):
    """C3 回归（spec §5）：detail 响应必须含 type_name 字段（非 null）.
    M3a 已通过 Asset.type_name @property + AssetRead.type_name 实现
    (SQLModel Relationship lazy='joined')，此测试避免未来重构误删
    @property 或 AssetRead 字段。"""
    asset_id = idle_asset["id"]
    res = client.get(f"/api/assets/{asset_id}")
    assert res.status_code == 200
    body = res.json()
    assert "type_name" in body
    assert body["type_name"] is not None
