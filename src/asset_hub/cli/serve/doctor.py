"""serve doctor 子命令的核心检查逻辑。

read-only 诊断；不抛域异常；所有 check 收集后聚合渲染。
M3e §2.4。
"""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from asset_hub.cli.serve import proc as proc_mod
from asset_hub.config import Settings


@dataclass
class DoctorCheck:
    name: str
    ok: bool
    detail: str = ""
    code: str | None = None
    fix_hint: str = ""

    def to_dict(self) -> dict:
        d: dict = {"name": self.name, "ok": self.ok, "detail": self.detail}
        if not self.ok:
            d["code"] = self.code or ""
            d["fix_hint"] = self.fix_hint
        return d


@dataclass
class DoctorResult:
    checks: list[DoctorCheck] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(c.ok for c in self.checks)

    @property
    def issue_count(self) -> int:
        return sum(1 for c in self.checks if not c.ok)

    def to_dict(self) -> dict:
        return {
            "checks": [c.to_dict() for c in self.checks],
            "ok": self.ok,
            "issue_count": self.issue_count,
        }


def _run_version(cmd: str) -> str:
    """运行 `<cmd> --version`，返回 stdout（已 strip）。FileNotFoundError 让 caller 捕。"""
    result = subprocess.run(
        [cmd, "--version"], capture_output=True, text=True, check=False
    )
    return result.stdout.strip()


def check_uv() -> DoctorCheck:
    try:
        out = _run_version("uv")
        return DoctorCheck(name="uv (>= 0.4)", ok=True, detail=out)
    except FileNotFoundError:
        return DoctorCheck(
            name="uv (>= 0.4)", ok=False, detail="not found",
            code="serve.uv_missing",
            fix_hint="install uv: https://docs.astral.sh/uv/getting-started/installation/",
        )


def check_pnpm() -> DoctorCheck:
    try:
        out = _run_version("pnpm")
        return DoctorCheck(name="pnpm (>= 9)", ok=True, detail=out)
    except FileNotFoundError:
        return DoctorCheck(
            name="pnpm (>= 9)", ok=False, detail="not found",
            code="serve.pnpm_missing",
            fix_hint="install pnpm: npm install -g pnpm@9",
        )


def check_python_version() -> DoctorCheck:
    v = sys.version_info
    s = f"{v.major}.{v.minor}.{v.micro}"
    if v >= (3, 12):
        return DoctorCheck(name="Python (>= 3.12)", ok=True, detail=s)
    return DoctorCheck(
        name="Python (>= 3.12)", ok=False, detail=s,
        code="serve.python_version_low",
        fix_hint="upgrade to Python 3.12+",
    )


def check_data_writable() -> DoctorCheck:
    settings = Settings()
    p = Path(settings.data_dir)
    if not p.exists():
        return DoctorCheck(
            name="data dir writable", ok=False, detail=f"{p} not exists",
            code="serve.data_unwritable",
            fix_hint=f"mkdir -p {p}",
        )
    test_file = p / ".doctor_writable_probe"
    try:
        test_file.write_text("")
        test_file.unlink()
        return DoctorCheck(name="data dir writable", ok=True, detail=str(p))
    except OSError as e:
        return DoctorCheck(
            name="data dir writable", ok=False, detail=f"{p} ({e})",
            code="serve.data_unwritable",
            fix_hint=f"check filesystem permissions on {p}",
        )


def check_alembic_head() -> DoctorCheck:
    try:
        cur = subprocess.run(
            ["uv", "run", "alembic", "current"],
            capture_output=True, text=True, check=False,
        ).stdout.strip()
        head = subprocess.run(
            ["uv", "run", "alembic", "heads"],
            capture_output=True, text=True, check=False,
        ).stdout.strip()
    except FileNotFoundError:
        return DoctorCheck(
            name="alembic head", ok=False, detail="uv/alembic not available",
            code="serve.alembic_outdated",
            fix_hint="run `uv sync` then `uv run alembic upgrade head`",
        )

    cur_rev = cur.split()[0] if cur else ""
    head_rev = head.split()[0] if head else ""
    if cur_rev and cur_rev == head_rev:
        return DoctorCheck(
            name="alembic head", ok=True,
            detail=f"{cur_rev[:8]} (current = head)",
        )
    return DoctorCheck(
        name="alembic head", ok=False,
        detail=f"current={cur_rev[:8] or '<none>'} head={head_rev[:8] or '<none>'}",
        code="serve.alembic_outdated",
        fix_hint="run `uv run alembic upgrade head`",
    )


def check_frontend_dist() -> DoctorCheck:
    p = Path("frontend/dist/index.html")
    if p.exists():
        return DoctorCheck(name="frontend/dist", ok=True, detail="present")
    return DoctorCheck(
        name="frontend/dist", ok=False, detail="missing",
        code="serve.dist_missing",
        fix_hint="run `pnpm --dir frontend build`",
    )


def check_port_free(port: int) -> DoctorCheck:
    in_use = proc_mod.is_port_in_use(port)
    name = f"port :{port} free"
    if not in_use:
        return DoctorCheck(name=name, ok=True, detail="free")
    return DoctorCheck(
        name=name, ok=False, detail="in use",
        code="serve.port_occupied",
        fix_hint=f"stop existing service on :{port} or override with --port",
    )


def run_all_checks(*, mode: str = "prod") -> DoctorResult:
    """聚合 7-8 项检查；mode='dev' 时额外查 :5173。"""
    checks = [
        check_uv(),
        check_pnpm(),
        check_python_version(),
        check_data_writable(),
        check_alembic_head(),
        check_frontend_dist(),
        check_port_free(8000),
    ]
    if mode == "dev":
        checks.append(check_port_free(5173))
    return DoctorResult(checks=checks)
