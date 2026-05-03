import uuid


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
