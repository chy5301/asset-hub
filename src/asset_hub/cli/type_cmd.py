import json
from pathlib import Path
from typing import Annotated

import typer

from asset_hub.api.schemas.asset_type import TypeRead
from asset_hub.cli.deps import cli_session, parse_uuid
from asset_hub.cli.envelope import (
    handle_domain_errors,
    print_dry_run,
    print_error,
    print_result,
    to_json_dict,
)
from asset_hub.services.asset_type import TypeService

type_app = typer.Typer(name="type", help="资产类型管理", no_args_is_help=True)


@type_app.command("define")
def type_define(
    name: Annotated[str | None, typer.Option(help="类型名称")] = None,
    prefix: Annotated[str | None, typer.Option("--prefix", help="编号前缀（2-4 大写字母，如 NB）")] = None,
    description: Annotated[str | None, typer.Option(help="类型描述")] = None,
    fields: Annotated[str | None, typer.Option(help="自定义字段 JSON 数组")] = None,
    from_file: Annotated[Path | None, typer.Option("--from", help="JSON schema 文件路径")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="JSON 信封输出")] = False,
) -> None:
    """定义新的资产类型。"""
    if from_file is not None:
        schema = json.loads(from_file.read_text(encoding="utf-8"))
        name = schema["name"]
        prefix = schema.get("code_prefix") or schema.get("prefix") or prefix
        description = schema.get("description")
        custom_fields = schema.get("custom_fields", [])
    elif name is not None:
        custom_fields = json.loads(fields) if fields else []
    else:
        print_error("必须提供 --name 或 --from", json_output, exit_code=2)

    if not prefix:
        print_error("必须提供 --prefix（2-4 大写字母）", json_output, exit_code=2)

    with cli_session() as session, handle_domain_errors(json_output):
        svc = TypeService(session)
        t = svc.create_type(
            name=name,
            code_prefix=prefix,
            description=description,
            custom_fields=custom_fields,
        )
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


@type_app.command("delete")
def type_delete(
    type_id: Annotated[str, typer.Argument(help="要删除的 AssetType id")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="跳过二次确认（--json 模式自动跳过）")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="预览不真删")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="JSON 信封输出")] = False,
) -> None:
    """删除 AssetType（有引用的资产时严格拒绝）。"""
    uid = parse_uuid(type_id, json_output)

    with cli_session() as session, handle_domain_errors(json_output):
        svc = TypeService(session)
        t = svc.get_type(uid)  # 先校验存在 — NotFoundError → exit 3
        ref_count = svc.repo.count_assets_by_type(uid)

        if dry_run:
            if ref_count > 0:
                # 有引用 — 真删会失败；dry-run 应同样信号失败
                print_error(
                    f"该类型仍有 {ref_count} 个资产引用，dry-run 报告将会失败（实际删除会被拒绝）",
                    json_output,
                    exit_code=1,
                )
            payload = {
                "would_delete": {
                    "id": str(uid),
                    "name": t.name,
                    "code_prefix": t.code_prefix,
                },
                "reference_count": ref_count,
            }
            print_dry_run(
                payload,
                json_output,
                message=f"将删除 type '{t.name}' (引用资产数: {ref_count})",
            )

        if ref_count == 0 and not yes and not json_output:
            confirm = typer.confirm(f"确认删除 type '{t.name}' ({t.code_prefix})？")
            if not confirm:
                print_error("用户取消", json_output, exit_code=1)

        # delete_type 内部再校验 ref，>0 时抛 ConflictError → envelope → exit 1
        svc.delete_type(uid)
        deleted_payload = {"deleted_id": str(uid), "name": t.name}

    print_result(deleted_payload, json_output)
