import json
from uuid import uuid4

from typer.testing import CliRunner

from asset_hub.cli.main import app

runner = CliRunner()


def _define_type_and_asset() -> tuple[str, str]:
    r = runner.invoke(app, ["type", "define", "--name", "笔记本", "--json"])
    type_id = json.loads(r.stdout)["data"]["id"]
    r = runner.invoke(app, [
        "asset", "register", "--name", "X1", "--type-id", type_id, "--json",
    ])
    asset_id = json.loads(r.stdout)["data"]["id"]
    return type_id, asset_id


class TestAssetCheckout:
    def test_checkout_idle_asset(self):
        _, asset_id = _define_type_and_asset()
        result = runner.invoke(app, [
            "asset", "checkout", asset_id,
            "--to", "张三",
            "--location", "工位 5",
            "--note", "借用一周",
            "--json",
        ])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert data["data"]["holder"] == "张三"
        assert data["data"]["location"] == "工位 5"
        assert data["data"]["checkout_note"] == "借用一周"
        assert data["data"]["returned_at"] is None

        r = runner.invoke(app, ["asset", "show", asset_id, "--json"])
        shown = json.loads(r.stdout)["data"]
        assert shown["status"] == "IN_USE"
        assert shown["holder"] == "张三"

    def test_checkout_nonexistent_exits_3(self):
        result = runner.invoke(app, [
            "asset", "checkout", str(uuid4()),
            "--to", "张三", "--json",
        ])
        assert result.exit_code == 3

    def test_checkout_already_in_use_exits_1(self):
        _, asset_id = _define_type_and_asset()
        runner.invoke(app, [
            "asset", "checkout", asset_id, "--to", "张三", "--json",
        ])
        result = runner.invoke(app, [
            "asset", "checkout", asset_id, "--to", "李四", "--json",
        ])
        assert result.exit_code == 1
        data = json.loads(result.stdout)
        assert data["success"] is False
        assert "已派发" in data["error"]

    def test_checkout_bad_uuid_exits_2(self):
        result = runner.invoke(app, [
            "asset", "checkout", "not-a-uuid",
            "--to", "张三", "--json",
        ])
        assert result.exit_code == 2
