"""serve doctor 7 检查项的单元测试。

每检查项 mock subprocess / Path 状态，验证 ok/detail/code/fix_hint。
M3e §2.6 Phase 1 验收。
"""

from __future__ import annotations

import pytest

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
    def __init__(self, stdout: str = "", returncode: int = 0, stderr: str = ""):
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = stderr


def test_check_uv_ok(monkeypatch):
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor._resolve", lambda cmd: f"/fake/{cmd}"
    )
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
        "asset_hub.cli.serve.doctor._resolve", lambda cmd: f"/fake/{cmd}"
    )
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
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor._resolve", lambda cmd: f"/fake/{cmd}"
    )
    outputs = iter(["abc123 (head)\n", "abc123\n"])
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.subprocess.run",
        lambda *a, **kw: _FakeRun(stdout=next(outputs), returncode=0),
    )
    c = check_alembic_head()
    assert c.ok is True


def test_check_alembic_head_outdated(monkeypatch):
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor._resolve", lambda cmd: f"/fake/{cmd}"
    )
    outputs = iter(["abc123\n", "def456\n"])
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.subprocess.run",
        lambda *a, **kw: _FakeRun(stdout=next(outputs), returncode=0),
    )
    c = check_alembic_head()
    assert c.ok is False
    assert c.code == "serve.alembic_outdated"


def test_check_alembic_head_uv_missing(monkeypatch):
    monkeypatch.setattr("asset_hub.cli.serve.doctor._resolve", lambda cmd: None)
    c = check_alembic_head()
    assert c.ok is False
    assert c.code == "serve.alembic_outdated"
    assert "install uv" in c.fix_hint.lower()


def test_check_alembic_head_command_not_found(monkeypatch):
    """alembic 未装（uv run alembic current 退出非零 + stderr 含 module not found）→ fix_hint 指向 uv sync。"""
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor._resolve", lambda cmd: f"/fake/{cmd}"
    )
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.subprocess.run",
        lambda *a, **kw: _FakeRun(returncode=1, stderr="No module named 'alembic'"),
    )
    c = check_alembic_head()
    assert c.ok is False
    assert c.code == "serve.alembic_outdated"
    assert "uv sync" in c.fix_hint


def test_check_alembic_head_other_failure_fallback(monkeypatch):
    """alembic current 退出非零且 stderr 不含 module-missing 关键词 → fix_hint 默认 fallback 到 upgrade head。"""
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor._resolve", lambda cmd: f"/fake/{cmd}"
    )
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.subprocess.run",
        lambda *a, **kw: _FakeRun(
            returncode=1, stderr="Target database is not up to date"
        ),
    )
    c = check_alembic_head()
    assert c.ok is False
    assert c.code == "serve.alembic_outdated"
    assert "alembic upgrade head" in c.fix_hint


def test_check_frontend_dist_ok(tmp_path, monkeypatch):
    """check_frontend_dist 通过 _resolve_repo_root 定位 dist，不依赖 cwd。"""
    dist = tmp_path / "frontend" / "dist"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text("<html/>")
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor._resolve_repo_root",
        lambda: tmp_path,
    )
    c = check_frontend_dist()
    assert c.ok is True


def test_check_frontend_dist_missing(tmp_path, monkeypatch):
    """fake repo root 下无 frontend/dist → 报 dist_missing。"""
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor._resolve_repo_root",
        lambda: tmp_path,
    )
    c = check_frontend_dist()
    assert c.ok is False
    assert c.code == "serve.dist_missing"
    assert "build" in c.fix_hint.lower()


def test_check_frontend_dist_independent_of_cwd(tmp_path, monkeypatch):
    """check_frontend_dist 用 _resolve_repo_root 找 dist，与 cwd 完全无关。"""
    # 准备 fake repo with valid frontend/dist
    fake_repo = tmp_path / "fake-repo"
    (fake_repo / "frontend" / "dist").mkdir(parents=True)
    (fake_repo / "frontend" / "dist" / "index.html").write_text("<html/>")
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor._resolve_repo_root",
        lambda: fake_repo,
    )

    # CWD 指到一个没 frontend/dist 的随机目录
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    # 结果应基于 fake_repo（有 dist），而不是 cwd（没 dist）
    c = check_frontend_dist()
    assert c.ok is True


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


@pytest.fixture
def mock_all_checks_ok(monkeypatch):
    """全部 check_* 函数 mock 为 ok，run_all_checks_* 测共用。"""
    fakes = {
        "check_uv": DoctorCheck(name="uv", ok=True, detail="0.5.4"),
        "check_pnpm": DoctorCheck(name="pnpm", ok=True, detail="9.12.3"),
        "check_python_version": DoctorCheck(name="python", ok=True, detail="3.12.7"),
        "check_data_writable": DoctorCheck(name="data_dir", ok=True, detail="/tmp"),
        "check_alembic_head": DoctorCheck(name="alembic", ok=True, detail="head"),
        "check_frontend_dist": DoctorCheck(name="frontend_dist", ok=True, detail="ok"),
    }
    for name, check in fakes.items():
        monkeypatch.setattr(f"asset_hub.cli.serve.doctor.{name}", lambda c=check: c)
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.check_port_free",
        lambda port: DoctorCheck(name=f"port_{port}", ok=True, detail="free"),
    )
    monkeypatch.setattr(
        "asset_hub.cli.serve.doctor.check_port_owner",
        lambda port, expected_pid: DoctorCheck(
            name=f"port_owner:{port}", ok=True, detail=f"port {port} ok"
        ),
    )


def test_run_all_checks_aggregates(mock_all_checks_ok):
    """全部 ok 时 result.ok=True；prod 模式 8 项（含 :8000 port + port_owner）。"""
    result = run_all_checks(mode="prod")
    assert result.ok is True
    assert result.issue_count == 0
    assert (
        len(result.checks) == 8
    )  # uv/pnpm/python/data/alembic/dist + port_free(8000) + port_owner(8000)


def test_run_all_checks_dev_mode_includes_5173(mock_all_checks_ok):
    """dev 模式额外查 :5173 + port_owner，共 10 项。"""
    result = run_all_checks(mode="dev")
    assert len(result.checks) == 10  # +port_free(5173) + port_owner(5173)


# CL-4: port_owner 检测组件（6 个失败测）
def test_check_port_owner_free(monkeypatch):
    """端口空闲 → ok=True, detail 含 '空闲'。"""
    from asset_hub.cli.serve import doctor

    monkeypatch.setattr(doctor, "_find_port_owner_pid", lambda port: None)
    result = doctor.check_port_owner(5173, expected_pid=12345)
    assert result.ok is True
    assert "空闲" in result.detail


def test_check_port_owner_self(monkeypatch):
    """端口由 expected_pid 占用 → ok=True, detail 含 PID + '我管理'。"""
    from asset_hub.cli.serve import doctor

    monkeypatch.setattr(doctor, "_find_port_owner_pid", lambda port: 12345)
    result = doctor.check_port_owner(5173, expected_pid=12345)
    assert result.ok is True
    assert "12345" in result.detail
    assert "我管理" in result.detail


def test_check_port_owner_external(monkeypatch):
    """端口被外部进程占用，expected_pid 给定 → ok=False + code + fix_hint。"""
    from asset_hub.cli.serve import doctor

    monkeypatch.setattr(doctor, "_find_port_owner_pid", lambda port: 9999)
    result = doctor.check_port_owner(5173, expected_pid=12345)
    assert result.ok is False
    assert result.code == "external_port_owner"
    assert "9999" in result.detail
    assert "5173" in result.fix_hint


def test_check_port_owner_external_no_pidfile(monkeypatch):
    """端口被占但 PID 文件不存在 (expected_pid=None) → ok=False + detail 含 '无对应 PID 文件'。"""
    from asset_hub.cli.serve import doctor

    monkeypatch.setattr(doctor, "_find_port_owner_pid", lambda port: 9999)
    result = doctor.check_port_owner(5173, expected_pid=None)
    assert result.ok is False
    assert result.code == "external_port_owner"
    assert "9999" in result.detail
    assert "无对应 PID 文件" in result.detail


def test_run_all_checks_includes_port_owner(monkeypatch):
    """run_all_checks 在 dev 模式应包含两个 port_owner 检测 (5173 + 8000)。"""
    from asset_hub.cli.serve import doctor

    monkeypatch.setattr(doctor, "_find_port_owner_pid", lambda port: None)
    result = doctor.run_all_checks(mode="dev")
    names = [c.name for c in result.checks]
    assert "port_owner:5173" in names
    assert "port_owner:8000" in names


def test_run_all_checks_prod_mode_no_5173_owner(monkeypatch):
    """prod 模式无前端端口 → port_owner:5173 不应出现，但 port_owner:8000 必须有。"""
    from asset_hub.cli.serve import doctor

    monkeypatch.setattr(doctor, "_find_port_owner_pid", lambda port: None)
    result = doctor.run_all_checks(mode="prod")
    names = [c.name for c in result.checks]
    assert "port_owner:5173" not in names
    assert "port_owner:8000" in names


class TestPortOwnerParentChain:
    """CL-22：check_port_owner 识别 uv 父子进程链路（#22 闭环）。"""

    def test_check_port_owner_self_via_parent_chain(self, monkeypatch):
        """actual_pid 的直接父是 expected_pid → ok=True（uv 父子场景）。"""
        from asset_hub.cli.serve import doctor
        import psutil

        monkeypatch.setattr(doctor, "_find_port_owner_pid", lambda port: 59740)

        class FakeParent:
            pid = 59584
        class FakePython:
            def parents(self): return [FakeParent()]
        monkeypatch.setattr(psutil, "Process", lambda pid: FakePython() if pid == 59740 else FakeParent())

        result = doctor.check_port_owner(8000, expected_pid=59584)
        assert result.ok is True
        assert "59740" in result.detail
        assert "我管理" in result.detail

    def test_check_port_owner_self_via_grandparent_chain(self, monkeypatch):
        """actual_pid 的祖父是 expected_pid（多层 spawn 场景）→ ok=True。"""
        from asset_hub.cli.serve import doctor
        import psutil

        monkeypatch.setattr(doctor, "_find_port_owner_pid", lambda port: 100)

        class P:
            def __init__(self, pid): self.pid = pid
        class FakeChild:
            def parents(self): return [P(99), P(98)]
        monkeypatch.setattr(psutil, "Process", lambda pid: FakeChild() if pid == 100 else None)

        result = doctor.check_port_owner(8000, expected_pid=98)
        assert result.ok is True

    def test_check_port_owner_external_unrelated_chain(self, monkeypatch):
        """actual_pid 祖先链不含 expected_pid → ok=False（保持原行为）。"""
        from asset_hub.cli.serve import doctor
        import psutil

        monkeypatch.setattr(doctor, "_find_port_owner_pid", lambda port: 9999)

        class P:
            def __init__(self, pid): self.pid = pid
        class FakeUnrelated:
            def parents(self): return [P(8888), P(7777)]
        monkeypatch.setattr(psutil, "Process", lambda pid: FakeUnrelated() if pid == 9999 else None)

        result = doctor.check_port_owner(8000, expected_pid=12345)
        assert result.ok is False
        assert result.code == "external_port_owner"
        assert "9999" in result.detail

    def test_walks_ancestor_chain_handles_psutil_errors(self, monkeypatch):
        """_walks_ancestor_chain: psutil.Process raises → 返 False 不抛。"""
        from asset_hub.cli.serve import doctor
        import psutil

        def raise_no_such(pid):
            raise psutil.NoSuchProcess(pid)
        monkeypatch.setattr(psutil, "Process", raise_no_such)

        assert doctor._walks_ancestor_chain(9999, 12345) is False
