import json
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any, NoReturn

from pydantic import BaseModel

from asset_hub.errors import (
    ConflictError,
    DuplicateError,
    NotFoundError,
    StateError,
    ValidationError,
)


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


def print_error(message: str, json_output: bool, exit_code: int = 1) -> NoReturn:
    if json_output:
        print(error_envelope(message))
    else:
        from rich.console import Console
        Console(stderr=True).print(f"[red]错误:[/red] {message}")
    raise SystemExit(exit_code)


def print_dry_run(payload: Any, json_output: bool, *, message: str) -> NoReturn:
    if json_output:
        print(success_envelope(payload))
    else:
        from rich import print as rprint
        rprint(f"[yellow]dry-run:[/yellow] {message}")
    raise SystemExit(10)


def to_json_dict(schema_cls: type[BaseModel], obj: Any) -> dict:
    return schema_cls.model_validate(obj).model_dump(mode="json")


@contextmanager
def handle_domain_errors(json_output: bool) -> Generator[None, None, None]:
    """把域异常按 CLI 退出码契约翻译成 print_error。

    退出码：NotFoundError → 3；ConflictError/DuplicateError/ValidationError/StateError → 1。
    与 api/app.py 的 HTTP 映射对称，避免每个命令重复 try/except。
    """
    try:
        yield
    except NotFoundError as e:
        print_error(str(e), json_output, exit_code=3)
    except (ConflictError, DuplicateError, ValidationError, StateError) as e:
        print_error(str(e), json_output, exit_code=1)
