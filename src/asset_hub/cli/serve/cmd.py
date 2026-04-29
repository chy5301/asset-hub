from __future__ import annotations

import sys
from typing import Annotated

import typer

from asset_hub.cli.serve import lifecycle
from asset_hub.cli.serve import logs as logs_mod
from asset_hub.cli.serve.lifecycle import ServeLifecycleError
from asset_hub.cli.serve.output import (
    render_json_envelope,
    render_plain_start,
    render_plain_status,
    render_plain_stop,
)
from asset_hub.config import Settings

serve_app = typer.Typer(name="serve", help="管理后端 + 前端服务生命周期", no_args_is_help=True)


def _emit_success(*, json_out: bool, plain_text: str = "", data=None, metadata=None,
                  exit_code: int = 0):
    if json_out:
        out = render_json_envelope(success=True, data=data, metadata=metadata)
        print(out)
    elif plain_text:
        print(plain_text)
    raise typer.Exit(code=exit_code)


def _emit_error(*, json_out: bool, plain_text: str, error: dict, metadata=None,
                exit_code: int = 1):
    if json_out:
        out = render_json_envelope(success=False, error=error, metadata=metadata)
        print(out)
    else:
        print(plain_text, file=sys.stderr)
    raise typer.Exit(code=exit_code)


@serve_app.command("start")
def start(
    mode: Annotated[str, typer.Option("--mode", help="启动模式 (dev|prod)")] = "prod",
    skip_build: Annotated[bool, typer.Option("--skip-build", help="跳过自动 build")] = False,
    port: Annotated[int | None, typer.Option("--port", help="覆盖后端端口")] = None,
    frontend_port: Annotated[int | None, typer.Option("--frontend-port", help="覆盖前端端口")] = None,
    host: Annotated[str | None, typer.Option("--host", help="覆盖后端 host")] = None,
    json_out: Annotated[bool, typer.Option("--json", help="JSON 信封输出")] = False,
):
    """启动服务（默认 prod 模式）。"""
    if mode not in ("dev", "prod"):
        _emit_error(
            json_out=json_out,
            plain_text=f"✗ Invalid --mode '{mode}' (expected dev|prod)",
            error={"code": "serve.usage", "message": f"invalid --mode '{mode}'"},
            exit_code=2,
        )
    try:
        result = lifecycle.start_service(
            mode=mode,  # type: ignore[arg-type]
            skip_build=skip_build,
            port_override=port,
            frontend_port_override=frontend_port,
            host_override=host,
        )
    except ServeLifecycleError as e:
        _emit_error(
            json_out=json_out,
            plain_text=f"✗ {e.message}",
            error={"code": e.code, "message": e.message},
            exit_code=1,
        )

    _emit_success(
        json_out=json_out,
        plain_text=render_plain_start(result),
        data=result.to_dict(),
        metadata=result.metadata(),
    )


@serve_app.command("stop")
def stop(
    json_out: Annotated[bool, typer.Option("--json", help="JSON 信封输出")] = False,
):
    """停止当前在跑的服务（幂等）。"""
    try:
        result = lifecycle.stop_service()
    except ServeLifecycleError as e:
        _emit_error(
            json_out=json_out,
            plain_text=f"✗ {e.message}",
            error={"code": e.code, "message": e.message},
            exit_code=1,
        )

    _emit_success(
        json_out=json_out,
        plain_text=render_plain_stop(result),
        data=result.to_dict(),
        metadata={},
    )


@serve_app.command("status")
def status(
    json_out: Annotated[bool, typer.Option("--json", help="JSON 信封输出")] = False,
    no_probe: Annotated[bool, typer.Option("--no-probe", help="跳过 HTTP 健康探测")] = False,
):
    """查询服务状态（含 HTTP 健康探测）。"""
    report = lifecycle.status_service(no_probe=no_probe)
    _emit_success(
        json_out=json_out,
        plain_text=render_plain_status(report),
        data=report.to_dict(),
        metadata=report.metadata(),
    )


@serve_app.command("restart")
def restart(
    mode: Annotated[str | None, typer.Option("--mode", help="显式指定模式 (dev|prod)")] = None,
    skip_build: Annotated[bool, typer.Option("--skip-build")] = False,
    port: Annotated[int | None, typer.Option("--port")] = None,
    frontend_port: Annotated[int | None, typer.Option("--frontend-port")] = None,
    host: Annotated[str | None, typer.Option("--host")] = None,
    json_out: Annotated[bool, typer.Option("--json", help="JSON 信封输出")] = False,
):
    """重启服务（自动推断 mode；如无法推断需 --mode）。"""
    if mode is not None and mode not in ("dev", "prod"):
        _emit_error(
            json_out=json_out,
            plain_text=f"✗ Invalid --mode '{mode}' (expected dev|prod)",
            error={"code": "serve.usage", "message": f"invalid --mode '{mode}'"},
            exit_code=2,
        )
    try:
        stop_res, start_res = lifecycle.restart_service(
            mode_override=mode,  # type: ignore[arg-type]
            skip_build=skip_build,
            port_override=port,
            frontend_port_override=frontend_port,
            host_override=host,
        )
    except ServeLifecycleError as e:
        _emit_error(
            json_out=json_out,
            plain_text=f"✗ {e.message}",
            error={"code": e.code, "message": e.message},
            exit_code=1,
        )

    plain = render_plain_stop(stop_res) + "\n" + render_plain_start(start_res)
    _emit_success(
        json_out=json_out,
        plain_text=plain,
        data={"stop": stop_res.to_dict(), "start": start_res.to_dict()},
        metadata=start_res.metadata(),
    )


@serve_app.command("logs")
def logs(
    service: Annotated[str, typer.Option("--service", help="日志源 (backend|frontend|all)")] = "backend",
    lines: Annotated[int, typer.Option("--lines", help="一次性 tail 行数")] = 200,
    follow: Annotated[bool, typer.Option("--follow", help="持续 tail（Ctrl+C 终止）")] = False,
    json_out: Annotated[bool, typer.Option("--json", help="JSON 信封输出（仅一次性模式）")] = False,
):
    """查看服务日志（默认 backend，最近 200 行）。"""
    if service not in ("backend", "frontend", "all"):
        _emit_error(
            json_out=json_out,
            plain_text=f"✗ Invalid --service '{service}' (expected backend|frontend|all)",
            error={"code": "serve.usage", "message": f"invalid --service '{service}'"},
            exit_code=2,
        )

    if follow:
        if json_out:
            print("warning: --json ignored in --follow mode", file=sys.stderr)
        if service == "all":
            print("warning: --follow only supports single service; using backend", file=sys.stderr)
            service = "backend"
        path = Settings().logs_dir / f"{service}.log"
        if not path.exists():
            print(f"- No logs available for {service}")
            raise typer.Exit(code=0)
        try:
            for line in logs_mod.follow_log(path):
                sys.stdout.write(line)
                sys.stdout.flush()
        except KeyboardInterrupt:
            pass
        raise typer.Exit(code=0)

    out = lifecycle.logs_for_service(
        service=service,  # type: ignore[arg-type]
        lines=lines,
    )
    if all(len(v) == 0 for v in out.values()):
        if json_out:
            payload = {"service": service, "lines": [], "truncated": False}
            print(render_json_envelope(success=True, data=payload, metadata={}))
        else:
            print(f"- No logs available for {service}")
        raise typer.Exit(code=0)

    if json_out:
        if service == "all":
            payload = {"services": out}
        else:
            payload = {"service": service, "lines": out[service], "truncated": False}
        print(render_json_envelope(success=True, data=payload, metadata={}))
        raise typer.Exit(code=0)

    text_parts = []
    if service == "all":
        for s_name, s_lines in out.items():
            for ln in s_lines:
                text_parts.append(f"[{s_name}] {ln}")
    else:
        text_parts = out[service]
    print("\n".join(text_parts))
    raise typer.Exit(code=0)
