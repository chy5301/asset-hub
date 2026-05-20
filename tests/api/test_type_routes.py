from fastapi.testclient import TestClient


class TestCreateType:
    def test_create_minimal(self, client: TestClient):
        resp = client.post(
            "/api/types", json={"name": "笔记本电脑", "code_prefix": "NB"}
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "笔记本电脑"
        assert data["code_prefix"] == "NB"
        assert "id" in data
        # §Q：新建 type ref_count = 0
        assert data["ref_count"] == 0

    def test_create_with_fields(self, client: TestClient):
        body = {
            "name": "显卡",
            "code_prefix": "GPU",
            "custom_fields": [
                {"key": "vram_gb", "label": "显存(GB)", "type": "int", "required": True}
            ],
        }
        resp = client.post("/api/types", json=body)
        assert resp.status_code == 201
        assert len(resp.json()["custom_fields"]) == 1

    def test_create_duplicate_name_409(self, client: TestClient):
        client.post("/api/types", json={"name": "硬盘", "code_prefix": "HD"})
        # 不同 prefix，但 name 重复
        resp = client.post("/api/types", json={"name": "硬盘", "code_prefix": "HDX"})
        assert resp.status_code == 409

    def test_create_normalizes_prefix_to_upper(self, client: TestClient):
        # 输入小写，DTO 层 field_validator 已 .upper()，service 再校验
        resp = client.post("/api/types", json={"name": "笔记本", "code_prefix": "nb"})
        assert resp.status_code == 201
        assert resp.json()["code_prefix"] == "NB"

    def test_create_missing_prefix_422(self, client: TestClient):
        # 缺 code_prefix → Pydantic 必填校验
        resp = client.post("/api/types", json={"name": "笔记本"})
        assert resp.status_code == 422

    def test_create_invalid_prefix_format_422(self, client: TestClient):
        # 1 字符 / 5+ 字符 → service ValidationError → 422
        resp_short = client.post(
            "/api/types", json={"name": "笔记本", "code_prefix": "N"}
        )
        assert resp_short.status_code == 422
        resp_long = client.post(
            "/api/types", json={"name": "笔记本", "code_prefix": "LAPTOP"}
        )
        assert resp_long.status_code == 422

    def test_create_duplicate_prefix_409(self, client: TestClient):
        client.post("/api/types", json={"name": "笔记本", "code_prefix": "NB"})
        # 不同 name，相同 prefix
        resp = client.post(
            "/api/types", json={"name": "笔记本电脑", "code_prefix": "NB"}
        )
        assert resp.status_code == 409


class TestListTypes:
    def test_list_empty(self, client: TestClient):
        resp = client.get("/api/types")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_after_create(self, client: TestClient):
        client.post("/api/types", json={"name": "A", "code_prefix": "AA"})
        client.post("/api/types", json={"name": "B", "code_prefix": "BB"})
        resp = client.get("/api/types")
        data = resp.json()
        assert len(data) == 2
        # §Q：每条 type 都带 ref_count 字段（初值 0）
        assert all("ref_count" in t for t in data)
        assert all(t["ref_count"] == 0 for t in data)


class TestGetType:
    def test_get_existing(self, client: TestClient):
        r = client.post("/api/types", json={"name": "硬盘", "code_prefix": "HD"})
        type_id = r.json()["id"]
        resp = client.get(f"/api/types/{type_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "硬盘"
        assert body["code_prefix"] == "HD"
        # §Q：单条 get 也带 ref_count
        assert body["ref_count"] == 0

    def test_get_nonexistent_404(self, client: TestClient):
        from uuid import uuid4

        resp = client.get(f"/api/types/{uuid4()}")
        assert resp.status_code == 404
