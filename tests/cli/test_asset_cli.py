import json

from typer.testing import CliRunner

from asset_hub.cli.main import app

runner = CliRunner()


def _define_type(name: str = "笔记本电脑", code_prefix: str = "NB", fields: list | None = None) -> str:
    """Helper: 创建类型并返回 type_id"""
    args = ["type", "define", "--name", name, "--prefix", code_prefix, "--json"]
    if fields:
        args += ["--fields", json.dumps(fields, ensure_ascii=False)]
    r = runner.invoke(app, args)
    return json.loads(r.stdout)["data"]["id"]


class TestAssetRegister:
    def test_register_minimal(self):
        type_id = _define_type()
        result = runner.invoke(app, [
            "asset", "register",
            "--name", "ThinkPad X1",
            "--type-id", type_id,
            "--json",
        ])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert data["data"]["name"] == "ThinkPad X1"
        assert data["data"]["status"] == "IDLE"

    def test_register_with_custom_data(self):
        type_id = _define_type(
            fields=[{"key": "brand", "label": "品牌", "type": "string", "required": True}]
        )
        result = runner.invoke(app, [
            "asset", "register",
            "--name", "ThinkPad X1",
            "--type-id", type_id,
            "--custom", '{"brand": "Lenovo"}',
            "--json",
        ])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["data"]["custom_data"]["brand"] == "Lenovo"

    def test_register_bad_type_exits_3(self):
        from uuid import uuid4
        result = runner.invoke(app, [
            "asset", "register",
            "--name", "X",
            "--type-id", str(uuid4()),
            "--json",
        ])
        assert result.exit_code == 3


class TestAssetRegisterAcquiredAt:
    def test_register_with_acquired_at(self):
        type_id = _define_type()
        result = runner.invoke(app, [
            "asset", "register",
            "--name", "X1",
            "--type-id", type_id,
            "--acquired-at", "2025-01-15",
            "--json",
        ])
        assert result.exit_code == 0
        body = json.loads(result.stdout)
        assert body["success"] is True
        assert body["data"]["acquired_at"] == "2025-01-15"
        assert body["data"]["asset_code"].startswith("NB-")


class TestAssetChangeStatus:
    def test_change_status_to_maintenance(self):
        type_id = _define_type()
        create = runner.invoke(app, [
            "asset", "register",
            "--name", "X1", "--type-id", type_id,
            "--json",
        ])
        asset_id = json.loads(create.stdout)["data"]["id"]

        resp = runner.invoke(app, [
            "asset", "change-status", asset_id,
            "--to", "MAINTENANCE",
            "--json",
        ])
        assert resp.exit_code == 0
        assert json.loads(resp.stdout)["data"]["status"] == "MAINTENANCE"

    def test_change_status_illegal_returns_exit_1(self):
        type_id = _define_type()
        create = runner.invoke(app, [
            "asset", "register",
            "--name", "X1", "--type-id", type_id,
            "--json",
        ])
        asset_id = json.loads(create.stdout)["data"]["id"]
        runner.invoke(app, ["asset", "change-status", asset_id, "--to", "RETIRED", "--json"])
        resp = runner.invoke(app, ["asset", "change-status", asset_id, "--to", "IN_USE", "--json"])
        assert resp.exit_code == 1
        body = json.loads(resp.stdout)
        assert body["success"] is False
        assert "不允许" in body["error"]


class TestAssetList:
    def test_list_empty(self):
        result = runner.invoke(app, ["asset", "list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["data"] == []

    def test_list_with_filter(self):
        type_id = _define_type()
        runner.invoke(app, ["asset", "register", "--name", "A", "--type-id", type_id])
        runner.invoke(app, ["asset", "register", "--name", "B", "--type-id", type_id])
        result = runner.invoke(app, ["asset", "list", "--json"])
        data = json.loads(result.stdout)
        assert data["metadata"]["count"] == 2


class TestAssetShow:
    def test_show_existing(self):
        type_id = _define_type()
        r = runner.invoke(app, [
            "asset", "register", "--name", "X1", "--type-id", type_id, "--json",
        ])
        asset_id = json.loads(r.stdout)["data"]["id"]
        result = runner.invoke(app, ["asset", "show", asset_id, "--json"])
        assert result.exit_code == 0
        assert json.loads(result.stdout)["data"]["name"] == "X1"

    def test_show_nonexistent_exits_3(self):
        from uuid import uuid4
        result = runner.invoke(app, ["asset", "show", str(uuid4()), "--json"])
        assert result.exit_code == 3


class TestAssetUpdate:
    def test_update_holder(self):
        type_id = _define_type()
        r = runner.invoke(app, [
            "asset", "register", "--name", "X1", "--type-id", type_id, "--json",
        ])
        asset_id = json.loads(r.stdout)["data"]["id"]
        result = runner.invoke(app, [
            "asset", "update", asset_id,
            "--set", '{"holder": "张三"}',
            "--json",
        ])
        assert result.exit_code == 0
        assert json.loads(result.stdout)["data"]["holder"] == "张三"


class TestAssetDelete:
    def test_delete_existing(self):
        type_id = _define_type()
        r = runner.invoke(app, [
            "asset", "register", "--name", "X1", "--type-id", type_id, "--json",
        ])
        asset_id = json.loads(r.stdout)["data"]["id"]
        result = runner.invoke(app, ["asset", "delete", asset_id, "--yes", "--json"])
        assert result.exit_code == 0

    def test_delete_dry_run_exits_10(self):
        type_id = _define_type()
        r = runner.invoke(app, [
            "asset", "register", "--name", "X1", "--type-id", type_id, "--json",
        ])
        asset_id = json.loads(r.stdout)["data"]["id"]
        result = runner.invoke(app, ["asset", "delete", asset_id, "--dry-run", "--json"])
        assert result.exit_code == 10
        # 验证资产仍然存在
        check = runner.invoke(app, ["asset", "show", asset_id, "--json"])
        assert check.exit_code == 0
