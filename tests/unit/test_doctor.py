"""serve doctor 7 检查项的单元测试。

每检查项 mock subprocess / Path 状态，验证 ok/detail/code/fix_hint。
M3e §2.6 Phase 1 验收。
"""
from __future__ import annotations

from asset_hub.cli.serve.doctor import (
    DoctorCheck,
    check_alembic_head,
    check_data_writable,
    check_frontend_dist,
    check_pnpm,
    check_port_free,
    check_python_version,
    check_uv,
    run_all_checks,
)


class _FakeRun:
    def __init__(self, stdout: str = "", returncode: int = 0):
        self.stdout = stdout
        self.returncode = returncode


def test_check_uv_ok(monkeypatch):
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.subprocess.run",
        lambda *a, **kw: _FakeRun(stdout="uv 0.5.4\n", returncode=0),
    )
    c = check_uv()
    assert c.ok is True
    assert "0.5.4" in c.detail


def test_check_uv_missing(monkeypatch):
    monkeypatch.setattr("asset_hub.cli.serve.doctor._resolve", lambda cmd: None)
    c = check_uv()
    assert c.ok is False
    assert c.code == "serve.uv_missing"
    assert c.fix_hint  # 有引导


def test_check_pnpm_ok(monkeypatch):
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.subprocess.run",
        lambda *a, **kw: _FakeRun(stdout="9.12.3\n", returncode=0),
    )
    c = check_pnpm()
    assert c.ok is True


def test_check_pnpm_missing(monkeypatch):
    monkeypatch.setattr("asset_hub.cli.serve.doctor._resolve", lambda cmd: None)
    c = check_pnpm()
    assert c.ok is False
    assert c.code == "serve.pnpm_missing"


def test_check_python_version_ok():
    c = check_python_version()
    # 当前测试环境就是 >= 3.12（pyproject 已锁），应该 ok
    assert c.ok is True


def test_check_data_writable_ok(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSET_HUB_DATA_DIR", str(tmp_path))
    c = check_data_writable()
    assert c.ok is True


def test_check_data_writable_missing(tmp_path, monkeypatch):
    fake = tmp_path / "no_such_dir"
    monkeypatch.setenv("ASSET_HUB_DATA_DIR", str(fake))
    c = check_data_writable()
    # data dir 不存在或不可写应失败
    assert c.ok is False
    assert c.code == "serve.data_unwritable"


def test_check_alembic_head_ok(monkeypatch):
    # alembic current 与 alembic heads 输出一致
    outputs = iter(["abc123 (head)\n", "abc123\n"])
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.subprocess.run",
        lambda *a, **kw: _FakeRun(stdout=next(outputs), returncode=0),
    )
    c = check_alembic_head()
    assert c.ok is True


def test_check_alembic_head_outdated(monkeypatch):
    outputs = iter(["abc123\n", "def456\n"])
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.subprocess.run",
        lambda *a, **kw: _FakeRun(stdout=next(outputs), returncode=0),
    )
    c = check_alembic_head()
    assert c.ok is False
    assert c.code == "serve.alembic_outdated"


def test_check_frontend_dist_ok(tmp_path, monkeypatch):
    dist = tmp_path / "frontend" / "dist"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text("<html/>")
    monkeypatch.chdir(tmp_path)
    c = check_frontend_dist()
    assert c.ok is True


def test_check_frontend_dist_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    c = check_frontend_dist()
    assert c.ok is False
    assert c.code == "serve.dist_missing"
    assert "build" in c.fix_hint.lower()


def test_check_port_free_ok(monkeypatch):
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.proc_mod.is_port_in_use",
        lambda port: False,
    )
    c = check_port_free(8000)
    assert c.ok is True


def test_check_port_free_occupied(monkeypatch):
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.proc_mod.is_port_in_use",
        lambda port: True,
    )
    c = check_port_free(8000)
    assert c.ok is False
    assert c.code == "serve.port_occupied"


def test_run_all_checks_aggregates(monkeypatch, tmp_path):
    """全部 ok 时 result.ok=True；至少一个 fail 时 ok=False。"""
    # mock 全 ok
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.check_uv",
        lambda: DoctorCheck(name="uv", ok=True, detail="0.5.4"),
    )
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.check_pnpm",
        lambda: DoctorCheck(name="pnpm", ok=True, detail="9.12.3"),
    )
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.check_python_version",
        lambda: DoctorCheck(name="python", ok=True, detail="3.12.7"),
    )
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.check_data_writable",
        lambda: DoctorCheck(name="data_dir", ok=True, detail="/tmp"),
    )
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.check_alembic_head",
        lambda: DoctorCheck(name="alembic", ok=True, detail="head"),
    )
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.check_frontend_dist",
        lambda: DoctorCheck(name="frontend_dist", ok=True, detail="ok"),
    )
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.check_port_free",
        lambda port: DoctorCheck(name=f"port_{port}", ok=True, detail="free"),
    )

    result = run_all_checks(mode="prod")
    assert result.ok is True
    assert result.issue_count == 0
    assert len(result.checks) == 7  # uv/pnpm/python/data/alembic/dist + 1 port (prod 不查 5173)


def test_run_all_checks_dev_mode_includes_5173(monkeypatch):
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.check_uv",
        lambda: DoctorCheck(name="uv", ok=True, detail="0.5.4"),
    )
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.check_pnpm",
        lambda: DoctorCheck(name="pnpm", ok=True, detail="9.12.3"),
    )
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.check_python_version",
        lambda: DoctorCheck(name="python", ok=True, detail="3.12.7"),
    )
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.check_data_writable",
        lambda: DoctorCheck(name="data_dir", ok=True, detail="/tmp"),
    )
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.check_alembic_head",
        lambda: DoctorCheck(name="alembic", ok=True, detail="head"),
    )
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.check_frontend_dist",
        lambda: DoctorCheck(name="frontend_dist", ok=True, detail="ok"),
    )
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.check_port_free",
        lambda port: DoctorCheck(name=f"port_{port}", ok=True, detail="free"),
    )

    result = run_all_checks(mode="dev")
    assert len(result.checks) == 8  # +5173
