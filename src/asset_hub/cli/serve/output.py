from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class ServiceInfo:
    pid: int
    port: int
    host: str
    log: str

    def to_dict(self) -> dict[str, Any]:
        return {"pid": self.pid, "port": self.port, "host": self.host, "log": self.log}


@dataclass
class StartResult:
    mode: Literal["dev", "prod"]
    backend: ServiceInfo | None
    frontend: ServiceInfo | None
    took_ms: int
    build_ran: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "backend": self.backend.to_dict() if self.backend else None,
            "frontend": self.frontend.to_dict() if self.frontend else None,
        }

    def metadata(self) -> dict[str, Any]:
        return {"took_ms": self.took_ms, "build_ran": self.build_ran}


@dataclass
class StopResult:
    stopped: list[dict[str, Any]] = field(default_factory=list)
    stale_cleaned: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"stopped": self.stopped, "stale_cleaned": self.stale_cleaned}


@dataclass
class StatusReport:
    running: bool
    mode: Literal["dev", "prod"] | None
    backend: dict[str, Any] | None
    frontend: dict[str, Any] | None
    probed: bool
    took_ms: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "running": self.running,
            "mode": self.mode,
            "backend": self.backend,
            "frontend": self.frontend,
        }

    def metadata(self) -> dict[str, Any]:
        return {"took_ms": self.took_ms, "probed": self.probed}


def render_plain_start(result: StartResult) -> str:
    lines = []
    if result.backend:
        b = result.backend
        lines.append(
            f"✓ Backend started     pid={b.pid}  http://{b.host}:{b.port}  mode={result.mode}"
        )
        lines.append(f"  {b.log}")
    if result.frontend:
        f = result.frontend
        lines.append(f"✓ Frontend started    pid={f.pid}  http://{f.host}:{f.port}")
    return "\n".join(lines)


def render_plain_stop(result: StopResult) -> str:
    if not result.stopped and not result.stale_cleaned:
        return "- Not running"
    lines = []
    for cleaned in result.stale_cleaned:
        lines.append(f"! Stale PID files cleaned ({cleaned})")
    if not result.stopped and result.stale_cleaned:
        lines.append("- Not running")
    for s in result.stopped:
        if s.get("method") == "sigkill":
            lines.append(
                f"! {s['service'].capitalize()} stopped via SIGKILL  pid={s['pid']}  (SIGTERM timeout 5s)"
            )
        else:
            lines.append(f"✓ {s['service'].capitalize()} stopped     pid={s['pid']}")
    return "\n".join(lines)


def render_plain_status(report: StatusReport) -> str:
    if not report.running:
        return "- Not running"

    header = "SERVICE   STATUS    PID    PORT  MODE  UPTIME    HEALTHY"
    lines = [header]
    for service_name, info in [
        ("backend", report.backend),
        ("frontend", report.frontend),
    ]:
        if info is None:
            lines.append(f"{service_name:<9} -         -      -     -     -         -")
            continue
        uptime = _fmt_uptime(info.get("uptime_sec", 0))
        healthy = "✓" if info.get("healthy") else "✗"
        lines.append(
            f"{service_name:<9} {info['status']:<9} {info['pid']:<6} {info['port']:<5} "
            f"{(report.mode or '-'):<5} {uptime:<9} {healthy}"
        )
    return "\n".join(lines)


def _fmt_uptime(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m"
    h, m = divmod(seconds // 60, 60)
    return f"{h}h {m}m"
