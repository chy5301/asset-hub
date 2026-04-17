import json
from typing import Annotated

import typer

from asset_hub.api.schemas.asset import AssetRead
from asset_hub.api.schemas.checkout import CheckoutRead
from asset_hub.cli.deps import cli_session, parse_uuid
from asset_hub.cli.envelope import print_error, print_result
from asset_hub.errors import DuplicateError, NotFoundError, StateError, ValidationError
from asset_hub.models.asset import AssetStatus
from asset_hub.services.asset import AssetService
from asset_hub.services.checkout import CheckoutService

asset_app = typer.Typer(name="asset", help="资产管理", no_args_is_help=True)


def _asset_to_dict(a) -> dict:
    return AssetRead.model_validate(a).model_dump(mode="json")


def _checkout_to_dict(r) -> dict:
    return CheckoutRead.model_validate(r).model_dump(mode="json")


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

    with cli_session() as session:
        svc = AssetService(session)
        try:
            a = svc.register(
                name=name,
                type_id=uid,
                serial_number=serial_number,
                holder=holder,
                location=location,
                notes=notes,
                custom_data=custom_data,
            )
        except NotFoundError as e:
            print_error(str(e), json_output, exit_code=3)
            return
        except (DuplicateError, ValidationError) as e:
            print_error(str(e), json_output, exit_code=1)
            return
    print_result(_asset_to_dict(a), json_output)


@asset_app.command("list")
def asset_list(
    type_id: Annotated[str | None, typer.Option("--type-id", help="按类型筛选")] = None,
    status: Annotated[str | None, typer.Option(help="按状态筛选")] = None,
    holder: Annotated[str | None, typer.Option(help="按保管人筛选")] = None,
    q: Annotated[str | None, typer.Option(help="关键词搜索")] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """列出资产。"""
    from uuid import UUID

    parsed_type_id = UUID(type_id) if type_id else None
    parsed_status = AssetStatus(status) if status else None

    with cli_session() as session:
        svc = AssetService(session)
        assets = svc.list_assets(
            type_id=parsed_type_id,
            status=parsed_status,
            holder=holder,
            q=q,
        )
    data = [_asset_to_dict(a) for a in assets]
    print_result(data, json_output, count=len(data))


@asset_app.command("show")
def asset_show(
    asset_id: Annotated[str, typer.Argument(help="资产 UUID")],
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """查看资产详情。"""
    uid = parse_uuid(asset_id, json_output)

    with cli_session() as session:
        svc = AssetService(session)
        try:
            a = svc.get_asset(uid)
        except NotFoundError as e:
            print_error(str(e), json_output, exit_code=3)
            return
    print_result(_asset_to_dict(a), json_output)


@asset_app.command("update")
def asset_update(
    asset_id: Annotated[str, typer.Argument(help="资产 UUID")],
    set_data: Annotated[str, typer.Option("--set", help="要更新的字段 JSON")],
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """更新资产字段。"""
    uid = parse_uuid(asset_id, json_output)

    updates = json.loads(set_data)

    with cli_session() as session:
        svc = AssetService(session)
        try:
            a = svc.update_asset(uid, **updates)
        except NotFoundError as e:
            print_error(str(e), json_output, exit_code=3)
            return
    print_result(_asset_to_dict(a), json_output)


@asset_app.command("delete")
def asset_delete(
    asset_id: Annotated[str, typer.Argument(help="资产 UUID")],
    yes: Annotated[bool, typer.Option("--yes", help="跳过确认")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="预览，不实际删除")] = False,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """删除资产。"""
    uid = parse_uuid(asset_id, json_output)

    with cli_session() as session:
        svc = AssetService(session)
        try:
            a = svc.get_asset(uid)
        except NotFoundError as e:
            print_error(str(e), json_output, exit_code=3)
            return

        if dry_run:
            if json_output:
                from asset_hub.cli.envelope import success_envelope
                print(success_envelope({"would_delete": _asset_to_dict(a)}))
            else:
                from rich import print as rprint
                rprint(f"[yellow]dry-run:[/yellow] 将删除 {a.name} ({a.id})")
            raise SystemExit(10)

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
    with cli_session() as session:
        svc = CheckoutService(session)
        try:
            rec = svc.checkout(asset_id=uid, holder=to, location=location, note=note)
        except NotFoundError as e:
            print_error(str(e), json_output, exit_code=3)
            return
        except StateError as e:
            print_error(str(e), json_output, exit_code=1)
            return
    print_result(_checkout_to_dict(rec), json_output)
