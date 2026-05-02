from fastapi.testclient import TestClient


def _create_type(client: TestClient, name="原名", prefix="ZZ", **extra) -> str:
    body = {"name": name, "code_prefix": prefix, "custom_fields": [], **extra}
    resp = client.post("/api/types", json=body)
    assert resp.status_code == 201
    return resp.json()["id"]


class TestPatchType:
    def test_patch_returns_200_with_updated_dto(self, client: TestClient):
        tid = _create_type(client)
        resp = client.patch(f"/api/types/{tid}", json={"name": "新名"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "新名"
        assert data["code_prefix"] == "ZZ"  # 不动

    def test_patch_404_on_unknown_id(self, client: TestClient):
        import uuid
        resp = client.patch(f"/api/types/{uuid.uuid4()}", json={"name": "x"})
        assert resp.status_code == 404

    def test_patch_409_on_duplicate_name(self, client: TestClient):
        _create_type(client, name="A", prefix="AA")
        tid = _create_type(client, name="B", prefix="BB")
        resp = client.patch(f"/api/types/{tid}", json={"name": "A"})
        assert resp.status_code == 409

    def test_patch_422_on_bad_field_def(self, client: TestClient):
        tid = _create_type(client)
        # CustomFieldDef 缺 type
        resp = client.patch(
            f"/api/types/{tid}",
            json={"custom_fields": [{"key": "x"}]},
        )
        # Pydantic body 校验先于 service：缺 type 会被 router level 422
        assert resp.status_code == 422

    def test_patch_with_only_name_keeps_other_fields(self, client: TestClient):
        tid = _create_type(client, description="原描述")
        resp = client.patch(f"/api/types/{tid}", json={"name": "新名"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["description"] == "原描述"

    def test_patch_custom_fields_full_replace_semantics(self, client: TestClient):
        tid = _create_type(
            client,
            custom_fields=[{"key": "old", "type": "string"}],
        )
        resp = client.patch(
            f"/api/types/{tid}",
            json={"custom_fields": [{"key": "new", "type": "int"}]},
        )
        assert resp.status_code == 200
        fields = resp.json()["custom_fields"]
        assert len(fields) == 1
        assert fields[0]["key"] == "new"
