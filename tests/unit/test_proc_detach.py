import sys
from unittest.mock import MagicMock, patch

import pytest

from asset_hub.cli.serve.proc import start_detached


@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific path")
def test_start_detached_uses_start_new_session_on_unix(tmp_path):
    log = tmp_path / "out.log"
    captured: dict = {}

    def fake_popen(cmd, **kwargs):
        captured.update(kwargs)
        m = MagicMock()
        m.pid = 99999
        return m

    with patch("asset_hub.cli.serve.proc.subprocess.Popen", fake_popen):
        start_detached(["echo", "hi"], log_file=log, cwd=tmp_path)

    assert captured.get("start_new_session") is True


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific path")
def test_start_detached_uses_creation_flags_on_windows(tmp_path):
    DETACHED_PROCESS = 0x00000008
    CREATE_NEW_PROCESS_GROUP = 0x00000200
    log = tmp_path / "out.log"
    captured: dict = {}

    def fake_popen(cmd, **kwargs):
        captured.update(kwargs)
        m = MagicMock()
        m.pid = 99999
        return m

    with patch("asset_hub.cli.serve.proc.subprocess.Popen", fake_popen):
        start_detached(["echo", "hi"], log_file=log, cwd=tmp_path)

    assert captured.get("creationflags", 0) & DETACHED_PROCESS
    assert captured.get("creationflags", 0) & CREATE_NEW_PROCESS_GROUP
    assert captured.get("close_fds") is True


def test_start_detached_returns_pid(tmp_path):
    log = tmp_path / "out.log"

    def fake_popen(cmd, **kwargs):
        m = MagicMock()
        m.pid = 42
        return m

    with patch("asset_hub.cli.serve.proc.subprocess.Popen", fake_popen):
        pid = start_detached(["echo", "hi"], log_file=log, cwd=tmp_path)
    assert pid == 42
