import uuid


def test_undo_reverts_last_transition(client, idle_asset):
    """checkout 后 undo → asset 回 IDLE，holder 清空，流转记录清零。"""
    aid = idle_asset["id"]
    # 先 checkout（IDLE → IN_USE）
    r = client.post(
        f"/api/assets/{aid}/transitions",
        json={"kind": "CHECKOUT_INTERNAL", "to_holder": "张三"},
    )
    assert r.status_code == 201

    # undo
    r = client.post(f"/api/assets/{aid}/transitions/undo")
    assert r.status_code == 200
    body = r.json()
    assert body["kind"] == "CHECKOUT_INTERNAL"  # 返回被撤销的那条

    # asset 回到 IDLE / holder 清空
    a = client.get(f"/api/assets/{aid}").json()
    assert a["status"] == "IDLE"
    assert a["holder"] is None

    # 流转记录清零
    lst = client.get(f"/api/assets/{aid}/transitions").json()
    assert lst == []


def test_undo_no_transition_returns_409(client, idle_asset):
    """无流转记录的 asset undo → StateError → 409。"""
    aid = idle_asset["id"]
    r = client.post(f"/api/assets/{aid}/transitions/undo")
    assert r.status_code == 409
    assert r.json()["code"] == "state_conflict"


def test_undo_nonexistent_asset_returns_404(client):
    r = client.post(f"/api/assets/{uuid.uuid4()}/transitions/undo")
    assert r.status_code == 404
