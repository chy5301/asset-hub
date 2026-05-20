"""serve doctor CLI 测试 (plain / json / fail exit 1)。"""

from __future__ import annotations

import json

from typer.testing import CliRunner

from asset_hub.cli.main import app
from asset_hub.cli.serve.doctor import DoctorCheck

runner = CliRunner()


def _mock_all_ok(monkeypatch):
    """所有 check 都返回 ok=True。"""
    for fn in (
        "check_uv",
        "check_pnpm",
        "check_python_version",
        "check_data_writable",
        "check_alembic_head",
        "check_frontend_dist",
    ):
        monkeypatch.setattr(
            f"asset_hub.cli.serve.doctor.{fn}",
            lambda _fn=fn: DoctorCheck(name=_fn, ok=True, detail="ok"),
        )
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.check_port_free",
        lambda port: DoctorCheck(name=f"port_{port}", ok=True, detail="free"),
    )
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.check_port_owner",
        lambda port, expected_pid: DoctorCheck(
            name=f"port_owner:{port}", ok=True, detail="ok"
        ),
    )


def _mock_dist_missing(monkeypatch):
    """only frontend_dist fails。"""
    for fn in (
        "check_uv",
        "check_pnpm",
        "check_python_version",
        "check_data_writable",
        "check_alembic_head",
    ):
        monkeypatch.setattr(
            f"asset_hub.cli.serve.doctor.{fn}",
            lambda _fn=fn: DoctorCheck(name=_fn, ok=True, detail="ok"),
        )
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.check_frontend_dist",
        lambda: DoctorCheck(
            name="frontend/dist",
            ok=False,
            detail="missing",
            code="serve.dist_missing",
            fix_hint="run `pnpm --dir frontend build`",
        ),
    )
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.check_port_free",
        lambda port: DoctorCheck(name=f"port_{port}", ok=True, detail="free"),
    )
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.check_port_owner",
        lambda port, expected_pid: DoctorCheck(
            name=f"port_owner:{port}", ok=True, detail="ok"
        ),
    )


def test_doctor_plain_all_ok(monkeypatch):
    _mock_all_ok(monkeypatch)
    result = runner.invoke(app, ["serve", "doctor"])
    assert result.exit_code == 0
    assert "All checks passed" in result.stdout
    assert "✓" in result.stdout


def test_doctor_json_all_ok(monkeypatch):
    _mock_all_ok(monkeypatch)
    result = runner.invoke(app, ["serve", "doctor", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["success"] is True
    assert payload["data"]["ok"] is True
    assert payload["data"]["issue_count"] == 0
    assert len(payload["data"]["checks"]) == 8  # prod mode: 7 原 + port_owner:8000


def test_doctor_json_one_fail_exits_1(monkeypatch):
    _mock_dist_missing(monkeypatch)
    result = runner.invoke(app, ["serve", "doctor", "--json"])
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert (
        payload["success"] is True
    )  # success=true 因为 doctor 不抛域异常；但 data.ok=false
    assert payload["data"]["ok"] is False
    assert payload["data"]["issue_count"] == 1
    bad = [c for c in payload["data"]["checks"] if not c["ok"]][0]
    assert bad["code"] == "serve.dist_missing"
    assert "build" in bad["fix_hint"]


def test_doctor_invalid_mode_exits_2(monkeypatch):
    result = runner.invoke(app, ["serve", "doctor", "--mode", "invalid", "--json"])
    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "serve.usage"


def test_doctor_dev_mode_includes_5173(monkeypatch):
    _mock_all_ok(monkeypatch)
    result = runner.invoke(app, ["serve", "doctor", "--mode", "dev", "--json"])
    payload = json.loads(result.stdout)
    assert (
        len(payload["data"]["checks"]) == 10
    )  # dev: 6 原 + port_free 8000 + port_free 5173 + port_owner:8000 + port_owner:5173
