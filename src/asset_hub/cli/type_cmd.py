import json
from pathlib import Path
from typing import Annotated

import typer

from asset_hub.api.schemas.asset_type import TypeRead
from asset_hub.cli.deps import cli_session, parse_uuid
from asset_hub.cli.envelope import (
    handle_domain_errors,
    print_error,
    print_result,
    to_json_dict,
)
from asset_hub.services.asset_type import TypeService

type_app = typer.Typer(name="type", help="资产类型管理", no_args_is_help=True)


@type_app.command("define")
def type_define(
    name: Annotated[str | None, typer.Option(help="类型名称")] = None,
    description: Annotated[str | None, typer.Option(help="类型描述")] = None,
    fields: Annotated[str | None, typer.Option(help="自定义字段 JSON 数组")] = None,
    from_file: Annotated[Path | None, typer.Option("--from", help="JSON schema 文件路径")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="JSON 信封输出")] = False,
) -> None:
    """定义新的资产类型。"""
    if from_file is not None:
        schema = json.loads(from_file.read_text(encoding="utf-8"))
        name = schema["name"]
        description = schema.get("description")
        custom_fields = schema.get("custom_fields", [])
    elif name is not None:
        custom_fields = json.loads(fields) if fields else []
    else:
        print_error("必须提供 --name 或 --from", json_output, exit_code=2)

    with cli_session() as session, handle_domain_errors(json_output):
        svc = TypeService(session)
        t = svc.create_type(name=name, description=description, custom_fields=custom_fields)
    print_result(to_json_dict(TypeRead, t), json_output)


@type_app.command("list")
def type_list(
    json_output: Annotated[bool, typer.Option("--json", help="JSON 信封输出")] = False,
) -> None:
    """列出所有资产类型。"""
    with cli_session() as session:
        svc = TypeService(session)
        types = svc.list_types()
    data = [to_json_dict(TypeRead, t) for t in types]
    print_result(data, json_output, count=len(data))


@type_app.command("show")
def type_show(
    type_id: Annotated[str, typer.Argument(help="类型 UUID")],
    json_output: Annotated[bool, typer.Option("--json", help="JSON 信封输出")] = False,
) -> None:
    """查看单个资产类型详情。"""
    uid = parse_uuid(type_id, json_output)

    with cli_session() as session, handle_domain_errors(json_output):
        svc = TypeService(session)
        t = svc.get_type(uid)
    print_result(to_json_dict(TypeRead, t), json_output)
