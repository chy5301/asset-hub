"""v2.0 spec §4.4 CLI --fields 字段掩码测（T20）。

覆盖 14 命令中代表性子集（list / show / history / checkout / reassign）+
unknown-field validation error + backward compat（不传 --fields → 全字段）。
"""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from asset_hub.cli.main import app

runner = CliRunner()


def _define_type(name: str = "笔记本电脑", prefix: str = "NB") -> str:
    """复用 test_asset_cli.py 风格 helper：返 type_id。"""
    r = runner.invoke(
        app, ["type", "define", "--name", name, "--prefix", prefix, "--json"]
    )
    assert r.exit_code == 0, r.stdout
    return json.loads(r.stdout)["data"]["id"]


@pytest.fixture
def sample_asset(isolated_db):
    """注册一个测试 asset，返回 dict (含 id)。"""
    type_id = _define_type()
    r = runner.invoke(
        app,
        [
            "asset",
            "register",
            "--name",
            "Sample",
            "--type-id",
            type_id,
            "--json",
        ],
    )
    assert r.exit_code == 0, r.stdout
    return json.loads(r.stdout)["data"]


def test_asset_list_fields_mask(sample_asset):
    r = runner.invoke(app, ["asset", "list", "--fields", "id,name", "--json"])
    assert r.exit_code == 0, r.stdout
    body = json.loads(r.stdout)
    assert body["success"] is True
    assert len(body["data"]) >= 1
    for row in body["data"]:
        assert set(row.keys()) == {"id", "name"}


def test_asset_show_fields_mask(sample_asset):
    aid = sample_asset["id"]
    r = runner.invoke(
        app, ["asset", "show", aid, "--fields", "id,status,holder", "--json"]
    )
    assert r.exit_code == 0, r.stdout
    body = json.loads(r.stdout)
    assert set(body["data"].keys()) == {"id", "status", "holder"}


def test_asset_show_unknown_field_validation_error(sample_asset):
    aid = sample_asset["id"]
    r = runner.invoke(app, ["asset", "show", aid, "--fields", "id,foobar", "--json"])
    assert r.exit_code == 1, r.stdout  # validation error
    body = json.loads(r.stdout)
    assert body["success"] is False
    assert body["error"]["code"] == "validation"
    assert "foobar" in body["error"]["fields_invalid"]
    # hint 列出合法字段
    assert body["error"]["hint"]
    assert "id" in body["error"]["hint"]
    assert "name" in body["error"]["hint"]


def test_asset_checkout_fields_mask(sample_asset):
    """transition 写命令的返回也支持 --fields。"""
    aid = sample_asset["id"]
    r = runner.invoke(
        app,
        [
            "asset",
            "checkout",
            aid,
            "--to-holder",
            "张三",
            "--fields",
            "id,kind,to_holder",
            "--json",
        ],
    )
    assert r.exit_code == 0, r.stdout
    body = json.loads(r.stdout)
    assert set(body["data"].keys()) == {"id", "kind", "to_holder"}


def test_asset_reassign_fields_mask(sample_asset):
    """reassign 也支持 --fields。"""
    aid = sample_asset["id"]
    # 先 checkout 让 asset IN_USE 才能 reassign
    co = runner.invoke(
        app,
        [
            "asset",
            "checkout",
            aid,
            "--to-holder",
            "A",
            "--json",
        ],
    )
    assert co.exit_code == 0, co.stdout
    r = runner.invoke(
        app,
        [
            "asset",
            "reassign",
            aid,
            "--to-holder",
            "B",
            "--fields",
            "id,kind,to_holder",
            "--json",
        ],
    )
    assert r.exit_code == 0, r.stdout
    body = json.loads(r.stdout)
    assert set(body["data"].keys()) == {"id", "kind", "to_holder"}


def test_asset_history_fields_mask(sample_asset):
    aid = sample_asset["id"]
    co = runner.invoke(app, ["asset", "checkout", aid, "--to-holder", "X", "--json"])
    assert co.exit_code == 0, co.stdout
    r = runner.invoke(
        app,
        [
            "asset",
            "history",
            aid,
            "--fields",
            "id,kind",
            "--json",
        ],
    )
    assert r.exit_code == 0, r.stdout
    body = json.loads(r.stdout)
    assert len(body["data"]) >= 1
    for row in body["data"]:
        assert set(row.keys()) == {"id", "kind"}


def test_asset_list_no_fields_full_payload(sample_asset):
    """backward compat：不传 --fields → 默认全字段。"""
    r = runner.invoke(app, ["asset", "list", "--json"])
    assert r.exit_code == 0, r.stdout
    body = json.loads(r.stdout)
    assert len(body["data"]) >= 1
    for row in body["data"]:
        # AssetRead 字段全在
        assert {"id", "name", "status", "type_id"} <= set(row.keys())


def test_dry_run_ignores_fields_mask(sample_asset):
    """dry-run + --fields: dry-run preview 不被 filter（contract: dry-run preview 不是 record）。

    防止未来 refactor 把 filter 误移到 dry-run 之前——dry-run 优先短路。
    """
    aid = sample_asset["id"]
    r = runner.invoke(
        app,
        [
            "asset",
            "retire",
            aid,
            "--dry-run",
            "--yes",
            "--fields",
            "id",
            "--json",
        ],
    )
    assert r.exit_code == 10, r.stdout  # dry-run 退出码
    body = json.loads(r.stdout)
    assert body["success"] is True
    # dry-run preview 形状为 {"would_retire": {...AssetRead}}，不是 {"id": "<uuid>"}
    assert body["data"] != {"id": str(aid)}
    assert "would_retire" in body["data"]
    # would_retire 内含完整 AssetRead，未被 fields=id filter 掉
    assert body["data"]["would_retire"]["id"] == str(aid)
    assert "name" in body["data"]["would_retire"]
    assert "status" in body["data"]["would_retire"]
