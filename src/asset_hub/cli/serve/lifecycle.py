from __future__ import annotations

import os
import shutil
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from asset_hub.cli.serve import logs as logs_mod
from asset_hub.cli.serve import pid as pid_mod
from asset_hub.cli.serve import probe as probe_mod
from asset_hub.cli.serve import proc as proc_mod
from asset_hub.cli.serve.output import (
    ServiceInfo,
    StartResult,
    StatusReport,
    StopResult,
)
from asset_hub.config import Settings


class ServeLifecycleError(Exception):
    """raise 时携带 (code, message) 给上层 cmd 转 exit code + envelope error。"""

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

    # Phase 1 · 构建（仅 prod；默认总是 rebuild 确保拿到最新前端代码，--skip-build 显式跳过）
    build_ran = False
    if mode == "prod":
        dist_index = Path("frontend/dist/index.html")
        if skip_build:
            if not dist_index.exists():
                raise ServeLifecycleError(
                    "serve.dist_missing",
                    "frontend/dist not found; omit --skip-build or run 'pnpm --dir frontend build'",
                )
        else:
            _run_build()
            build_ran = True

    # Phase 2 · 日志轮转
    backend_log = settings.logs_dir / "backend.log"
    logs_mod.rotate_log(backend_log)
    if mode == "dev":
        logs_mod.rotate_log(settings.logs_dir / "frontend.log")

    # Phase 3 · 启动子进程（uvicorn 子进程继承 ASSET_HUB_MODE 环境变量；api/app.py 据此决定 SPA fallback）
    os.environ["ASSET_HUB_MODE"] = mode

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
    spawned: list[tuple[Literal["backend", "frontend"], int]] = [("backend", backend_pid)]
    if frontend_pid is not None:
        spawned.append(("frontend", frontend_pid))
    healthz_url = f"http://127.0.0.1:{backend_port}/api/healthz"
    probe = probe_mod.probe_until_ready(healthz_url)
    if not probe.ok:
        _rollback_spawned(settings, spawned)
        raise ServeLifecycleError(
            "serve.health_probe_timeout",
            f"backend failed to start within ~10s; see {backend_log}",
        )
    if mode == "dev":
        # frontend 用 localhost 而非 127.0.0.1：Vite 8.x dev 默认只绑 IPv6 ::1，
        # IPv4 127.0.0.1 会被拒绝；localhost 由 OS 解析。后端走 127.0.0.1 因为
        # uvicorn 显式 --host 绑 IPv4。status / output 同此约定。
        frontend_url = f"http://localhost:{frontend_port}/"
        if not probe_mod.probe_once(frontend_url, timeout=2.0):
            # 前端慢，再试一次更宽松窗
            time.sleep(2.0)
            if not probe_mod.probe_once(frontend_url, timeout=4.0):
                _rollback_spawned(settings, spawned)
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
        # frontend host 用 "localhost"，见 Phase 4 注释
        frontend_info = ServiceInfo(
            pid=frontend_pid, port=frontend_port, host="localhost",
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
    # Windows pnpm 是 .cmd/.ps1 wrapper，subprocess 不解析 PATHEXT，必须用 which 显式解析
    pnpm = shutil.which("pnpm")
    if pnpm is None:
        raise ServeLifecycleError(
            "serve.build_failed", "pnpm not found on PATH"
        )
    proc = subprocess.run(
        [pnpm, "--dir", "frontend", "build"], check=False
    )
    if proc.returncode != 0:
        raise ServeLifecycleError(
            "serve.build_failed",
            "frontend build failed (see output above)",
        )


def _rollback_spawned(
    settings: Settings,
    spawned: list[tuple[Literal["backend", "frontend"], int]],
) -> None:
    """探测失败时直接杀刚刚 spawn 的子进程 + 删对应 PID 文件。

    避免重读 PID 文件 + 重复 psutil 调用（PID 是我们刚 spawn 的，cmdline_match
    隐含为真）。SIGKILL 失败时静默吞错——rollback 是 best-effort，让用户看到
    原始探测超时错误而非二次错误。
    """
    for service, pid in spawned:
        try:
            proc_mod.kill_tree(pid, timeout=5.0)
        except proc_mod.KillFailedError:
            pass
        pid_mod.remove_pid_file(settings.pids_dir / f"{service}.pid")


def stop_service() -> StopResult:
    settings = Settings()
    result = StopResult()
    for service in ("backend", "frontend"):
        f = settings.pids_dir / f"{service}.pid"
        state = pid_mod.read_pid_state(f, service)  # type: ignore[arg-type]
        if state.status is pid_mod.PidStateStatus.NONE:
            continue
        if state.status is pid_mod.PidStateStatus.STALE:
            result.stale_cleaned.append(
                f"{service} pid={state.pid} not alive"
                if state.pid is not None
                else f"{service} corrupt PID file"
            )
            pid_mod.remove_pid_file(f)
            continue
        # status == RUNNING
        try:
            method = proc_mod.kill_tree(state.pid, timeout=5.0)  # type: ignore[arg-type]
        except proc_mod.KillFailedError as e:
            raise ServeLifecycleError(
                "serve.kill_failed",
                f"failed to kill {service} pid={state.pid}: {e}; "
                "manual cleanup required (PID file kept)",
            ) from e
        result.stopped.append({
            "service": service, "pid": state.pid, "method": method.value,
        })
        pid_mod.remove_pid_file(f)
    return result


def status_service(*, no_probe: bool) -> StatusReport:
    t0 = time.monotonic()
    settings = Settings()
    backend_state = pid_mod.read_pid_state(
        settings.pids_dir / "backend.pid", "backend"
    )
    frontend_state = pid_mod.read_pid_state(
        settings.pids_dir / "frontend.pid", "frontend"
    )

    if backend_state.status is pid_mod.PidStateStatus.NONE:
        return StatusReport(
            running=False, mode=None, backend=None, frontend=None,
            probed=False, took_ms=int((time.monotonic() - t0) * 1000),
        )

    mode = backend_state.mode
    if mode is None:
        # fallback: frontend.pid 存在 → dev
        mode = "dev" if frontend_state.file_exists else "prod"

    backend_info = _build_status_info(
        backend_state,
        no_probe=no_probe, port_for_probe=settings.backend_port,
    )
    frontend_info = None
    if mode == "dev" and frontend_state.status is not pid_mod.PidStateStatus.NONE:
        frontend_info = _build_status_info(
            frontend_state,
            no_probe=no_probe, port_for_probe=settings.frontend_port,
        )
    return StatusReport(
        running=backend_state.status is pid_mod.PidStateStatus.RUNNING,
        mode=mode,
        backend=backend_info,
        frontend=frontend_info,
        probed=not no_probe,
        took_ms=int((time.monotonic() - t0) * 1000),
    )


def _build_status_info(state, *, no_probe: bool, port_for_probe: int):
    if state.status is pid_mod.PidStateStatus.STALE:
        return {"status": "stale", "pid": state.pid, "port": None,
                "uptime_sec": 0, "healthy": False}
    uptime = 0
    if state.started_at is not None:
        uptime = int((datetime.now(UTC) - state.started_at).total_seconds())
    healthy = False
    if not no_probe:
        # frontend 用 localhost / backend 用 127.0.0.1，详见 start_service 注释
        url = (
            f"http://127.0.0.1:{port_for_probe}/api/healthz"
            if state.service == "backend"
            else f"http://localhost:{port_for_probe}/"
        )
        healthy = probe_mod.probe_once(url, timeout=2.0)
    return {
        "status": "running",
        "pid": state.pid,
        "port": port_for_probe,
        "uptime_sec": uptime,
        "healthy": healthy,
    }


def restart_service(
    *,
    mode_override: Literal["dev", "prod"] | None,
    skip_build: bool,
    port_override: int | None,
    frontend_port_override: int | None,
    host_override: str | None,
) -> tuple[StopResult, StartResult]:
    settings = Settings()
    backend_state = pid_mod.read_pid_state(
        settings.pids_dir / "backend.pid", "backend"
    )
    frontend_state = pid_mod.read_pid_state(
        settings.pids_dir / "frontend.pid", "frontend"
    )

    inferred_mode: Literal["dev", "prod"] | None = backend_state.mode
    if inferred_mode is None and backend_state.status is not pid_mod.PidStateStatus.NONE:
        inferred_mode = "dev" if frontend_state.file_exists else "prod"

    target_mode = mode_override or inferred_mode
    if target_mode is None:
        raise ServeLifecycleError(
            "serve.mode_required",
            "cannot infer mode from PID files; specify --mode dev|prod",
        )

    stop_result = stop_service()
    start_result = start_service(
        mode=target_mode,
        skip_build=skip_build,
        port_override=port_override,
        frontend_port_override=frontend_port_override,
        host_override=host_override,
    )
    return stop_result, start_result


def logs_for_service(
    *,
    service: Literal["backend", "frontend", "all"],
    lines: int,
) -> dict[str, list[str]]:
    settings = Settings()
    out: dict[str, list[str]] = {}
    services = ["backend", "frontend"] if service == "all" else [service]
    for s in services:
        path = settings.logs_dir / f"{s}.log"
        out[s] = logs_mod.tail_lines(path, lines)
    return out
