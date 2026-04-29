"""CLI 集成测试 · serve status

不真起 uvicorn —— psutil / probe 全部 mock。
"""

import json
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from asset_hub.cli.main import app

runner = CliRunner()


def test_status_not_running(isolated_db):
    res = runner.invoke(app, ["serve", "status", "--json"])
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)
    assert payload["data"]["running"] is False


def test_status_running_with_probe(isolated_db):
    """PID 活 + healthz 200 → running + healthy"""
    pids_dir = isolated_db / "pids"
    pids_dir.mkdir()
    (pids_dir / "backend.pid").write_text(
        "12345\nmode=prod\nstarted_at=2026-04-29T10:00:00Z\n"
    )

    mp = MagicMock()
    mp.cmdline.return_value = ["python", "-m", "uvicorn", "asset_hub.api.app"]
    mp.status.return_value = "running"

    with patch("asset_hub.cli.serve.pid.psutil.pid_exists", return_value=True), \
         patch("asset_hub.cli.serve.pid.psutil.Process", return_value=mp), \
         patch("asset_hub.cli.serve.lifecycle.probe_mod.probe_once", return_value=True):
        res = runner.invoke(app, ["serve", "status", "--json"])
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)
    assert payload["data"]["running"] is True
    assert payload["data"]["mode"] == "prod"
    assert payload["data"]["backend"]["healthy"] is True


def test_status_no_probe_skips_http(isolated_db):
    """--no-probe 跳过 HTTP 探测"""
    pids_dir = isolated_db / "pids"
    pids_dir.mkdir()
    (pids_dir / "backend.pid").write_text("12345\nmode=prod\n")

    mp = MagicMock()
    mp.cmdline.return_value = ["python", "-m", "uvicorn", "asset_hub.api.app"]
    mp.status.return_value = "running"

    with patch("asset_hub.cli.serve.pid.psutil.pid_exists", return_value=True), \
         patch("asset_hub.cli.serve.pid.psutil.Process", return_value=mp), \
         patch("asset_hub.cli.serve.lifecycle.probe_mod.probe_once") as mock_probe:
        res = runner.invoke(app, ["serve", "status", "--no-probe", "--json"])
    assert res.exit_code == 0, res.stdout
    mock_probe.assert_not_called()
