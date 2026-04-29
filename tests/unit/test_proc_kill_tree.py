from unittest.mock import MagicMock, patch

import pytest

from asset_hub.cli.serve.proc import KillFailedError, KillMethod, kill_tree


def _mock_proc(pid: int):
    p = MagicMock()
    p.pid = pid
    return p


def test_kill_tree_sigterm_succeeds():
    proc = _mock_proc(pid=1)
    children = [_mock_proc(pid=2), _mock_proc(pid=3)]

    with patch("asset_hub.cli.serve.proc.psutil.Process") as mock_proc_cls, \
         patch("asset_hub.cli.serve.proc.psutil.wait_procs") as mock_wait:
        mock_proc_cls.return_value = proc
        proc.children.return_value = children
        mock_wait.side_effect = [(children + [proc], [])]  # all dead after SIGTERM

        method = kill_tree(1, timeout=5.0)

    assert method is KillMethod.SIGTERM
    proc.terminate.assert_called_once()
    for c in children:
        c.terminate.assert_called_once()


def test_kill_tree_falls_back_to_sigkill():
    proc = _mock_proc(pid=1)
    proc.children.return_value = []

    with patch("asset_hub.cli.serve.proc.psutil.Process") as mock_proc_cls, \
         patch("asset_hub.cli.serve.proc.psutil.wait_procs") as mock_wait:
        mock_proc_cls.return_value = proc
        # SIGTERM 后 proc 仍存活；SIGKILL 后死
        mock_wait.side_effect = [
            ([], [proc]),  # SIGTERM 后 alive
            ([proc], []),  # SIGKILL 后 dead
        ]

        method = kill_tree(1, timeout=5.0)

    assert method is KillMethod.SIGKILL
    proc.terminate.assert_called_once()
    proc.kill.assert_called_once()


def test_kill_tree_raises_when_sigkill_fails():
    proc = _mock_proc(pid=1)
    proc.children.return_value = []

    with patch("asset_hub.cli.serve.proc.psutil.Process") as mock_proc_cls, \
         patch("asset_hub.cli.serve.proc.psutil.wait_procs") as mock_wait:
        mock_proc_cls.return_value = proc
        mock_wait.side_effect = [
            ([], [proc]),  # SIGTERM 后 alive
            ([], [proc]),  # SIGKILL 后仍 alive
        ]

        with pytest.raises(KillFailedError):
            kill_tree(1, timeout=5.0)
