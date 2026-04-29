def test_return_with_location_and_receiver(client, session):
    from asset_hub.services.asset import AssetService
    from asset_hub.services.asset_type import TypeService
    from asset_hub.services.checkout import CheckoutService

    t = TypeService(session).create_type(name="API-RT", code_prefix="RT")
    a = AssetService(session).register(type_id=t.id, name="A1", custom_data={})
    CheckoutService(session).checkout(a.id, holder="张三")

    resp = client.post(
        f"/api/assets/{a.id}/return",
        json={
            "note": "测试归还",
            "return_location": "仓库C",
            "return_receiver": "管理员丙",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["return_location"] == "仓库C"
    assert body["return_receiver"] == "管理员丙"

    asset_resp = client.get(f"/api/assets/{a.id}")
    assert asset_resp.json()["location"] == "仓库C"


def test_return_without_extra_fields_backward_compat(client, session):
    """保证 v1 早期客户端只传 note 仍工作"""
    from asset_hub.services.asset import AssetService
    from asset_hub.services.asset_type import TypeService
    from asset_hub.services.checkout import CheckoutService

    t = TypeService(session).create_type(name="API-BC", code_prefix="BC")
    a = AssetService(session).register(type_id=t.id, name="A2", custom_data={})
    CheckoutService(session).checkout(a.id, holder="李四")

    resp = client.post(f"/api/assets/{a.id}/return", json={"note": "仅备注"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["return_location"] is None
    assert body["return_receiver"] is None
