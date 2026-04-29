from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Literal

import psutil

# cmdline 校验关键词（两 token 必须同时命中）
BACKEND_CMDLINE_TOKENS = ("uvicorn", "asset_hub.api.app")
FRONTEND_CMDLINE_TOKENS = ("pnpm", "dev")


class PidStateStatus(StrEnum):
    NONE = "none"
    RUNNING = "running"
    STALE = "stale"


@dataclass
class PidFileContent:
    pid: int
    mode: Literal["dev", "prod"] | None
    started_at: datetime | None


@dataclass
class PidState:
    service: Literal["backend", "frontend"]
    file_exists: bool
    pid: int | None
    mode: Literal["dev", "prod"] | None
    started_at: datetime | None
    process_alive: bool
    cmdline_match: bool
    status: PidStateStatus


def write_pid_file(
    path: Path,
    *,
    pid: int,
    mode: Literal["dev", "prod"],
    started_at: datetime | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{pid}", f"mode={mode}"]
    if started_at is not None:
        ts = started_at.replace(microsecond=0).isoformat()
        if ts.endswith("+00:00"):
            ts = ts[:-6] + "Z"
        lines.append(f"started_at={ts}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_pid_file(path: Path) -> PidFileContent | None:
    if not path.exists():
        return None
    raw = path.read_text(encoding="utf-8").strip().splitlines()
    if not raw:
        raise ValueError("empty PID file")
    pid = int(raw[0].strip())  # ValueError if corrupt

    mode: Literal["dev", "prod"] | None = None
    started_at: datetime | None = None
    for line in raw[1:]:
        if line.startswith("mode="):
            v = line.split("=", 1)[1].strip()
            if v in ("dev", "prod"):
                mode = v  # type: ignore[assignment]
        elif line.startswith("started_at="):
            v = line.split("=", 1)[1].strip()
            try:
                if v.endswith("Z"):
                    v = v[:-1] + "+00:00"
                started_at = datetime.fromisoformat(v)
            except ValueError:
                started_at = None
    return PidFileContent(pid=pid, mode=mode, started_at=started_at)


def _cmdline_tokens_for(service: Literal["backend", "frontend"]) -> tuple[str, ...]:
    return BACKEND_CMDLINE_TOKENS if service == "backend" else FRONTEND_CMDLINE_TOKENS


def _check_cmdline(pid: int, tokens: tuple[str, ...]) -> bool:
    try:
        cmdline_str = " ".join(psutil.Process(pid).cmdline())
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False
    return all(t in cmdline_str for t in tokens)


def read_pid_state(
    path: Path,
    service: Literal["backend", "frontend"],
) -> PidState:
    if not path.exists():
        return PidState(
            service=service,
            file_exists=False,
            pid=None,
            mode=None,
            started_at=None,
            process_alive=False,
            cmdline_match=False,
            status=PidStateStatus.NONE,
        )

    try:
        content = read_pid_file(path)
        assert content is not None
    except ValueError:
        return PidState(
            service=service,
            file_exists=True,
            pid=None,
            mode=None,
            started_at=None,
            process_alive=False,
            cmdline_match=False,
            status=PidStateStatus.STALE,
        )

    pid = content.pid
    if not psutil.pid_exists(pid):
        return PidState(
            service=service,
            file_exists=True,
            pid=pid,
            mode=content.mode,
            started_at=content.started_at,
            process_alive=False,
            cmdline_match=False,
            status=PidStateStatus.STALE,
        )

    try:
        proc_status = psutil.Process(pid).status()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return PidState(
            service=service,
            file_exists=True,
            pid=pid,
            mode=content.mode,
            started_at=content.started_at,
            process_alive=False,
            cmdline_match=False,
            status=PidStateStatus.STALE,
        )

    if proc_status == psutil.STATUS_ZOMBIE:
        return PidState(
            service=service,
            file_exists=True,
            pid=pid,
            mode=content.mode,
            started_at=content.started_at,
            process_alive=False,
            cmdline_match=False,
            status=PidStateStatus.STALE,
        )

    cmdline_ok = _check_cmdline(pid, _cmdline_tokens_for(service))
    if not cmdline_ok:
        return PidState(
            service=service,
            file_exists=True,
            pid=pid,
            mode=content.mode,
            started_at=content.started_at,
            process_alive=True,
            cmdline_match=False,
            status=PidStateStatus.STALE,
        )

    return PidState(
        service=service,
        file_exists=True,
        pid=pid,
        mode=content.mode,
        started_at=content.started_at,
        process_alive=True,
        cmdline_match=True,
        status=PidStateStatus.RUNNING,
    )


def remove_pid_file(path: Path) -> None:
    if path.exists():
        path.unlink()
