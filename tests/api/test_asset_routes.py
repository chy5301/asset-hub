from fastapi.testclient import TestClient


def _create_type(client: TestClient, name: str = "笔记本电脑", fields: list | None = None) -> str:
    body = {"name": name}
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
        resp = client.patch(f"/api/assets/{asset_id}", json={"holder": "张三"})
        assert resp.status_code == 200
        assert resp.json()["holder"] == "张三"


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
