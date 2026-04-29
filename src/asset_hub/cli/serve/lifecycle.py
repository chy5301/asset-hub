from __future__ import annotations

import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from asset_hub.cli.serve import logs as logs_mod
from asset_hub.cli.serve import pid as pid_mod
from asset_hub.cli.serve import probe as probe_mod
from asset_hub.cli.serve import proc as proc_mod
from asset_hub.cli.serve.output import ServiceInfo, StartResult
from asset_hub.config import Settings


class ServeLifecycleError(Exception):
    """raise 时携带 ServeError 给上层 cmd 转 exit code。"""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


def start_service(
    *,
    mode: Literal["dev", "prod"],
    skip_build: bool,
    port_override: int | None,
    frontend_port_override: int | None,
    host_override: str | None,
) -> StartResult:
    t0 = time.monotonic()
    settings = Settings()
    backend_port = port_override if port_override is not None else settings.backend_port
    frontend_port = (
        frontend_port_override if frontend_port_override is not None else settings.frontend_port
    )
    host = host_override if host_override is not None else settings.resolve_backend_host(mode)

    # Phase 0 · 前置检查
    _ensure_dirs_writable(settings)
    _check_pids_or_clean_stale(settings)
    if proc_mod.is_port_in_use(backend_port):
        raise ServeLifecycleError("serve.port_occupied", f"port {backend_port} is in use")
    if mode == "dev" and proc_mod.is_port_in_use(frontend_port):
        raise ServeLifecycleError("serve.port_occupied", f"port {frontend_port} is in use")

    # Phase 1 · 构建（仅 prod）
    build_ran = False
    if mode == "prod":
        dist_index = Path("frontend/dist/index.html")
        if not dist_index.exists():
            if skip_build:
                raise ServeLifecycleError(
                    "serve.dist_missing",
                    "frontend/dist not found; omit --skip-build or run 'pnpm --dir frontend build'",
                )
            _run_build()
            build_ran = True

    # Phase 2 · 日志轮转
    backend_log = settings.logs_dir / "backend.log"
    logs_mod.rotate_log(backend_log)
    if mode == "dev":
        logs_mod.rotate_log(settings.logs_dir / "frontend.log")

    # Phase 3 · 启动子进程
    started_at = datetime.now(UTC)
    backend_cmd = [
        "uv", "run", "uvicorn", "asset_hub.api.app:app",
        "--host", host, "--port", str(backend_port),
    ]
    if mode == "dev":
        backend_cmd.append("--reload")

    backend_pid = proc_mod.start_detached(
        backend_cmd, log_file=backend_log, cwd=Path.cwd()
    )
    pid_mod.write_pid_file(
        settings.pids_dir / "backend.pid",
        pid=backend_pid, mode=mode, started_at=started_at,
    )

    frontend_pid: int | None = None
    if mode == "dev":
        frontend_log = settings.logs_dir / "frontend.log"
        frontend_pid = proc_mod.start_detached(
            ["pnpm", "--dir", "frontend", "dev"],
            log_file=frontend_log, cwd=Path.cwd(),
        )
        pid_mod.write_pid_file(
            settings.pids_dir / "frontend.pid",
            pid=frontend_pid, mode=mode, started_at=started_at,
        )

    # Phase 4 · 健康探测
    healthz_url = f"http://127.0.0.1:{backend_port}/api/healthz"
    probe = probe_mod.probe_until_ready(healthz_url)
    if not probe.ok:
        _rollback_start(settings)
        raise ServeLifecycleError(
            "serve.health_probe_timeout",
            f"backend failed to start within ~10s; see {backend_log}",
        )
    if mode == "dev":
        frontend_url = f"http://127.0.0.1:{frontend_port}/"
        if not probe_mod.probe_once(frontend_url, timeout=2.0):
            # 前端慢，再试一次更宽松窗
            time.sleep(2.0)
            if not probe_mod.probe_once(frontend_url, timeout=4.0):
                _rollback_start(settings)
                raise ServeLifecycleError(
                    "serve.frontend_failed_to_start",
                    f"frontend (pnpm dev) failed to respond on :{frontend_port}",
                )

    # Phase 5 · 输出
    backend_info = ServiceInfo(
        pid=backend_pid, port=backend_port, host=host,
        log=str(backend_log),
    )
    frontend_info = None
    if mode == "dev" and frontend_pid is not None:
        frontend_info = ServiceInfo(
            pid=frontend_pid, port=frontend_port, host=host,
            log=str(settings.logs_dir / "frontend.log"),
        )
    return StartResult(
        mode=mode,
        backend=backend_info,
        frontend=frontend_info,
        took_ms=int((time.monotonic() - t0) * 1000),
        build_ran=build_ran,
    )


def _ensure_dirs_writable(settings: Settings) -> None:
    for d in [settings.pids_dir, settings.logs_dir]:
        try:
            d.mkdir(parents=True, exist_ok=True)
            test = d / ".write-test"
            test.touch()
            test.unlink()
        except OSError as e:
            raise ServeLifecycleError(
                "serve.data_unwritable",
                f"cannot write at {d}: {e}",
            ) from e


def _check_pids_or_clean_stale(settings: Settings) -> None:
    for service in ("backend", "frontend"):
        f = settings.pids_dir / f"{service}.pid"
        state = pid_mod.read_pid_state(f, service)  # type: ignore[arg-type]
        if state.status is pid_mod.PidStateStatus.RUNNING:
            raise ServeLifecycleError(
                "serve.already_running",
                f"already running ({service} mode={state.mode}, pid={state.pid}); "
                f"use 'serve stop' or 'serve restart'",
            )
        if state.status is pid_mod.PidStateStatus.STALE:
            pid_mod.remove_pid_file(f)


def _run_build() -> None:
    proc = subprocess.run(
        ["pnpm", "--dir", "frontend", "build"], check=False
    )
    if proc.returncode != 0:
        raise ServeLifecycleError(
            "serve.build_failed",
            "frontend build failed (see output above)",
        )


def _rollback_start(settings: Settings) -> None:
    """探测失败时杀已起子进程 + 删 PID 文件。"""
    for service in ("backend", "frontend"):
        f = settings.pids_dir / f"{service}.pid"
        state = pid_mod.read_pid_state(f, service)  # type: ignore[arg-type]
        if state.pid is not None:
            try:
                proc_mod.kill_tree(state.pid, timeout=5.0)
            except (proc_mod.KillFailedError, Exception):
                pass
        pid_mod.remove_pid_file(f)
