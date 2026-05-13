"""CLI 集成测试 · serve logs

只读取本地日志文件，无外部依赖。
"""

import json

from typer.testing import CliRunner

from asset_hub.cli.main import app

runner = CliRunner()


def test_logs_no_file_friendly_message(isolated_db):
    """log 文件不存在 → exit 0 + 空 lines"""
    res = runner.invoke(app, ["serve", "logs", "--json"])
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)
    assert payload["data"]["lines"] == []


def test_logs_tail_lines(isolated_db):
    """log 文件存在 → tail N 行"""
    logs_dir = isolated_db / "logs"
    logs_dir.mkdir()
    (logs_dir / "backend.log").write_text(
        "\n".join(f"line{i}" for i in range(50)) + "\n"
    )
    res = runner.invoke(app, ["serve", "logs", "--lines", "5", "--json"])
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)
    assert len(payload["data"]["lines"]) == 5
    assert payload["data"]["lines"][-1] == "line49"


def test_logs_invalid_service_returns_exit_2(isolated_db):
    """非法 --service → exit 2"""
    res = runner.invoke(app, ["serve", "logs", "--service", "weird", "--json"])
    assert res.exit_code == 2, res.stdout
