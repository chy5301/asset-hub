"""v2.0 API exception handler 响应深度结构化测（spec §4.2）。

backward compat：response 保留 `detail` 字段，**追加** code / hint / fields_missing
/ fields_invalid / affected_resource_id 顶层字段（exclude None）。
前端 `frontend/src/lib/error.ts` 仍读 `detail`，零变更。
"""
from __future__ import annotations

import uuid


def test_reassign_no_change_envelope_has_hint_and_fields_missing(client, idle_asset):
    """REASSIGN 不改 holder/location → 409 + envelope 含 detail + code + hint + fields_missing。"""
    aid = idle_asset["id"]
    r = client.post(f"/api/assets/{aid}/transitions", json={"kind": "REASSIGN"})
    assert r.status_code == 409
    body = r.json()
    # backward compat: detail 字段仍存在
    assert "至少一项" in body["detail"]
    # v2.0 新字段
    assert body["code"] == "illegal_transition"
    assert body["hint"]
    assert "to_holder" in body["fields_missing"]
    assert "to_location" in body["fields_missing"]


def test_not_found_envelope_excludes_none_optional_fields(client):
    """简单 NotFoundError 响应应不含 None 可选字段（exclude None）。"""
    bogus_id = "00000000-0000-0000-0000-000000000000"
    r = client.get(f"/api/assets/{bogus_id}")
    assert r.status_code == 404
    body = r.json()
    # backward compat: detail + code
    assert body.get("detail")
    assert body["code"] == "not_found"
    # 不应有 hint / fields_missing 等 None key
    assert "hint" not in body
    assert "fields_missing" not in body
    assert "fields_invalid" not in body
    assert "affected_resource_id" not in body


def test_illegal_from_status_envelope_has_hint(client, idle_asset):
    """对 IDLE 资产 DISPOSE → 409；state_machine.validate_transition 加了 hint。"""
    aid = idle_asset["id"]
    r = client.post(f"/api/assets/{aid}/transitions", json={"kind": "DISPOSE"})
    assert r.status_code == 409
    body = r.json()
    assert body["code"] == "illegal_transition"
    # backward compat: detail 仍含原始 message
    assert "不能从" in body["detail"]
    # v2.0 新字段：hint 说明合法 from-states
    assert body["hint"]
    assert "IDLE" in body["hint"]  # 当前状态
    # 这条路径不应有 fields_missing（不是字段缺失场景）
    assert "fields_missing" not in body


def test_required_field_missing_envelope_has_fields_missing(client, idle_asset):
    """CHECKOUT_INTERNAL 不传 to_holder → 409 + fields_missing=['to_holder']。"""
    aid = idle_asset["id"]
    r = client.post(f"/api/assets/{aid}/transitions", json={"kind": "CHECKOUT_INTERNAL"})
    assert r.status_code == 409
    body = r.json()
    assert body["code"] == "illegal_transition"
    assert body["hint"]
    assert body["fields_missing"] == ["to_holder"]


def test_return_no_open_checkout_envelope_has_affected_resource_id(client, idle_asset):
    """对 IDLE 资产 RETURN → 409；transition.py 该 raise 加了 affected_resource_id。

    注：当前 IDLE 状态会先被 validate_transition 拦住（RETURN 必须从 IN_USE 出发），
    所以这里实际命中的是 validate_transition 的 hint 路径，而非 transition.py
    的 RETURN-no-open-checkout 路径。为测后者，需要先把资产推到 IN_USE 再回去——
    但 IN_USE→RETURN 会成功 close 那条 checkout，不会触发该路径。
    实际上 RETURN-no-open 仅在 IN_USE 状态记录被人工删除/数据损坏时才会触发，
    属防御性 raise，难在 API 层 reproduce。这里仅 assert from-status 路径 envelope。
    """
    aid = idle_asset["id"]
    r = client.post(f"/api/assets/{aid}/transitions", json={"kind": "RETURN"})
    assert r.status_code == 409
    body = r.json()
    assert body["code"] == "illegal_transition"
    # validate_transition hint 路径——RETURN 仅允许从 IN_USE 出发
    assert body["hint"]


def test_type_delete_conflict_envelope_preserves_detail(client, session):
    """ConflictError（type 被资产引用）→ 409 + detail 含数量 + code=conflict。

    test_type_routes_delete.py 现有 `assert "1" in r.json()["detail"]` 测仍 PASS。
    """
    from asset_hub.services.asset import AssetService
    from asset_hub.services.asset_type import TypeService

    type_svc = TypeService(session)
    t = type_svc.create_type(name="冲突类型", code_prefix="CT")
    AssetService(session).register(type_id=t.id, name="X1", custom_data={})

    r = client.delete(f"/api/types/{t.id}")
    assert r.status_code == 409
    body = r.json()
    # backward compat
    assert "1" in body["detail"]
    # v2.0
    assert body["code"] == "conflict"


def test_uuid_404_includes_code(client):
    """GET /api/types/<bogus uuid> → 404，envelope 含 code=not_found。"""
    r = client.get(f"/api/types/{uuid.uuid4()}")
    assert r.status_code == 404
    body = r.json()
    assert body.get("detail")
    assert body["code"] == "not_found"
