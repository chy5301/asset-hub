import json
import sys
from typing import Any


def success_envelope(data: Any, count: int | None = None, took_ms: float | None = None) -> str:
    meta: dict[str, Any] = {}
    if count is not None:
        meta["count"] = count
    if took_ms is not None:
        meta["took_ms"] = round(took_ms, 1)
    return json.dumps(
        {"success": True, "data": data, "metadata": meta, "error": None},
        ensure_ascii=False,
        default=str,
    )


def error_envelope(message: str) -> str:
    return json.dumps(
        {"success": False, "data": None, "metadata": {}, "error": message},
        ensure_ascii=False,
    )


def print_result(data: Any, json_output: bool, *, count: int | None = None) -> None:
    if json_output:
        print(success_envelope(data, count=count))
    else:
        from rich import print as rprint
        rprint(data)


def print_error(message: str, json_output: bool, exit_code: int = 1) -> None:
    if json_output:
        print(error_envelope(message))
    else:
        from rich.console import Console
        Console(stderr=True).print(f"[red]错误:[/red] {message}")
    raise SystemExit(exit_code)
