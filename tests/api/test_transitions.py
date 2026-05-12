import uuid


def test_send_to_maintenance_no_holder_keeps_current(client, sample_type_nb_via_api):
    """v2.0：POST transitions 不传 to_holder（字段不在 JSON 中）→ keep current。"""
    # 直接创建 IDLE 资产并设置 holder="张三"
    resp = client.post(
        "/api/assets",
        json={"name": "待送修笔记本", "type_id": sample_type_nb_via_api, "holder": "张三", "custom_data": {}},
    )
    assert resp.status_code == 201
    aid = resp.json()["id"]

    # SEND_TO_MAINTENANCE，不传 to_holder 字段
    r = client.post(f"/api/assets/{aid}/transitions", json={"kind": "SEND_TO_MAINTENANCE"})
    assert r.status_code == 201
    body = r.json()
    assert body["to_holder"] == "张三"  # keep rule 保留
    assert body["to_status"] == "MAINTENANCE"


def test_send_to_maintenance_explicit_null_clears(client, sample_type_nb_via_api):
    """v2.0：传 to_holder=null（字段在 JSON 中显式为 null）→ 清空。"""
    resp = client.post(
        "/api/assets",
        json={"name": "待送修笔记本2", "type_id": sample_type_nb_via_api, "holder": "张三", "custom_data": {}},
    )
    assert resp.status_code == 201
    aid = resp.json()["id"]

    r = client.post(
        f"/api/assets/{aid}/transitions",
        json={"kind": "SEND_TO_MAINTENANCE", "to_holder": None},  # explicit null
    )
    assert r.status_code == 201
    assert r.json()["to_holder"] is None


def test_relocate_kind_rejected(client, idle_asset):
    """v1 RELOCATE 已删，TransitionKind enum 不含，应 422 Pydantic validation。"""
    aid = idle_asset["id"]
    r = client.post(
        f"/api/assets/{aid}/transitions",
        json={"kind": "RELOCATE", "to_location": "L2"},
    )
    assert r.status_code == 422


def test_reassign_at_least_one_change(client, idle_asset):
    """REASSIGN 不传任何字段 → service 抛 IllegalTransitionError → 409。"""
    aid = idle_asset["id"]
    # idle_asset 默认 holder=None
    # REASSIGN 必须改一项，但 holder/location 都 None 且不传 → no-op → 409
    r = client.post(f"/api/assets/{aid}/transitions", json={"kind": "REASSIGN"})
    assert r.status_code == 409
    assert "至少一项" in r.json()["detail"]


def test_post_transition_checkout_internal(client, idle_asset):
    resp = client.post(
        f"/api/assets/{idle_asset['id']}/transitions",
        json={"kind": "CHECKOUT_INTERNAL", "to_holder": "张三", "to_location": "1F"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["kind"] == "CHECKOUT_INTERNAL"
    assert body["from_status"] == "IDLE"
    assert body["to_status"] == "IN_USE"
    assert body["to_holder"] == "张三"


def test_post_transition_illegal_returns_409(client, idle_asset):
    resp = client.post(
        f"/api/assets/{idle_asset['id']}/transitions",
        json={"kind": "DISPOSE"},
    )
    assert resp.status_code == 409
    assert "不能从" in resp.json()["detail"]


def test_post_transition_required_field_missing_returns_409(client, idle_asset):
    resp = client.post(
        f"/api/assets/{idle_asset['id']}/transitions",
        json={"kind": "CHECKOUT_INTERNAL"},
    )
    assert resp.status_code == 409
    assert "to_holder" in resp.json()["detail"]


def test_post_transition_404_when_asset_missing(client):
    resp = client.post(
        f"/api/assets/{uuid.uuid4()}/transitions",
        json={"kind": "CHECKOUT_INTERNAL", "to_holder": "X"},
    )
    assert resp.status_code == 404


def test_get_transitions_returns_desc_order(client, idle_asset):
    client.post(f"/api/assets/{idle_asset['id']}/transitions", json={"kind": "CHECKOUT_INTERNAL", "to_holder": "X"})
    client.post(f"/api/assets/{idle_asset['id']}/transitions", json={"kind": "RETURN", "to_holder": "Y"})

    resp = client.get(f"/api/assets/{idle_asset['id']}/transitions")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 2
    assert rows[0]["kind"] == "RETURN"
    assert rows[1]["kind"] == "CHECKOUT_INTERNAL"


def test_get_transitions_404_when_asset_missing(client):
    resp = client.get(f"/api/assets/{uuid.uuid4()}/transitions")
    assert resp.status_code == 404


def test_list_assets_default_excludes_retired_and_disposed(client, idle_asset, retired_asset, disposed_asset):
    resp = client.get("/api/assets")
    assert resp.status_code == 200
    statuses = [a["status"] for a in resp.json()]
    assert "IDLE" in statuses
    assert "RETIRED" not in statuses
    assert "DISPOSED" not in statuses


def test_list_assets_include_retired(client, idle_asset, retired_asset):
    resp = client.get("/api/assets?include_retired=true")
    assert resp.status_code == 200
    statuses = [a["status"] for a in resp.json()]
    assert "RETIRED" in statuses


def test_list_assets_include_disposed(client, idle_asset, disposed_asset):
    resp = client.get("/api/assets?include_disposed=true")
    assert resp.status_code == 200
    statuses = [a["status"] for a in resp.json()]
    assert "DISPOSED" in statuses
