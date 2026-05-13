"""v2.0 spec §4.4 API ?fields= 字段掩码集成测。

覆盖 4 个 endpoint：
- GET /api/assets/{id}      (show)
- GET /api/assets           (list)
- POST /api/assets/{id}/transitions  (create)
- GET /api/assets/{id}/transitions   (list)

未知字段 → 422 + fields_invalid + hint（envelope handler 已自动序列化）。
"""
from __future__ import annotations


def test_asset_show_fields_mask(client, idle_asset):
    """GET /api/assets/{id}?fields=id,name → 仅含 id / name。"""
    r = client.get(f"/api/assets/{idle_asset['id']}?fields=id,name")
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"id", "name"}


def test_asset_show_unknown_field_422(client, idle_asset):
    """未知字段 → 422 validation error + fields_invalid 列含字段名。"""
    r = client.get(f"/api/assets/{idle_asset['id']}?fields=id,foobar,name")
    assert r.status_code == 422
    body = r.json()
    assert body["code"] == "validation"
    # fields_invalid 含 foobar；hint 给合法字段集
    assert "foobar" in body["fields_invalid"]
    assert body["hint"]


def test_asset_list_fields_mask(client, idle_asset):
    """GET /api/assets?fields=id,name → 数组每项 dict 仅含 id / name。"""
    r = client.get("/api/assets?fields=id,name")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    assert len(body) >= 1  # 至少有 idle_asset
    for row in body:
        assert set(row.keys()) == {"id", "name"}


def test_transition_create_fields_mask(client, idle_asset):
    """POST /api/assets/{id}/transitions?fields=id,kind → response 仅含 id / kind。"""
    r = client.post(
        f"/api/assets/{idle_asset['id']}/transitions?fields=id,kind",
        json={"kind": "CHECKOUT_INTERNAL", "to_holder": "张三"},
    )
    assert r.status_code == 201
    body = r.json()
    assert set(body.keys()) == {"id", "kind"}


def test_transition_list_fields_mask(client, idle_asset):
    """GET /api/assets/{id}/transitions?fields=id,kind → list[dict] 仅含 id / kind。"""
    # 先创建一个 transition 让 list 不空
    r0 = client.post(
        f"/api/assets/{idle_asset['id']}/transitions",
        json={"kind": "CHECKOUT_INTERNAL", "to_holder": "张三"},
    )
    assert r0.status_code == 201

    r = client.get(f"/api/assets/{idle_asset['id']}/transitions?fields=id,kind")
    assert r.status_code == 200
    body = r.json()
    assert len(body) >= 1
    for row in body:
        assert set(row.keys()) == {"id", "kind"}


def test_no_fields_returns_full_payload(client, idle_asset):
    """无 fields query → response_model 默认全字段（OpenAPI schema 不变）。"""
    r = client.get(f"/api/assets/{idle_asset['id']}")
    assert r.status_code == 200
    body = r.json()
    # AssetRead 核心字段全在
    assert {"id", "asset_code", "name", "status", "type_id", "type_name"} <= set(
        body.keys()
    )
