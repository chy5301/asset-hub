import json

import pytest
from typer.testing import CliRunner

from asset_hub.cli.main import app

runner = CliRunner()


@pytest.fixture
def idle_asset_id(isolated_db):
    """通过 CLI 创建一个 IDLE 资产，返回 id。"""
    res = runner.invoke(app, [
        "type", "define", "--name", "笔记本", "--prefix", "NB", "--json",
    ])
    assert res.exit_code == 0, res.stdout
    type_id = json.loads(res.stdout)["data"]["id"]

    res = runner.invoke(app, [
        "asset", "register",
        "--name", "测试机",
        "--type-id", type_id,
        "--json",
    ])
    assert res.exit_code == 0, res.stdout
    return json.loads(res.stdout)["data"]["id"]


def test_checkout_internal_default_kind(idle_asset_id):
    res = runner.invoke(app, [
        "asset", "checkout", idle_asset_id,
        "--to", "张三", "--json",
    ])
    assert res.exit_code == 0, res.stdout
    body = json.loads(res.stdout)
    assert body["success"] is True
    assert body["data"]["kind"] == "CHECKOUT_INTERNAL"
    assert body["data"]["to_holder"] == "张三"


def test_checkout_external_with_kind_flag(idle_asset_id):
    res = runner.invoke(app, [
        "asset", "checkout", idle_asset_id,
        "--to", "客户A", "--kind", "external", "--json",
    ])
    assert res.exit_code == 0, res.stdout
    assert json.loads(res.stdout)["data"]["kind"] == "CHECKOUT_EXTERNAL"


def test_checkout_invalid_kind_returns_error(idle_asset_id):
    res = runner.invoke(app, [
        "asset", "checkout", idle_asset_id,
        "--to", "X", "--kind", "weird", "--json",
    ])
    assert res.exit_code != 0


def test_return_after_checkout(idle_asset_id):
    runner.invoke(app, ["asset", "checkout", idle_asset_id, "--to", "X", "--json"])
    res = runner.invoke(app, [
        "asset", "return", idle_asset_id,
        "--receiver", "仓管", "--json",
    ])
    assert res.exit_code == 0, res.stdout
    body = json.loads(res.stdout)
    assert body["data"]["kind"] == "RETURN"
    assert body["data"]["to_holder"] == "仓管"


def test_return_without_open_checkout_exits_1(idle_asset_id):
    res = runner.invoke(app, [
        "asset", "return", idle_asset_id, "--json",
    ])
    assert res.exit_code == 1
    body = json.loads(res.stdout)
    assert body["success"] is False


def test_send_to_maintenance(idle_asset_id):
    res = runner.invoke(app, [
        "asset", "send-to-maintenance", idle_asset_id, "--json",
    ])
    assert res.exit_code == 0, res.stdout
    assert json.loads(res.stdout)["data"]["to_status"] == "MAINTENANCE"


def test_recover_after_maintenance(idle_asset_id):
    runner.invoke(app, ["asset", "send-to-maintenance", idle_asset_id, "--json"])
    res = runner.invoke(app, ["asset", "recover", idle_asset_id, "--json"])
    assert res.exit_code == 0, res.stdout
    assert json.loads(res.stdout)["data"]["to_status"] == "IDLE"


def test_retire_with_yes(idle_asset_id):
    res = runner.invoke(app, [
        "asset", "retire", idle_asset_id, "--yes", "--json",
    ])
    assert res.exit_code == 0, res.stdout
    assert json.loads(res.stdout)["data"]["to_status"] == "RETIRED"


def test_retire_dry_run_does_not_change_status(idle_asset_id):
    res = runner.invoke(app, [
        "asset", "retire", idle_asset_id, "--dry-run", "--json",
    ])
    assert res.exit_code == 10
    res2 = runner.invoke(app, ["asset", "show", idle_asset_id, "--json"])
    assert json.loads(res2.stdout)["data"]["status"] == "IDLE"


def test_reinstate_after_retire(idle_asset_id):
    runner.invoke(app, ["asset", "retire", idle_asset_id, "--yes", "--json"])
    res = runner.invoke(app, ["asset", "reinstate", idle_asset_id, "--json"])
    assert res.exit_code == 0, res.stdout
    assert json.loads(res.stdout)["data"]["to_status"] == "IDLE"


def test_dispose_from_retired_with_yes(idle_asset_id):
    runner.invoke(app, ["asset", "retire", idle_asset_id, "--yes", "--json"])
    res = runner.invoke(app, [
        "asset", "dispose", idle_asset_id, "--yes", "--json",
    ])
    assert res.exit_code == 0, res.stdout
    body = json.loads(res.stdout)
    assert body["data"]["to_status"] == "DISPOSED"
    assert body["data"]["to_holder"] is None
    assert body["data"]["to_location"] is None


def test_dispose_from_idle_exits_1(idle_asset_id):
    res = runner.invoke(app, [
        "asset", "dispose", idle_asset_id, "--yes", "--json",
    ])
    assert res.exit_code == 1


def test_relocate(idle_asset_id):
    res = runner.invoke(app, [
        "asset", "relocate", idle_asset_id,
        "--to-location", "新仓库", "--json",
    ])
    assert res.exit_code == 0, res.stdout
    body = json.loads(res.stdout)
    assert body["data"]["kind"] == "RELOCATE"
    assert body["data"]["to_location"] == "新仓库"


def test_transfer_holder(idle_asset_id):
    res = runner.invoke(app, [
        "asset", "transfer-holder", idle_asset_id,
        "--to-holder", "李四", "--json",
    ])
    assert res.exit_code == 0, res.stdout
    body = json.loads(res.stdout)
    assert body["data"]["kind"] == "TRANSFER_HOLDER"
    assert body["data"]["to_holder"] == "李四"


def test_history_after_multiple_transitions(idle_asset_id):
    runner.invoke(app, ["asset", "checkout", idle_asset_id, "--to", "X", "--json"])
    runner.invoke(app, ["asset", "return", idle_asset_id, "--json"])
    res = runner.invoke(app, ["asset", "history", idle_asset_id, "--json"])
    assert res.exit_code == 0, res.stdout
    body = json.loads(res.stdout)
    assert body["metadata"]["count"] == 2


def test_change_status_command_removed(idle_asset_id):
    """change-status 命令在 M3a 已删除。"""
    res = runner.invoke(app, [
        "asset", "change-status", idle_asset_id, "--to", "MAINTENANCE",
    ])
    assert res.exit_code != 0
