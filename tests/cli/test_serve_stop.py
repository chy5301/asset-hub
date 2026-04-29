"""CLI 集成测试 · serve stop

不真起 uvicorn —— Popen / psutil / probe / 端口检测全部 mock，
只验 cmd 层 → lifecycle → proc/pid 的串联。
"""

import json
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from asset_hub.cli.main import app

runner = CliRunner()


def test_stop_when_not_running(isolated_db):
    """无 PID 文件 → exit 0 + stopped:[] + stale_cleaned:[]"""
    res = runner.invoke(app, ["serve", "stop", "--json"])
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)
    assert payload["success"] is True
    assert payload["data"]["stopped"] == []
    assert payload["data"]["stale_cleaned"] == []


def test_stop_running_service(isolated_db):
    """PID 活着 → kill_tree 调用 + 删 PID 文件"""
    pids_dir = isolated_db / "pids"
    pids_dir.mkdir()
    (pids_dir / "backend.pid").write_text("12345\nmode=prod\n")

    mp = MagicMock()
    mp.cmdline.return_value = ["python", "-m", "uvicorn", "asset_hub.api.app"]
    mp.status.return_value = "running"
    mp.children.return_value = []

    with patch("asset_hub.cli.serve.pid.psutil.pid_exists", return_value=True), \
         patch("asset_hub.cli.serve.pid.psutil.Process", return_value=mp), \
         patch("asset_hub.cli.serve.proc.psutil.Process", return_value=mp), \
         patch("asset_hub.cli.serve.proc.psutil.wait_procs",
               return_value=([mp], [])):
        res = runner.invoke(app, ["serve", "stop", "--json"])
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)
    assert len(payload["data"]["stopped"]) == 1
    assert payload["data"]["stopped"][0]["service"] == "backend"
    assert payload["data"]["stopped"][0]["pid"] == 12345
    # PID 文件已删
    assert not (pids_dir / "backend.pid").exists()


def test_stop_stale_cleans_pid_file(isolated_db):
    """PID 文件存在但进程已死 → 自动清 + exit 0"""
    pids_dir = isolated_db / "pids"
    pids_dir.mkdir()
    pid_file = pids_dir / "backend.pid"
    pid_file.write_text("99999\nmode=prod\n")

    with patch("asset_hub.cli.serve.pid.psutil.pid_exists", return_value=False):
        res = runner.invoke(app, ["serve", "stop", "--json"])
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)
    assert len(payload["data"]["stale_cleaned"]) == 1
    assert not pid_file.exists()
