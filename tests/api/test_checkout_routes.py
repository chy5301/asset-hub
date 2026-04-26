from uuid import uuid4

from fastapi.testclient import TestClient


def _create_type_and_asset(client: TestClient) -> str:
    r = client.post("/api/types", json={"name": "笔记本", "code_prefix": "NB"})
    type_id = r.json()["id"]
    r = client.post("/api/assets", json={
        "name": "X1", "type_id": type_id, "custom_data": {},
    })
    return r.json()["id"]


class TestCheckoutEndpoint:
    def test_checkout_idle_asset(self, client: TestClient):
        asset_id = _create_type_and_asset(client)
        resp = client.post(f"/api/assets/{asset_id}/checkout", json={
            "holder": "张三",
            "location": "工位 5",
            "note": "借用一周",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["holder"] == "张三"
        assert data["location"] == "工位 5"
        assert data["checkout_note"] == "借用一周"
        assert data["returned_at"] is None

        r = client.get(f"/api/assets/{asset_id}")
        assert r.json()["status"] == "IN_USE"

    def test_checkout_nonexistent_404(self, client: TestClient):
        resp = client.post(f"/api/assets/{uuid4()}/checkout", json={
            "holder": "张三",
        })
        assert resp.status_code == 404

    def test_checkout_already_in_use_409(self, client: TestClient):
        asset_id = _create_type_and_asset(client)
        client.post(f"/api/assets/{asset_id}/checkout", json={"holder": "张三"})
        resp = client.post(f"/api/assets/{asset_id}/checkout", json={"holder": "李四"})
        assert resp.status_code == 409


class TestReturnEndpoint:
    def test_return_closes_checkout(self, client: TestClient):
        asset_id = _create_type_and_asset(client)
        client.post(f"/api/assets/{asset_id}/checkout", json={"holder": "张三"})
        resp = client.post(f"/api/assets/{asset_id}/return", json={"note": "完好"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["returned_at"] is not None
        assert data["return_note"] == "完好"

        r = client.get(f"/api/assets/{asset_id}")
        assert r.json()["status"] == "IDLE"

    def test_return_without_open_409(self, client: TestClient):
        asset_id = _create_type_and_asset(client)
        resp = client.post(f"/api/assets/{asset_id}/return", json={})
        assert resp.status_code == 409

    def test_return_nonexistent_404(self, client: TestClient):
        resp = client.post(f"/api/assets/{uuid4()}/return", json={})
        assert resp.status_code == 404


class TestHistoryEndpoint:
    def test_history_empty(self, client: TestClient):
        asset_id = _create_type_and_asset(client)
        resp = client.get(f"/api/assets/{asset_id}/history")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_history_lists_records(self, client: TestClient):
        asset_id = _create_type_and_asset(client)
        client.post(f"/api/assets/{asset_id}/checkout", json={"holder": "张三"})
        client.post(f"/api/assets/{asset_id}/return", json={})
        client.post(f"/api/assets/{asset_id}/checkout", json={"holder": "李四"})

        resp = client.get(f"/api/assets/{asset_id}/history")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["holder"] == "李四"
        assert data[1]["holder"] == "张三"

    def test_history_nonexistent_404(self, client: TestClient):
        resp = client.get(f"/api/assets/{uuid4()}/history")
        assert resp.status_code == 404
