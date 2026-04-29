"""CLI 集成测试 · serve start

不真起 uvicorn —— Popen / psutil / probe / 端口检测全部 mock，
只验 cmd 层 → lifecycle → proc/pid/probe 的串联。
"""

import json
import pathlib
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from asset_hub.cli.main import app

runner = CliRunner()


def _patch_pid_dead():
    return patch("asset_hub.cli.serve.pid.psutil.pid_exists", return_value=False)


def _patch_port_free():
    return patch("asset_hub.cli.serve.proc.is_port_in_use", return_value=False)


def _patch_popen_returns_pid(pid: int = 99999):
    fake = MagicMock()
    fake.pid = pid
    return patch("asset_hub.cli.serve.proc.subprocess.Popen", return_value=fake)


def _patch_probe_ok():
    probe_result = MagicMock()
    probe_result.ok = True
    return patch(
        "asset_hub.cli.serve.lifecycle.probe_mod.probe_until_ready",
        return_value=probe_result,
    )


def _patch_dist_exists(exists: bool):
    """让 Path('frontend/dist/index.html').exists() 返回指定值，其它路径走真实 exists。"""
    real_exists = pathlib.Path.exists

    def fake_exists(self):
        if "dist/index.html" in str(self).replace("\\", "/"):
            return exists
        return real_exists(self)

    return patch.object(pathlib.Path, "exists", fake_exists)


def test_start_prod_success_skip_build(isolated_db):
    """prod 模式 + --skip-build + dist 存在 → 启动成功"""
    with _patch_pid_dead(), \
         _patch_port_free(), \
         _patch_popen_returns_pid(99999), \
         _patch_probe_ok(), \
         _patch_dist_exists(True):
        res = runner.invoke(
            app, ["serve", "start", "--skip-build", "--mode", "prod", "--json"]
        )
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)
    assert payload["success"] is True
    assert payload["data"]["mode"] == "prod"
    assert payload["data"]["backend"]["pid"] == 99999
    assert payload["data"]["frontend"] is None


def test_start_already_running_returns_exit_1(isolated_db):
    """PID 文件存在且对应进程活着 → exit 1 already_running"""
    pids_dir = isolated_db / "pids"
    pids_dir.mkdir()
    (pids_dir / "backend.pid").write_text("12345\nmode=prod\n")

    mp = MagicMock()
    mp.cmdline.return_value = ["python", "-m", "uvicorn", "asset_hub.api.app"]
    mp.status.return_value = "running"

    with patch("asset_hub.cli.serve.pid.psutil.pid_exists", return_value=True), \
         patch("asset_hub.cli.serve.pid.psutil.Process", return_value=mp):
        res = runner.invoke(
            app, ["serve", "start", "--mode", "prod", "--skip-build", "--json"]
        )
    assert res.exit_code == 1, res.stdout
    payload = json.loads(res.stdout)
    assert payload["error"]["code"] == "serve.already_running"


def test_start_port_occupied(isolated_db):
    """端口被外部进程占用 → exit 1 serve.port_occupied"""
    with _patch_pid_dead(), \
         patch("asset_hub.cli.serve.proc.is_port_in_use", return_value=True):
        res = runner.invoke(
            app, ["serve", "start", "--mode", "prod", "--skip-build", "--json"]
        )
    assert res.exit_code == 1, res.stdout
    payload = json.loads(res.stdout)
    assert payload["error"]["code"] == "serve.port_occupied"


def test_start_invalid_mode_returns_exit_2(isolated_db):
    """非法 mode → exit 2"""
    res = runner.invoke(app, ["serve", "start", "--mode", "foo", "--json"])
    assert res.exit_code == 2, res.stdout
