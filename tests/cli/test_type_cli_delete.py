import json
import uuid

import pytest
from typer.testing import CliRunner

from asset_hub.cli.deps import cli_session
from asset_hub.cli.main import app
from asset_hub.errors import NotFoundError
from asset_hub.services.asset import AssetService
from asset_hub.services.asset_type import TypeService

runner = CliRunner()


def test_type_delete_dry_run_no_db_change(isolated_db):
    with cli_session() as s:
        t = TypeService(s).create_type(name="CLI-DR", code_prefix="DR")
        type_id = t.id

    res = runner.invoke(app, ["type", "delete", str(type_id), "--dry-run", "--json"])
    assert res.exit_code == 10  # dry-run 预览
    payload = json.loads(res.stdout)
    assert payload["success"] is True

    # 数据库内 type 仍存在
    with cli_session() as s:
        assert TypeService(s).get_type(type_id) is not None


def test_type_delete_no_refs_succeeds(isolated_db):
    with cli_session() as s:
        t = TypeService(s).create_type(name="CLI-OK", code_prefix="OK")
        type_id = t.id

    res = runner.invoke(app, ["type", "delete", str(type_id), "--yes", "--json"])
    assert res.exit_code == 0

    with cli_session() as s, pytest.raises(NotFoundError):
        TypeService(s).get_type(type_id)


def test_type_delete_with_refs_returns_exit_1(isolated_db):
    with cli_session() as s:
        t = TypeService(s).create_type(name="CLI-CF", code_prefix="CF")
        AssetService(s).register(type_id=t.id, name="A1", custom_data={})
        type_id = t.id

    res = runner.invoke(app, ["type", "delete", str(type_id), "--yes", "--json"])
    assert res.exit_code == 1
    payload = json.loads(res.stdout)
    assert payload["success"] is False
    # error envelope: M3e 起统一为 {code, message} dict — 见 envelope.py error_envelope
    assert payload["error"]["code"] == "conflict"
    assert "引用" in payload["error"]["message"]


def test_type_delete_not_found_returns_exit_3(isolated_db):
    res = runner.invoke(app, ["type", "delete", str(uuid.uuid4()), "--yes", "--json"])
    assert res.exit_code == 3


def test_type_delete_interactive_cancel_exit_10(isolated_db):
    """v2.0: interactive cancel of type delete returns exit 10 (与 dry-run 同档信号化).

    回归锁：type_cmd.py:122-123 的 cancel 分支仅在 human TTY 模式（无 --yes、无 --json）
    触发，--json 模式永不进入。这是 src/ 内唯一一处 code='cancelled' 调用点。
    """
    with cli_session() as s:
        t = TypeService(s).create_type(name="CLI-CN", code_prefix="CN")
        type_id = t.id

    # 不带 --yes / --json，stdin 喂 "n" 拒绝确认
    res = runner.invoke(app, ["type", "delete", str(type_id)], input="n\n")

    # 锁：exit_code 10 — v2.0 信号化退出码（与 dry-run 同档），而非通用错误 1
    assert res.exit_code == 10

    # type 仍存在（未真删）
    with cli_session() as s:
        assert TypeService(s).get_type(type_id) is not None


def test_type_delete_dry_run_with_refs_returns_exit_1(isolated_db):
    """dry-run 在有引用时应预报失败而非误报成功。"""
    from asset_hub.cli.deps import cli_session
    from asset_hub.services.asset import AssetService
    from asset_hub.services.asset_type import TypeService

    with cli_session() as session:
        t = TypeService(session).create_type(name="CLI-DR-CF", code_prefix="DC")
        AssetService(session).register(type_id=t.id, name="A1", custom_data={})
        type_id = t.id

    res = runner.invoke(app, ["type", "delete", str(type_id), "--dry-run", "--json"])
    assert res.exit_code == 1
    payload = json.loads(res.stdout)
    assert payload["success"] is False
    assert payload["error"]["code"] == "conflict"
    assert (
        "1" in payload["error"]["message"] and "dry-run" in payload["error"]["message"]
    )

    # type 仍存在（未真删）
    with cli_session() as session:
        assert TypeService(session).get_type(type_id) is not None
