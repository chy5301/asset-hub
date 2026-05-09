import json
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any, NoReturn

from pydantic import BaseModel

from asset_hub.errors import (
    AssetHubError,
    ConflictError,
    DuplicateError,
    IllegalTransitionError,
    NotFoundError,
    StateError,
    ValidationError,
)

_DOMAIN_ERROR_CODES: dict[type[AssetHubError], str] = {
    NotFoundError: "not_found",
    DuplicateError: "duplicate",
    ValidationError: "validation",
    StateError: "state_conflict",
    ConflictError: "conflict",
    IllegalTransitionError: "illegal_transition",
}


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


def error_envelope(message: str, *, code: str) -> str:
    return json.dumps(
        {
            "success": False,
            "data": None,
            "metadata": {},
            "error": {"code": code, "message": message},
        },
        ensure_ascii=False,
    )


def print_result(data: Any, json_output: bool, *, count: int | None = None) -> None:
    if json_output:
        print(success_envelope(data, count=count))
    else:
        from rich import print as rprint
        rprint(data)


def print_error(
    message: str, json_output: bool, *, code: str, exit_code: int = 1
) -> NoReturn:
    if json_output:
        print(error_envelope(message, code=code))
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
def handle_domain_errors(
    json_output: bool,
    *,
    exit_2_on_validation: bool = False,
) -> Generator[None, None, None]:
    """把域异常按 CLI 退出码契约翻译成 print_error。

    退出码：NotFoundError → 3；ValidationError → 1（默认）/ 2（exit_2_on_validation=True）；
    其余 ConflictError/DuplicateError/IllegalTransitionError/StateError → 1。
    error.code 由 _DOMAIN_ERROR_CODES 显式映射，避与状态机歧义（StateError → state_conflict）。
    与 api/app.py 的 HTTP 映射对称。
    """
    try:
        yield
    except AssetHubError as e:
        code = _DOMAIN_ERROR_CODES[type(e)]
        if isinstance(e, NotFoundError):
            exit_code = 3
        elif isinstance(e, ValidationError) and exit_2_on_validation:
            exit_code = 2
        else:
            exit_code = 1
        print_error(str(e), json_output, code=code, exit_code=exit_code)
