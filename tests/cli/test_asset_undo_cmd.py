import json

import pytest
from typer.testing import CliRunner

from asset_hub.cli.main import app

runner = CliRunner()


@pytest.fixture
def idle_asset_id(isolated_db):
    """创建一个 IDLE 资产，返回 UUID 字符串。"""
    res = runner.invoke(
        app,
        ["type", "define", "--name", "笔记本", "--prefix", "NB", "--json"],
    )
    assert res.exit_code == 0, res.stdout
    type_id = json.loads(res.stdout)["data"]["id"]

    res = runner.invoke(
        app,
        ["asset", "register", "--name", "测试机", "--type-id", type_id, "--json"],
    )
    assert res.exit_code == 0, res.stdout
    return json.loads(res.stdout)["data"]["id"]


@pytest.fixture
def asset_with_one_checkout(idle_asset_id):
    res = runner.invoke(
        app,
        ["asset", "checkout", idle_asset_id, "--to-holder", "张三", "--json"],
    )
    assert res.exit_code == 0, res.stdout
    return idle_asset_id


def test_undo_success_returns_transition_envelope(asset_with_one_checkout):
    res = runner.invoke(app, ["asset", "undo", asset_with_one_checkout, "--json"])
    assert res.exit_code == 0, res.stdout
    body = json.loads(res.stdout)
    assert body["success"] is True
    assert body["data"]["kind"] == "CHECKOUT_INTERNAL"
    assert body["data"]["to_holder"] == "张三"

    # 验证副作用：asset 已回 IDLE
    show = runner.invoke(app, ["asset", "show", asset_with_one_checkout, "--json"])
    assert json.loads(show.stdout)["data"]["status"] == "IDLE"


def test_undo_dry_run_returns_preview_envelope_exit_10(asset_with_one_checkout):
    res = runner.invoke(
        app,
        ["asset", "undo", asset_with_one_checkout, "--dry-run", "--json"],
    )
    assert res.exit_code == 10, res.stdout
    body = json.loads(res.stdout)
    assert body["success"] is True
    assert "would_undo" in body["data"]
    assert "would_restore" in body["data"]
    assert body["data"]["would_undo"]["kind"] == "CHECKOUT_INTERNAL"
    assert body["data"]["would_restore"]["status"] == "IDLE"

    # 验证 dry-run 不改 DB：还能再 undo
    res2 = runner.invoke(app, ["asset", "undo", asset_with_one_checkout, "--json"])
    assert res2.exit_code == 0


def test_undo_invalid_uuid_exit_2(isolated_db):
    res = runner.invoke(app, ["asset", "undo", "not-a-uuid", "--json"])
    assert res.exit_code == 2, res.stdout
    body = json.loads(res.stdout)
    assert body["success"] is False
    assert body["error"]["code"] == "validation"


def test_undo_nonexistent_asset_exit_3(isolated_db):
    res = runner.invoke(
        app,
        [
            "asset",
            "undo",
            "00000000-0000-0000-0000-000000000000",
            "--json",
        ],
    )
    assert res.exit_code == 3, res.stdout
    body = json.loads(res.stdout)
    assert body["success"] is False
    assert body["error"]["code"] == "not_found"


def test_undo_no_transitions_state_conflict_exit_1(idle_asset_id):
    res = runner.invoke(app, ["asset", "undo", idle_asset_id, "--json"])
    assert res.exit_code == 1, res.stdout
    body = json.loads(res.stdout)
    assert body["success"] is False
    assert body["error"]["code"] == "state_conflict"
    assert body["error"]["hint"]  # 非空


def test_undo_fields_filter_applies(asset_with_one_checkout):
    res = runner.invoke(
        app,
        [
            "asset",
            "undo",
            asset_with_one_checkout,
            "--fields",
            "kind,to_holder",
            "--json",
        ],
    )
    assert res.exit_code == 0, res.stdout
    body = json.loads(res.stdout)
    assert set(body["data"].keys()) == {"kind", "to_holder"}
    assert body["data"]["kind"] == "CHECKOUT_INTERNAL"
