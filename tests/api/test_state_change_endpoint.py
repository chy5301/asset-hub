"""§14.5 PATCH /api/assets/{id} body { status } 端点测试。"""


def test_patch_status_idle_to_maintenance(client, sample_type_nb_via_api):
    create = client.post("/api/assets", json={
        "name": "X1", "type_id": sample_type_nb_via_api, "custom_data": {},
    })
    asset_id = create.json()["id"]
    resp = client.patch(f"/api/assets/{asset_id}", json={"status": "MAINTENANCE"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "MAINTENANCE"


def test_patch_status_illegal_transition_returns_422(client, sample_type_nb_via_api):
    """直接 RETIRED → IN_USE 是非法转换"""
    create = client.post("/api/assets", json={
        "name": "X1", "type_id": sample_type_nb_via_api, "custom_data": {},
    })
    asset_id = create.json()["id"]
    client.patch(f"/api/assets/{asset_id}", json={"status": "RETIRED"})
    resp = client.patch(f"/api/assets/{asset_id}", json={"status": "IN_USE"})
    assert resp.status_code == 422
    assert "不允许" in resp.json()["detail"]


def test_patch_status_with_other_fields(client, sample_type_nb_via_api):
    """PATCH 同时改 status + holder 等字段也合法"""
    create = client.post("/api/assets", json={
        "name": "X1", "type_id": sample_type_nb_via_api, "custom_data": {},
    })
    asset_id = create.json()["id"]
    resp = client.patch(f"/api/assets/{asset_id}", json={
        "status": "MAINTENANCE",
        "notes": "屏幕进灰",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "MAINTENANCE"
    assert resp.json()["notes"] == "屏幕进灰"
