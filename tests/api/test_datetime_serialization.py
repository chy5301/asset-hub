"""API 层 datetime 字段必须带 tzinfo 序列化（否则前端 parseISO 会按本地时区解析造成时区漂移）。

回归：原本 SQLite 存裸 datetime，FastAPI 序列化时直接吐 ISO 字符串不带 tz designator，
导致前端 date-fns parseISO 把 UTC 时间当本地时间显示（差 8 小时）。
"""

from datetime import datetime


def _assert_tz_aware(value: str, field_path: str) -> None:
    """ISO 字符串必须能用 fromisoformat 解析出 tzinfo（带 Z 或 +HH:MM 后缀）。"""
    assert value is not None, f"{field_path} 为 None"
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None, (
        f"{field_path}={value!r} 缺少时区后缀（应带 Z 或 +HH:MM）"
    )


class TestAssetDatetime:
    def test_asset_create_has_tz(self, client, idle_asset):
        _assert_tz_aware(idle_asset["created_at"], "asset.created_at")
        _assert_tz_aware(idle_asset["updated_at"], "asset.updated_at")

    def test_asset_get_has_tz(self, client, idle_asset):
        resp = client.get(f"/api/assets/{idle_asset['id']}")
        assert resp.status_code == 200
        body = resp.json()
        _assert_tz_aware(body["created_at"], "asset.created_at")
        _assert_tz_aware(body["updated_at"], "asset.updated_at")

    def test_asset_list_has_tz(self, client, idle_asset):
        resp = client.get("/api/assets")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) >= 1
        _assert_tz_aware(items[0]["created_at"], "asset[0].created_at")
        _assert_tz_aware(items[0]["updated_at"], "asset[0].updated_at")


class TestAssetTypeDatetime:
    def test_type_create_has_tz(self, client):
        resp = client.post(
            "/api/types",
            json={"name": "测试类型", "code_prefix": "TT", "custom_fields": []},
        )
        assert resp.status_code == 201
        body = resp.json()
        _assert_tz_aware(body["created_at"], "type.created_at")
        _assert_tz_aware(body["updated_at"], "type.updated_at")

    def test_type_list_has_tz(self, client, sample_type_nb_via_api):
        resp = client.get("/api/types")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) >= 1
        _assert_tz_aware(items[0]["created_at"], "type[0].created_at")


class TestTransitionDatetime:
    def test_transition_create_has_tz(self, client, idle_asset):
        resp = client.post(
            f"/api/assets/{idle_asset['id']}/transitions",
            json={"kind": "CHECKOUT_INTERNAL", "to_holder": "张三"},
        )
        assert resp.status_code == 201
        body = resp.json()
        _assert_tz_aware(body["created_at"], "transition.created_at")

    def test_transition_history_has_tz(self, client, in_use_asset):
        resp = client.get(f"/api/assets/{in_use_asset['id']}/transitions")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) >= 1
        _assert_tz_aware(items[0]["created_at"], "transition[0].created_at")


class TestAttachmentDatetime:
    def test_attachment_upload_has_tz(self, client, idle_asset, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        with f.open("rb") as fp:
            resp = client.post(
                f"/api/assets/{idle_asset['id']}/attachments",
                files={"file": ("test.txt", fp, "text/plain")},
                data={"kind": "doc"},
            )
        assert resp.status_code == 201
        body = resp.json()
        _assert_tz_aware(body["uploaded_at"], "attachment.uploaded_at")


class TestStatsDatetimeRegression:
    """stats.py 已有 validator（已修），作为对照基线确保我们的修复方向与之一致。"""

    def test_stats_summary_has_tz(self, client):
        resp = client.get("/api/stats")
        assert resp.status_code == 200
        body = resp.json()
        _assert_tz_aware(body["summary"]["generated_at"], "stats.summary.generated_at")
