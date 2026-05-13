import json
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any, NoReturn

from pydantic import BaseModel

from asset_hub.errors import (
    AssetHubError,
    NotFoundError,
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


def _cli_error_payload(exc: AssetHubError) -> dict:
    """CLI envelope `error` 字段内容 — v2.0 §4.2 exclude-None 序列化。

    必含 code / message；可选 hint / fields_missing / fields_invalid /
    affected_resource_id 仅在异常实例携带值（非 None）时出现。
    """
    payload: dict = {"code": type(exc).code, "message": exc.message}
    if exc.hint is not None:
        payload["hint"] = exc.hint
    if exc.fields_missing is not None:
        payload["fields_missing"] = exc.fields_missing
    if exc.fields_invalid is not None:
        payload["fields_invalid"] = exc.fields_invalid
    if exc.affected_resource_id is not None:
        payload["affected_resource_id"] = exc.affected_resource_id
    return payload


def error_envelope(message: str, *, code: str) -> str:
    """构造 CLI 错误 envelope（v1 兼容入口；新代码优先用 print_error(exc=...)）。

    仅含 code / message，不带结构化字段——结构化路径走 print_error(exc=exc) /
    _cli_error_payload(exc)。保留此函数确保旧调用站点（含测试）零改动。
    """
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
    message: str,
    json_output: bool,
    *,
    code: str,
    exit_code: int = 1,
    exc: AssetHubError | None = None,
) -> NoReturn:
    """打印错误并 raise SystemExit。

    若提供 exc：JSON 输出走 _cli_error_payload(exc)，含 hint / fields_missing
    等结构化字段（spec §4.2）。否则 fallback 到 v1 行为 {code, message}。
    text 输出始终为单行 "错误: <message>"，结构化字段仅 JSON 模式可见。
    """
    if json_output:
        if exc is not None:
            payload = _cli_error_payload(exc)
        else:
            payload = {"code": code, "message": message}
        print(json.dumps(
            {"success": False, "data": None, "metadata": {}, "error": payload},
            ensure_ascii=False,
        ))
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
    error.code 直接取自 `type(exc).code` 类属性（v2.0 §4.2，取代旧
    _DOMAIN_ERROR_CODES dict 映射）。同时把 exc 透传给 print_error，启用
    hint / fields_missing 等结构化字段输出。与 api/app.py 的 HTTP 映射对称。
    """
    try:
        yield
    except AssetHubError as e:
        code = type(e).code
        if isinstance(e, NotFoundError):
            exit_code = 3
        elif isinstance(e, ValidationError) and exit_2_on_validation:
            exit_code = 2
        else:
            exit_code = 1
        print_error(e.message, json_output, code=code, exit_code=exit_code, exc=e)
