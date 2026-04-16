from fastapi.testclient import TestClient


class TestCreateType:
    def test_create_minimal(self, client: TestClient):
        resp = client.post("/api/types", json={"name": "笔记本电脑"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "笔记本电脑"
        assert "id" in data

    def test_create_with_fields(self, client: TestClient):
        body = {
            "name": "显卡",
            "custom_fields": [
                {"key": "brand", "label": "品牌", "type": "string", "required": True}
            ],
        }
        resp = client.post("/api/types", json=body)
        assert resp.status_code == 201
        assert len(resp.json()["custom_fields"]) == 1

    def test_create_duplicate_409(self, client: TestClient):
        client.post("/api/types", json={"name": "硬盘"})
        resp = client.post("/api/types", json={"name": "硬盘"})
        assert resp.status_code == 409


class TestListTypes:
    def test_list_empty(self, client: TestClient):
        resp = client.get("/api/types")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_after_create(self, client: TestClient):
        client.post("/api/types", json={"name": "A"})
        client.post("/api/types", json={"name": "B"})
        resp = client.get("/api/types")
        assert len(resp.json()) == 2


class TestGetType:
    def test_get_existing(self, client: TestClient):
        r = client.post("/api/types", json={"name": "硬盘"})
        type_id = r.json()["id"]
        resp = client.get(f"/api/types/{type_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "硬盘"

    def test_get_nonexistent_404(self, client: TestClient):
        from uuid import uuid4
        resp = client.get(f"/api/types/{uuid4()}")
        assert resp.status_code == 404
