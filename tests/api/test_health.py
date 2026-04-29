def test_healthz_returns_200_and_status_ok(client):
    resp = client.get("/api/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
