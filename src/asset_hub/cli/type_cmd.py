import json
from pathlib import Path
from typing import Annotated

import typer

from asset_hub.api.schemas.asset_type import TypeRead
from asset_hub.cli.deps import cli_session, load_schema_from_file, parse_uuid
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
        schema = load_schema_from_file(from_file, json_output)
        name = schema["name"]
        prefix = schema.get("code_prefix") or schema.get("prefix") or prefix
        description = schema.get("description")
        custom_fields = schema.get("custom_fields", [])
    elif name is not None:
        custom_fields = json.loads(fields) if fields else []
    else:
        print_error("必须提供 --name 或 --from", json_output, code="validation", exit_code=2)

    if not prefix:
        print_error("必须提供 --prefix（2-4 大写字母）", json_output, code="validation", exit_code=2)

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
        ref_count = svc.count_refs(uid)

        if dry_run:
            if ref_count > 0:
                # 有引用 — 真删会失败；dry-run 应同样信号失败
                print_error(
                    f"该类型仍有 {ref_count} 个资产引用，dry-run 报告将会失败（实际删除会被拒绝）",
                    json_output,
                    code="conflict",
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
                print_error("用户取消", json_output, code="cancelled", exit_code=10)

        # delete_type 内部再校验 ref，>0 时抛 ConflictError → envelope → exit 1
        svc.delete_type(uid)
        deleted_payload = {"deleted_id": str(uid), "name": t.name}

    print_result(deleted_payload, json_output)


@type_app.command("update")
def type_update(
    type_id: Annotated[str, typer.Argument(help="要更新的 AssetType id")],
    from_file: Annotated[Path | None, typer.Option("--from", help="JSON schema 文件路径（整体替换）")] = None,
    name: Annotated[str | None, typer.Option(help="新类型名称")] = None,
    description: Annotated[str | None, typer.Option(help="新描述")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="预览不真改")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="JSON 信封输出")] = False,
) -> None:
    """部分更新 AssetType（code_prefix 不可改）。"""
    uid = parse_uuid(type_id, json_output)

    # 互斥校验
    if from_file is not None and (name is not None or description is not None):
        print_error(
            "--from 与 --name/--description 互斥，请二选一",
            json_output,
            code="validation",
            exit_code=2,
        )

    # 至少一个修改源
    if from_file is None and name is None and description is None:
        print_error(
            "必须提供至少一个修改源：--from / --name / --description",
            json_output,
            code="validation",
            exit_code=2,
        )

    final_name = name
    final_description = description
    final_custom_fields: list | None = None
    if from_file is not None:
        schema = load_schema_from_file(from_file, json_output)
        final_name = schema.get("name")
        final_description = schema.get("description")
        final_custom_fields = schema.get("custom_fields")
        # code_prefix 出现也被忽略（spec §5.3 immutable）

    if dry_run:
        with cli_session() as session, handle_domain_errors(json_output):
            svc = TypeService(session)
            current_orm = svc.get_type(uid)
            current = TypeRead.model_validate(current_orm)
            ref_count = svc.count_refs(uid)

        diff = _build_diff(current, final_name, final_description, final_custom_fields)
        payload = {"diff": diff, "affected_assets_count": ref_count}
        print_dry_run(
            payload,
            json_output,
            message=f"将更新 type '{current.name}' (引用资产数: {ref_count})",
        )

    with cli_session() as session, handle_domain_errors(json_output):
        svc = TypeService(session)
        t = svc.update_type(
            uid,
            name=final_name,
            description=final_description,
            custom_fields=final_custom_fields,
        )
    print_result(to_json_dict(TypeRead, t), json_output)


def _build_diff(
    current: TypeRead,
    new_name: str | None,
    new_description: str | None,
    new_custom_fields: list | None,
) -> dict:
    """构造 update --dry-run 的 diff payload。

    注意：current 是 TypeRead DTO，custom_fields 是 list[CustomFieldDef]
    （Pydantic 模型）；通过属性访问 `f.key`，序列化用 `model_dump()`。
    """
    diff: dict = {}
    if new_name is not None:
        diff["name"] = (
            {"unchanged": True}
            if new_name == current.name
            else {"from": current.name, "to": new_name}
        )
    if new_description is not None:
        diff["description"] = (
            {"unchanged": True}
            if new_description == current.description
            else {"from": current.description, "to": new_description}
        )
    if new_custom_fields is not None:
        old_keys = {f.key: f.model_dump() for f in current.custom_fields}
        new_keys = {f["key"]: f for f in new_custom_fields}
        added = [f for k, f in new_keys.items() if k not in old_keys]
        removed = [{"key": k} for k in old_keys if k not in new_keys]
        changed = [
            {"key": k, "from": old_keys[k], "to": new_keys[k]}
            for k in new_keys
            if k in old_keys and old_keys[k] != new_keys[k]
        ]
        unchanged_count = sum(
            1 for k in new_keys if k in old_keys and old_keys[k] == new_keys[k]
        )
        diff["custom_fields"] = {
            "added": added,
            "removed": removed,
            "changed": changed,
            "unchanged_count": unchanged_count,
        }
    return diff
