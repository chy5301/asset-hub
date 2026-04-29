"""CLI 集成测试 · serve restart

不真起 uvicorn —— Popen / psutil / probe / 端口检测全部 mock。
"""

import json
import pathlib
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from asset_hub.cli.main import app

runner = CliRunner()


def _patch_dist_exists(exists: bool):
    real_exists = pathlib.Path.exists

    def fake_exists(self):
        if "dist/index.html" in str(self).replace("\\", "/"):
            return exists
        return real_exists(self)

    return patch.object(pathlib.Path, "exists", fake_exists)


def test_restart_cannot_infer_mode_when_no_pid(isolated_db):
    """无 PID 文件 + 无 --mode → exit 1 mode_required"""
    res = runner.invoke(app, ["serve", "restart", "--json"])
    assert res.exit_code == 1, res.stdout
    payload = json.loads(res.stdout)
    assert payload["error"]["code"] == "serve.mode_required"


def test_restart_with_explicit_mode(isolated_db):
    """显式 --mode prod + skip-build → 走 stop+start 全流程"""
    fake_popen_proc = MagicMock()
    fake_popen_proc.pid = 99999
    with patch("asset_hub.cli.serve.proc.is_port_in_use", return_value=False), \
         patch("asset_hub.cli.serve.proc.subprocess.Popen", return_value=fake_popen_proc), \
         patch("asset_hub.cli.serve.lifecycle.probe_mod.probe_until_ready",
               return_value=MagicMock(ok=True)), \
         _patch_dist_exists(True):
        res = runner.invoke(
            app, ["serve", "restart", "--mode", "prod", "--skip-build", "--json"]
        )
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)
    assert payload["success"] is True


def test_restart_invalid_mode_returns_exit_2(isolated_db):
    """非法 --mode → exit 2"""
    res = runner.invoke(app, ["serve", "restart", "--mode", "foo", "--json"])
    assert res.exit_code == 2, res.stdout
