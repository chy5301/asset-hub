import json
from collections.abc import Generator
from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from typing import overload
from uuid import UUID

import typer
from sqlmodel import Session

from asset_hub.cli.envelope import print_error
from asset_hub.db import get_engine
from asset_hub.errors import ValidationError
from asset_hub.services._common import UNSET, UnsetType


@contextmanager
def cli_session() -> Generator[Session, None, None]:
    with Session(get_engine()) as session:
        yield session


@overload
def parse_uuid(raw: str, json_output: bool) -> UUID: ...
@overload
def parse_uuid(raw: None, json_output: bool) -> None: ...


def parse_uuid(raw: str | None, json_output: bool) -> UUID | None:
    """解析 UUID 字符串，无效时以 exit_code=2 退出。`None` 透传。"""
    if raw is None:
        return None
    try:
        return UUID(raw)
    except ValueError:
        print_error(f"无效的 UUID: {raw}", json_output, code="validation", exit_code=2)


@overload
def parse_enum[E: Enum](cls: type[E], raw: str, json_output: bool) -> E: ...
@overload
def parse_enum[E: Enum](cls: type[E], raw: None, json_output: bool) -> None: ...


def parse_enum[E: Enum](cls: type[E], raw: str | None, json_output: bool) -> E | None:
    """解析枚举字符串，无效时以 exit_code=2 退出。`None` 透传。"""
    if raw is None:
        return None
    try:
        return cls(raw)
    except ValueError:
        valid = ", ".join(m.value for m in cls)
        print_error(
            f"无效的 {cls.__name__}: {raw}（允许：{valid}）",
            json_output,
            code="validation",
            exit_code=2,
        )


def parse_unset_or_value(value: str | None) -> str | None | UnsetType:
    """CLI flag → service 语义转换。

    Typer 默认 None（用户未传）→ UNSET（service 走 keep 路径，保留当前字段）
    用户传空字符串 ""（显式清空约定）→ None（service 走清空路径）
    用户传非空字符串 → 原值
    """
    if value is None:
        return UNSET
    if value == "":
        return None
    return value


# --- --fields 字段掩码 helper（spec §4.4 / v2.0 PR-2 T20+T21）---


def parse_cli_fields(fields: str | None) -> set[str] | None:
    """解析 --fields "a,b,c" → {'a','b','c'}。空/None 返回 None。"""
    if fields is None:
        return None
    parsed = {f.strip() for f in fields.split(",") if f.strip()}
    return parsed or None


def _raise_unknown_fields(
    unknown: set[str], allowed: set[str], json_output: bool
) -> None:
    """统一 unknown-field 报错路径（list / single record 共用）。"""
    msg = f"未知字段: {', '.join(sorted(unknown))}"
    print_error(
        msg,
        json_output,
        code="validation",
        exit_code=1,
        exc=ValidationError(
            msg,
            fields_invalid={f: "未知字段" for f in unknown},
            hint=f"合法字段：{', '.join(sorted(allowed))}",
        ),
    )


def filter_record_fields(
    record: dict,
    fields: set[str] | None,
    *,
    allowed: set[str],
    json_output: bool,
) -> dict:
    """按 fields 过滤单 record（dict）。

    fields=None → 原样返回。
    fields 含未知字段 → print_error 退出（exit 1）。
    """
    if fields is None:
        return record
    unknown = fields - allowed
    if unknown:
        _raise_unknown_fields(unknown, allowed, json_output)
    return {k: v for k, v in record.items() if k in fields}


def filter_list_fields(
    records: list[dict],
    fields: set[str] | None,
    *,
    allowed: set[str],
    json_output: bool,
) -> list[dict]:
    """list 版——unknown 检查放循环外。"""
    if fields is None:
        return records
    unknown = fields - allowed
    if unknown:
        _raise_unknown_fields(unknown, allowed, json_output)
    return [{k: v for k, v in r.items() if k in fields} for r in records]


def load_schema_from_file(path: Path, json_output: bool) -> dict:
    """读 --from 指定的 JSON schema 文件。失败时统一以 exit 2 退出。

    type_define / type_update 共用此 helper，避免 type_define 旧代码在 JSON
    解析失败时抛 Typer stack trace（reuse simplify F3 + 修预存 bug）。
    """
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print_error(
            f"JSON 文件读取失败：{path}（{e}）",
            json_output,
            code="validation",
            exit_code=2,
        )


# --- --help-json 双模：agent 友好的 command 元数据导出（spec §4.3）---


def _type_name(t: object) -> str:
    """Click type → JSON-friendly name。"""
    import click

    if isinstance(t, click.types.Choice):
        return f"choice({','.join(t.choices)})"
    if isinstance(t, click.types.IntParamType):
        return "int"
    if isinstance(t, click.types.FloatParamType):
        return "float"
    if isinstance(t, click.types.BoolParamType):
        return "bool"
    if isinstance(t, click.types.UUIDParameterType):
        return "uuid"
    if isinstance(t, click.types.Path):
        return "path"
    if isinstance(t, click.types.StringParamType):
        return "str"
    return type(t).__name__


def _default_value(d: object) -> object:
    """Click 默认值 → JSON-safe。callable / sentinel / Enum / UnsetType → JSON-safe form。"""
    if d is None:
        return None
    if d is ... or isinstance(d, UnsetType):
        return None
    if callable(d):
        return None
    if isinstance(d, Enum):
        return d.value
    # 基础类型 / list / dict 直接放行；其他 fallback 到 str
    if isinstance(d, str | int | float | bool | list | dict):
        return d
    return str(d)


# --- --help-json param enrichment registry ---


_PARAM_ENRICHMENTS: dict[tuple[str, str], dict[str, object]] = {}


def register_param_enrichment(
    command_path: str, param_name: str, extra: dict[str, object]
) -> None:
    """为指定 (command_path, param_name) 注册附加元数据，--help-json 输出时浅合并。

    command_path: 完整 typer / click 命令路径，如 "asset-hub type define"。
    param_name:   首个 long option / argument metavar，如 "--fields"。
    extra:        浅合并到 param dict（同名 key 覆盖默认）。
    """
    _PARAM_ENRICHMENTS[(command_path, param_name)] = extra


def print_help_json(ctx: typer.Context) -> None:
    """输出当前 command 的 JSON 结构化 help（agent 友好）。spec §4.3。

    用法：在 --help-json eager callback 内调，紧接 typer.Exit(0)。
    """
    import click

    cmd: click.Command = ctx.command

    params = []
    seen: set[str] = set()
    for p in cmd.params:
        # 跳过我们自己注入的 --help-json eager flag，输出更干净
        if "--help-json" in getattr(p, "opts", []):
            continue
        # 名称：优先取首个 long option / argument metavar
        opts = list(getattr(p, "opts", []))
        name = opts[0] if opts else getattr(p, "name", "")
        if name in seen:
            continue
        seen.add(name)
        entry: dict[str, object] = {
            "name": name,
            "type": _type_name(p.type),
            "default": _default_value(p.default),
            "required": bool(getattr(p, "required", False)),
            "help": getattr(p, "help", None) or "",
        }
        cmd_path = ctx.command_path or cmd.name or ""
        extra = _PARAM_ENRICHMENTS.get((cmd_path, name))
        if extra:
            entry.update(extra)
        params.append(entry)

    payload = {
        "command": ctx.command_path or cmd.name or "",
        "help": (cmd.help or "").strip(),
        "params": params,
        "examples": [],  # TODO v2.1：从 command docstring 末 "Examples:" 段提取
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _help_json_click_callback(ctx, param, value):  # type: ignore[no-untyped-def]
    """Click eager-option callback：检测 --help-json 后输出 JSON 元数据并退出。"""
    if value:
        print_help_json(ctx)
        ctx.exit(0)


def inject_help_json_recursive(cmd) -> None:  # type: ignore[no-untyped-def]
    """递归遍历 click Command/Group 树，在每个 leaf command 注入 --help-json eager flag。

    设计取舍（spec §4.3 实现备忘）：
      Typer 的 group-level callback 不支持 `<group> <sub> --flag` 顺序（Click 限制：
      group option 必须出现在 subcommand 之前），所以全局 root callback 方案行不通。
      改为构造时把 --help-json 注入到每个 leaf click Command 的 params 上——CliRunner
      可测，且不需要逐 command 手改源码。
    """
    import click

    if hasattr(cmd, "commands") and cmd.commands:
        # Group：递归 + 给 group 自身也加一份（支持 `asset --help-json`）
        for sub in cmd.commands.values():
            inject_help_json_recursive(sub)
    # Leaf command 或 group：附加 eager flag，已存在则跳过
    if not any("--help-json" in getattr(p, "opts", []) for p in cmd.params):
        cmd.params.append(
            click.Option(
                ["--help-json"],
                is_flag=True,
                expose_value=False,
                is_eager=True,
                callback=_help_json_click_callback,
                hidden=True,
                help="Output structured JSON help for this command (agent-friendly).",
            )
        )
