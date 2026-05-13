"""--help-json 双模（agent 元数据导出）单元测试。v2.0 spec §4.3。"""

from __future__ import annotations

import json

from typer.testing import CliRunner

from asset_hub.cli.main import app

runner = CliRunner()


def test_asset_list_help_json():
    """asset list --help-json 输出结构化命令元数据。"""
    result = runner.invoke(app, ["asset", "list", "--help-json"])
    assert result.exit_code == 0, result.stdout
    data = json.loads(result.stdout)
    assert "command" in data
    assert "asset list" in data["command"]
    assert "params" in data
    # 任意一个已知 flag 应出现（asset list 已有 --json / --status / etc.）
    assert "--json" in {p["name"] for p in data["params"]}


def test_asset_reassign_help_json():
    """asset reassign --help-json 输出 to_holder / to_location 字段定义。"""
    result = runner.invoke(app, ["asset", "reassign", "--help-json"])
    assert result.exit_code == 0, result.stdout
    data = json.loads(result.stdout)
    param_names = {p["name"] for p in data["params"]}
    assert "--to-holder" in param_names
    assert "--to-location" in param_names


def test_help_json_payload_schema():
    """--help-json payload 含必要 key：command, help, params (list of dicts)."""
    result = runner.invoke(app, ["asset", "show", "--help-json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert set(data.keys()) >= {"command", "help", "params"}
    assert isinstance(data["params"], list)
    for p in data["params"]:
        assert {"name", "type", "default", "required", "help"} <= set(p.keys())


def test_print_help_json_unit():
    """直接调 deps.print_help_json 工具函数（无 Typer 包装）"""
    from asset_hub.cli.deps import print_help_json  # noqa

    # 单元测：验证函数存在（详细单测可加 click.Context mock）
    assert callable(print_help_json)


def test_help_json_hidden_from_normal_help():
    """--help-json 不应出现在 --help 输出（hidden=True 守约）。"""
    result = runner.invoke(app, ["asset", "list", "--help"])
    assert result.exit_code == 0
    assert "--help-json" not in result.stdout


def test_help_json_covers_all_top_groups():
    """5 个 top-level groups 都 work，不只 asset.*（防 Typer 升级时部分 group 失 patch）。

    stats 没有 sub-command（callback-only），直接 `stats --help-json`；其余 4 个 group
    各挑一条已知 leaf 验证递归注入到位。
    """
    for group_cmd in [
        ["type", "list", "--help-json"],
        ["attachment", "add", "--help-json"],
        ["serve", "start", "--help-json"],
        ["stats", "--help-json"],
    ]:
        result = runner.invoke(app, group_cmd)
        assert result.exit_code == 0, f"{group_cmd}: {result.stdout}"
        data = json.loads(result.stdout)
        assert "command" in data
