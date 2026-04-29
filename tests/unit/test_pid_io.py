from datetime import UTC, datetime

import pytest

from asset_hub.cli.serve.pid import read_pid_file, write_pid_file


def test_write_then_read_roundtrip(tmp_path):
    f = tmp_path / "backend.pid"
    started = datetime(2026, 4, 29, 10, 23, 14, tzinfo=UTC)
    write_pid_file(f, pid=12345, mode="prod", started_at=started)

    content = read_pid_file(f)
    assert content.pid == 12345
    assert content.mode == "prod"
    assert content.started_at == started


def test_read_returns_none_when_file_missing(tmp_path):
    f = tmp_path / "missing.pid"
    assert read_pid_file(f) is None


def test_read_handles_minimal_pid_file(tmp_path):
    f = tmp_path / "min.pid"
    f.write_text("99999\n")
    content = read_pid_file(f)
    assert content.pid == 99999
    assert content.mode is None
    assert content.started_at is None


def test_read_handles_corrupt_file(tmp_path):
    f = tmp_path / "bad.pid"
    f.write_text("not-a-number\n")
    with pytest.raises(ValueError):
        read_pid_file(f)
