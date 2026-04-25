import json
from typing import Annotated

import typer

from asset_hub.api.schemas.asset import AssetRead
from asset_hub.api.schemas.checkout import CheckoutRead
from asset_hub.cli.deps import cli_session, parse_enum, parse_uuid
from asset_hub.cli.envelope import (
    handle_domain_errors,
    print_dry_run,
    print_result,
    to_json_dict,
)
from asset_hub.models.asset import AssetStatus
from asset_hub.services.asset import AssetService
from asset_hub.services.checkout import CheckoutService

asset_app = typer.Typer(name="asset", help="资产管理", no_args_is_help=True)


@asset_app.command("register")
def asset_register(
    name: Annotated[str, typer.Option(help="资产名称")],
    type_id: Annotated[str, typer.Option("--type-id", help="类型 UUID")],
    serial_number: Annotated[str | None, typer.Option("--sn", help="铭牌编号")] = None,
    holder: Annotated[str | None, typer.Option(help="保管人")] = None,
    location: Annotated[str | None, typer.Option(help="位置")] = None,
    notes: Annotated[str | None, typer.Option(help="备注")] = None,
    custom: Annotated[str | None, typer.Option(help="自定义字段 JSON")] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """登记新资产。"""
    uid = parse_uuid(type_id, json_output)
    custom_data = json.loads(custom) if custom else {}

    with cli_session() as session, handle_domain_errors(json_output):
        svc = AssetService(session)
        a = svc.register(
            name=name,
            type_id=uid,
            serial_number=serial_number,
            holder=holder,
            location=location,
            notes=notes,
            custom_data=custom_data,
        )
    print_result(to_json_dict(AssetRead, a), json_output)


@asset_app.command("list")
def asset_list(
    type_id: Annotated[str | None, typer.Option("--type-id", help="按类型筛选")] = None,
    status: Annotated[str | None, typer.Option(help="按状态筛选")] = None,
    holder: Annotated[str | None, typer.Option(help="按保管人筛选")] = None,
    q: Annotated[str | None, typer.Option(help="关键词搜索")] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """列出资产。"""
    parsed_type_id = parse_uuid(type_id, json_output)
    parsed_status = parse_enum(AssetStatus, status, json_output)

    with cli_session() as session:
        svc = AssetService(session)
        assets = svc.list_assets(
            type_id=parsed_type_id,
            status=parsed_status,
            holder=holder,
            q=q,
        )
    data = [to_json_dict(AssetRead, a) for a in assets]
    print_result(data, json_output, count=len(data))


@asset_app.command("show")
def asset_show(
    asset_id: Annotated[str, typer.Argument(help="资产 UUID")],
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """查看资产详情。"""
    uid = parse_uuid(asset_id, json_output)

    with cli_session() as session, handle_domain_errors(json_output):
        svc = AssetService(session)
        a = svc.get_asset(uid)
    print_result(to_json_dict(AssetRead, a), json_output)


@asset_app.command("update")
def asset_update(
    asset_id: Annotated[str, typer.Argument(help="资产 UUID")],
    set_data: Annotated[str, typer.Option("--set", help="要更新的字段 JSON")],
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """更新资产字段。"""
    uid = parse_uuid(asset_id, json_output)
    updates = json.loads(set_data)

    with cli_session() as session, handle_domain_errors(json_output):
        svc = AssetService(session)
        a = svc.update_asset(uid, **updates)
    print_result(to_json_dict(AssetRead, a), json_output)


@asset_app.command("delete")
def asset_delete(
    asset_id: Annotated[str, typer.Argument(help="资产 UUID")],
    yes: Annotated[bool, typer.Option("--yes", help="跳过确认")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="预览，不实际删除")] = False,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """删除资产。"""
    uid = parse_uuid(asset_id, json_output)

    with cli_session() as session, handle_domain_errors(json_output):
        svc = AssetService(session)
        a = svc.get_asset(uid)

        if dry_run:
            print_dry_run(
                {"would_delete": to_json_dict(AssetRead, a)},
                json_output,
                message=f"将删除 {a.name} ({a.id})",
            )

        if not yes:
            confirm = typer.confirm(f"确定删除 {a.name}?")
            if not confirm:
                raise typer.Abort()

        svc.delete_asset(uid)
    print_result({"deleted": str(uid)}, json_output)


@asset_app.command("checkout")
def asset_checkout(
    asset_id: Annotated[str, typer.Argument(help="资产 UUID")],
    to: Annotated[str, typer.Option("--to", help="派发给谁（保管人）")],
    location: Annotated[str | None, typer.Option(help="位置")] = None,
    note: Annotated[str | None, typer.Option(help="派发备注")] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """派发资产给某人。"""
    uid = parse_uuid(asset_id, json_output)
    with cli_session() as session, handle_domain_errors(json_output):
        svc = CheckoutService(session)
        rec = svc.checkout(asset_id=uid, holder=to, location=location, note=note)
    print_result(to_json_dict(CheckoutRead, rec), json_output)


@asset_app.command("return")
def asset_return(
    asset_id: Annotated[str, typer.Argument(help="资产 UUID")],
    note: Annotated[str | None, typer.Option(help="归还备注")] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """归还资产。"""
    uid = parse_uuid(asset_id, json_output)
    with cli_session() as session, handle_domain_errors(json_output):
        svc = CheckoutService(session)
        rec = svc.return_(asset_id=uid, note=note)
    print_result(to_json_dict(CheckoutRead, rec), json_output)


@asset_app.command("history")
def asset_history(
    asset_id: Annotated[str, typer.Argument(help="资产 UUID")],
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """查看资产流转历史。"""
    uid = parse_uuid(asset_id, json_output)
    with cli_session() as session, handle_domain_errors(json_output):
        svc = CheckoutService(session)
        records = svc.history(asset_id=uid)
    data = [to_json_dict(CheckoutRead, r) for r in records]
    print_result(data, json_output, count=len(data))
