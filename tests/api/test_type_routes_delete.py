def test_delete_type_no_assets_returns_204(client, session):
    from asset_hub.services.asset_type import TypeService

    type_svc = TypeService(session)
    t = type_svc.create_type(name="API-删除", code_prefix="AD")

    resp = client.delete(f"/api/types/{t.id}")
    assert resp.status_code == 204


def test_delete_type_with_assets_returns_409(client, session):
    from asset_hub.services.asset import AssetService
    from asset_hub.services.asset_type import TypeService

    type_svc = TypeService(session)
    t = type_svc.create_type(name="API-冲突", code_prefix="AC")
    AssetService(session).register(type_id=t.id, name="A1", custom_data={})

    resp = client.delete(f"/api/types/{t.id}")
    assert resp.status_code == 409
    assert "1" in resp.json()["detail"]


def test_delete_type_not_found_returns_404(client):
    import uuid

    resp = client.delete(f"/api/types/{uuid.uuid4()}")
    assert resp.status_code == 404
