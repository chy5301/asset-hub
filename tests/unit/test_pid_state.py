from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import psutil

from asset_hub.cli.serve.pid import (
    PidStateStatus,
    read_pid_state,
    write_pid_file,
)


def _mock_proc(cmdline: list[str], status: str = "running"):
    p = MagicMock()
    p.cmdline.return_value = cmdline
    p.status.return_value = status
    return p


def test_read_pid_state_none_when_file_missing(tmp_path):
    state = read_pid_state(tmp_path / "missing.pid", "backend")
    assert state.status is PidStateStatus.NONE
    assert state.pid is None


def test_read_pid_state_running_when_match(tmp_path):
    f = tmp_path / "backend.pid"
    write_pid_file(f, pid=12345, mode="prod", started_at=datetime.now(UTC))

    with patch("asset_hub.cli.serve.pid.psutil.pid_exists", return_value=True), \
         patch("asset_hub.cli.serve.pid.psutil.Process") as mock_process:
        mock_process.return_value = _mock_proc(
            cmdline=["python", "-m", "uvicorn", "asset_hub.api.app:app"]
        )
        state = read_pid_state(f, "backend")
    assert state.status is PidStateStatus.RUNNING
    assert state.pid == 12345
    assert state.mode == "prod"


def test_read_pid_state_stale_when_pid_dead(tmp_path):
    f = tmp_path / "backend.pid"
    write_pid_file(f, pid=99999, mode="prod", started_at=None)

    with patch("asset_hub.cli.serve.pid.psutil.pid_exists", return_value=False):
        state = read_pid_state(f, "backend")
    assert state.status is PidStateStatus.STALE


def test_read_pid_state_stale_when_zombie(tmp_path):
    f = tmp_path / "backend.pid"
    write_pid_file(f, pid=12345, mode="prod", started_at=None)

    with patch("asset_hub.cli.serve.pid.psutil.pid_exists", return_value=True), \
         patch("asset_hub.cli.serve.pid.psutil.Process") as mock_process:
        mock_process.return_value = _mock_proc(
            cmdline=["python", "-m", "uvicorn", "asset_hub.api.app:app"],
            status=psutil.STATUS_ZOMBIE,
        )
        state = read_pid_state(f, "backend")
    assert state.status is PidStateStatus.STALE


def test_read_pid_state_stale_when_cmdline_mismatch(tmp_path):
    """PID 复用到无关进程"""
    f = tmp_path / "backend.pid"
    write_pid_file(f, pid=12345, mode="prod", started_at=None)

    with patch("asset_hub.cli.serve.pid.psutil.pid_exists", return_value=True), \
         patch("asset_hub.cli.serve.pid.psutil.Process") as mock_process:
        mock_process.return_value = _mock_proc(
            cmdline=["bash", "-c", "sleep 99"]  # 不含 uvicorn / asset_hub
        )
        state = read_pid_state(f, "backend")
    assert state.status is PidStateStatus.STALE


def test_read_pid_state_corrupt_file_treated_stale(tmp_path):
    f = tmp_path / "bad.pid"
    f.write_text("garbage\n")
    state = read_pid_state(f, "backend")
    assert state.status is PidStateStatus.STALE
