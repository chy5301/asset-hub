def test_get_stats_default_returns_all_4_sections(client, populated_db):
    res = client.get("/api/stats")
    assert res.status_code == 200
    body = res.json()
    assert "type_distribution" in body
    assert "status_distribution" in body
    assert "holder_ranking" in body
    assert "idle_top" in body
    assert "summary" in body


def test_get_stats_summary_fields_complete(client, populated_db):
    res = client.get("/api/stats")
    summary = res.json()["summary"]
    assert "total_assets" in summary
    assert "registered_assets" in summary
    assert "idle_count" in summary
    assert summary["include_retired"] is False
    assert summary["include_disposed"] is False
    assert "generated_at" in summary


def test_get_stats_fields_idle_top_only(client, populated_db):
    res = client.get("/api/stats?fields=idle_top")
    assert res.status_code == 200
    body = res.json()
    assert body.get("idle_top") is not None
    assert body.get("type_distribution") is None
    assert body.get("status_distribution") is None
    assert body.get("holder_ranking") is None
    assert body["summary"] is not None


def test_get_stats_fields_multiple(client, populated_db):
    res = client.get("/api/stats?fields=idle_top,status_distribution")
    body = res.json()
    assert body.get("idle_top") is not None
    assert body.get("status_distribution") is not None
    assert body.get("type_distribution") is None


def test_get_stats_fields_unknown_returns_422(client):
    res = client.get("/api/stats?fields=foo")
    assert res.status_code == 422


def test_get_stats_fields_includes_unknown_returns_422(client):
    res = client.get("/api/stats?fields=idle_top,foo")
    assert res.status_code == 422


def test_get_stats_include_retired_passes_to_summary(client, populated_db):
    res = client.get("/api/stats?include_retired=true")
    body = res.json()
    assert body["summary"]["include_retired"] is True


def test_get_stats_invalid_bool_returns_422(client):
    res = client.get("/api/stats?include_retired=maybe")
    assert res.status_code == 422


def test_stats_endpoint_returns_idle_top_with_name(client, populated_db):
    """GET /api/stats idle_top 数组每项应含 name 字段。"""
    res = client.get("/api/stats?fields=idle_top")
    assert res.status_code == 200
    data = res.json()
    assert "idle_top" in data
    assert data["idle_top"] is not None
    assert len(data["idle_top"]) > 0
    for item in data["idle_top"]:
        assert "name" in item, f"idle_top item 缺 name 字段: {item}"
        assert isinstance(item["name"], str)
