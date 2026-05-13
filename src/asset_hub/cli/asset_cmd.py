import json
from datetime import date, datetime
from typing import Annotated

import typer

from asset_hub.api.schemas.asset import AssetRead
from asset_hub.api.schemas.transition import TransitionRead
from asset_hub.cli.deps import (
    cli_session,
    filter_list_fields,
    filter_record_fields,
    parse_cli_fields,
    parse_enum,
    parse_unset_or_value,
    parse_uuid,
)
from asset_hub.cli.envelope import (
    handle_domain_errors,
    print_dry_run,
    print_result,
    to_json_dict,
)
from asset_hub.models.asset import AssetStatus
from asset_hub.models.state_transition import TransitionKind
from asset_hub.services.asset import AssetService
from asset_hub.services.transition import TransitionService

asset_app = typer.Typer(name="asset", help="资产管理", no_args_is_help=True)

# 缓存合法字段集合（spec §4.4），避免每次 invoke 重算
_ASSET_READ_FIELDS = set(AssetRead.model_fields.keys())
_TRANSITION_READ_FIELDS = set(TransitionRead.model_fields.keys())


@asset_app.command("register")
def asset_register(
    name: Annotated[str, typer.Option(help="资产名称")],
    type_id: Annotated[str, typer.Option("--type-id", help="类型 UUID")],
    serial_number: Annotated[str | None, typer.Option("--sn", help="铭牌编号")] = None,
    model: Annotated[str | None, typer.Option("--model", help="型号")] = None,
    holder: Annotated[str | None, typer.Option(help="保管人")] = None,
    location: Annotated[str | None, typer.Option(help="位置")] = None,
    notes: Annotated[str | None, typer.Option(help="备注")] = None,
    custom: Annotated[str | None, typer.Option(help="自定义字段 JSON")] = None,
    acquired_at: Annotated[
        str | None, typer.Option("--acquired-at", help="入账日期 YYYY-MM-DD")
    ] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """登记新资产。"""
    uid = parse_uuid(type_id, json_output)
    custom_data = json.loads(custom) if custom else {}
    parsed_date = date.fromisoformat(acquired_at) if acquired_at else None

    with cli_session() as session, handle_domain_errors(json_output):
        svc = AssetService(session)
        a = svc.register(
            name=name,
            type_id=uid,
            serial_number=serial_number,
            model=model,
            holder=holder,
            location=location,
            notes=notes,
            custom_data=custom_data,
            acquired_at=parsed_date,
        )
        a = svc.annotate_idle_days([a])[0]
    print_result(to_json_dict(AssetRead, a), json_output)


@asset_app.command("checkout")
def asset_checkout(
    asset_id: Annotated[str, typer.Argument(help="资产 UUID")],
    to_holder: Annotated[str, typer.Option("--to-holder", help="派出对象（必填）")],
    kind: Annotated[
        str,
        typer.Option("--kind", help="派发类型：internal=组内派发，external=出借给外部"),
    ] = "internal",
    to_location: Annotated[
        str | None,
        typer.Option("--to-location", help='新位置（不传保留当前；传 "" 清空）'),
    ] = None,
    note: Annotated[str | None, typer.Option(help="备注")] = None,
    due_at: Annotated[
        str | None, typer.Option("--due-at", help="期望归还时间（ISO8601）")
    ] = None,
    fields: Annotated[
        str | None, typer.Option("--fields", help="逗号分隔字段名，按需返回")
    ] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """派发资产（kind: internal 内部派发 / external 对外出借）。"""
    uid = parse_uuid(asset_id, json_output)
    parsed_fields = parse_cli_fields(fields)
    kind_map = {
        "internal": TransitionKind.CHECKOUT_INTERNAL,
        "external": TransitionKind.CHECKOUT_EXTERNAL,
    }
    if kind not in kind_map:
        raise typer.BadParameter(f"--kind 必须是 internal 或 external，得到: {kind}")
    parsed_due = datetime.fromisoformat(due_at) if due_at else None

    with cli_session() as session, handle_domain_errors(json_output):
        svc = TransitionService(session)
        rec = svc.record_transition(
            asset_id=uid,
            kind=kind_map[kind],
            to_holder=to_holder,
            to_location=parse_unset_or_value(to_location),
            note=note,
            due_at=parsed_due,
        )
    record = to_json_dict(TransitionRead, rec)
    record = filter_record_fields(
        record,
        parsed_fields,
        allowed=_TRANSITION_READ_FIELDS,
        json_output=json_output,
    )
    print_result(record, json_output)


@asset_app.command("return")
def asset_return(
    asset_id: Annotated[str, typer.Argument(help="资产 UUID")],
    to_holder: Annotated[
        str | None,
        typer.Option(
            "--to-holder", help='归还接收人/仓管（不传则资产无 holder，传 "" 显式清空）'
        ),
    ] = None,
    to_location: Annotated[
        str | None, typer.Option("--to-location", help="归还位置")
    ] = None,
    note: Annotated[str | None, typer.Option(help="归还备注")] = None,
    fields: Annotated[
        str | None, typer.Option("--fields", help="逗号分隔字段名，按需返回")
    ] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """归还资产（--to-holder 是归还接收人，归还后成为新 holder；不传则资产无 holder）。"""
    uid = parse_uuid(asset_id, json_output)
    parsed_fields = parse_cli_fields(fields)

    with cli_session() as session, handle_domain_errors(json_output):
        svc = TransitionService(session)
        rec = svc.record_transition(
            asset_id=uid,
            kind=TransitionKind.RETURN,
            to_holder=parse_unset_or_value(to_holder),
            to_location=parse_unset_or_value(to_location),
            note=note,
        )
    record = to_json_dict(TransitionRead, rec)
    record = filter_record_fields(
        record,
        parsed_fields,
        allowed=_TRANSITION_READ_FIELDS,
        json_output=json_output,
    )
    print_result(record, json_output)


@asset_app.command("history")
def asset_history(
    asset_id: Annotated[str, typer.Argument(help="资产 UUID")],
    fields: Annotated[
        str | None, typer.Option("--fields", help="逗号分隔字段名，按需返回")
    ] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """查看资产流转历史（10 transition kind 全覆盖）。"""
    uid = parse_uuid(asset_id, json_output)
    parsed_fields = parse_cli_fields(fields)
    with cli_session() as session, handle_domain_errors(json_output):
        svc = TransitionService(session)
        records = svc.list_transitions(asset_id=uid)
    data = [to_json_dict(TransitionRead, r) for r in records]
    data = filter_list_fields(
        data,
        parsed_fields,
        allowed=_TRANSITION_READ_FIELDS,
        json_output=json_output,
    )
    print_result(data, json_output, count=len(data))


def _record_simple_transition(
    asset_id: str,
    kind: TransitionKind,
    *,
    to_holder: str | None = None,
    to_location: str | None = None,
    note: str | None = None,
    json_output: bool = False,
    fields: str | None = None,
) -> None:
    """通用 transition 命令封装（无特殊参数的 kind 共用）。"""
    uid = parse_uuid(asset_id, json_output)
    parsed_fields = parse_cli_fields(fields)
    with cli_session() as session, handle_domain_errors(json_output):
        svc = TransitionService(session)
        rec = svc.record_transition(
            asset_id=uid,
            kind=kind,
            to_holder=parse_unset_or_value(to_holder),
            to_location=parse_unset_or_value(to_location),
            note=note,
        )
    record = to_json_dict(TransitionRead, rec)
    record = filter_record_fields(
        record,
        parsed_fields,
        allowed=_TRANSITION_READ_FIELDS,
        json_output=json_output,
    )
    print_result(record, json_output)


@asset_app.command("send-to-maintenance")
def asset_send_to_maintenance(
    asset_id: Annotated[str, typer.Argument(help="资产 UUID")],
    to_holder: Annotated[
        str | None, typer.Option("--to-holder", help="维修联系人")
    ] = None,
    to_location: Annotated[
        str | None, typer.Option("--to-location", help="维修地点")
    ] = None,
    note: Annotated[str | None, typer.Option(help="备注")] = None,
    fields: Annotated[
        str | None, typer.Option("--fields", help="逗号分隔字段名，按需返回")
    ] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """送修。"""
    _record_simple_transition(
        asset_id,
        TransitionKind.SEND_TO_MAINTENANCE,
        to_holder=to_holder,
        to_location=to_location,
        note=note,
        json_output=json_output,
        fields=fields,
    )


@asset_app.command("recover")
def asset_recover(
    asset_id: Annotated[str, typer.Argument(help="资产 UUID")],
    to_holder: Annotated[
        str | None, typer.Option("--to-holder", help="新保管人/仓管")
    ] = None,
    to_location: Annotated[
        str | None, typer.Option("--to-location", help="新位置")
    ] = None,
    note: Annotated[str | None, typer.Option(help="备注")] = None,
    fields: Annotated[
        str | None, typer.Option("--fields", help="逗号分隔字段名，按需返回")
    ] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """维修完成回库。"""
    _record_simple_transition(
        asset_id,
        TransitionKind.RECOVER_FROM_MAINTENANCE,
        to_holder=to_holder,
        to_location=to_location,
        note=note,
        json_output=json_output,
        fields=fields,
    )


@asset_app.command("reinstate")
def asset_reinstate(
    asset_id: Annotated[str, typer.Argument(help="资产 UUID")],
    to_holder: Annotated[
        str | None, typer.Option("--to-holder", help="新保管人/仓管")
    ] = None,
    to_location: Annotated[
        str | None, typer.Option("--to-location", help="新位置")
    ] = None,
    note: Annotated[str | None, typer.Option(help="备注")] = None,
    fields: Annotated[
        str | None, typer.Option("--fields", help="逗号分隔字段名，按需返回")
    ] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """重新启用（从已退役回到闲置）。"""
    _record_simple_transition(
        asset_id,
        TransitionKind.REINSTATE,
        to_holder=to_holder,
        to_location=to_location,
        note=note,
        json_output=json_output,
        fields=fields,
    )


@asset_app.command("report-broken")
def asset_report_broken(
    asset_id: Annotated[str, typer.Argument(help="资产 UUID")],
    to_holder: Annotated[
        str | None,
        typer.Option("--to-holder", help='责任人（不传保留当前 holder，传 "" 清空）'),
    ] = None,
    to_location: Annotated[
        str | None, typer.Option("--to-location", help="位置（不传保留当前 location）")
    ] = None,
    note: Annotated[str | None, typer.Option(help="故障描述")] = None,
    fields: Annotated[
        str | None, typer.Option("--fields", help="逗号分隔字段名，按需返回")
    ] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """标记资产出现故障（IDLE/IN_USE → BROKEN）。"""
    _record_simple_transition(
        asset_id,
        TransitionKind.REPORT_BROKEN,
        to_holder=to_holder,
        to_location=to_location,
        note=note,
        json_output=json_output,
        fields=fields,
    )


@asset_app.command("declare-unrepairable")
def asset_declare_unrepairable(
    asset_id: Annotated[str, typer.Argument(help="资产 UUID")],
    note: Annotated[str | None, typer.Option(help="判定备注")] = None,
    yes: Annotated[bool, typer.Option("--yes", help="跳过确认")] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="预览，不实际执行")
    ] = False,
    fields: Annotated[
        str | None, typer.Option("--fields", help="逗号分隔字段名，按需返回")
    ] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """维修过程判定不可修复（MAINTENANCE → BROKEN）。"""
    uid = parse_uuid(asset_id, json_output)
    parsed_fields = parse_cli_fields(fields)
    with cli_session() as session, handle_domain_errors(json_output):
        asset_svc = AssetService(session)
        a = asset_svc.get_asset(uid)

        if dry_run:
            # dry-run 预览不是 TransitionRead，不应用 --fields filter
            print_dry_run(
                {"would_declare_unrepairable": to_json_dict(AssetRead, a)},
                json_output,
                message=f"将判定 {a.name} 不可修复（进入 BROKEN 态）",
            )
            return

        if not yes:
            confirm = typer.confirm(
                f"判定资产 {a.name} 维修不可修复（进入 BROKEN 态）？"
            )
            if not confirm:
                raise typer.Abort()

        svc = TransitionService(session)
        rec = svc.record_transition(
            asset_id=uid,
            kind=TransitionKind.DECLARE_UNREPAIRABLE,
            note=note,
        )
    record = to_json_dict(TransitionRead, rec)
    record = filter_record_fields(
        record,
        parsed_fields,
        allowed=_TRANSITION_READ_FIELDS,
        json_output=json_output,
    )
    print_result(record, json_output)


@asset_app.command("dismiss")
def asset_dismiss(
    asset_id: Annotated[str, typer.Argument(help="资产 UUID")],
    to_holder: Annotated[
        str | None, typer.Option("--to-holder", help="责任人（不传保留当前）")
    ] = None,
    to_location: Annotated[
        str | None, typer.Option("--to-location", help="位置（不传保留当前）")
    ] = None,
    note: Annotated[str | None, typer.Option(help="备注")] = None,
    fields: Annotated[
        str | None, typer.Option("--fields", help="逗号分隔字段名，按需返回")
    ] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """故障解除（BROKEN → IDLE）—— 自愈 / 自修场景。"""
    _record_simple_transition(
        asset_id,
        TransitionKind.DISMISS,
        to_holder=to_holder,
        to_location=to_location,
        note=note,
        json_output=json_output,
        fields=fields,
    )


@asset_app.command("reassign")
def asset_reassign(
    asset_id: Annotated[str, typer.Argument(help="资产 UUID")],
    to_holder: Annotated[
        str | None, typer.Option("--to-holder", help="新保管人")
    ] = None,
    to_location: Annotated[
        str | None, typer.Option("--to-location", help="新位置")
    ] = None,
    note: Annotated[str | None, typer.Option(help="备注")] = None,
    fields: Annotated[
        str | None, typer.Option("--fields", help="逗号分隔字段名，按需返回")
    ] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """重新分配持有人或位置（合并 v1.0 RELOCATE + TRANSFER_HOLDER）。

    必须改 holder 或 location 至少一项：
      asset reassign <id> --to-holder 李四
      asset reassign <id> --to-location 仓库
      asset reassign <id> --to-holder 李四 --to-location 仓库
    """
    _record_simple_transition(
        asset_id,
        TransitionKind.REASSIGN,
        to_holder=to_holder,
        to_location=to_location,
        note=note,
        json_output=json_output,
        fields=fields,
    )


@asset_app.command("retire")
def asset_retire(
    asset_id: Annotated[str, typer.Argument(help="资产 UUID")],
    to_holder: Annotated[
        str | None, typer.Option("--to-holder", help="备件库管理员")
    ] = None,
    to_location: Annotated[
        str | None, typer.Option("--to-location", help="存放位置")
    ] = None,
    note: Annotated[str | None, typer.Option(help="备注")] = None,
    yes: Annotated[bool, typer.Option("--yes", help="跳过确认")] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="预览，不实际执行")
    ] = False,
    fields: Annotated[
        str | None, typer.Option("--fields", help="逗号分隔字段名，按需返回")
    ] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """退役（可通过 reinstate 复活）。"""
    uid = parse_uuid(asset_id, json_output)
    parsed_fields = parse_cli_fields(fields)
    with cli_session() as session, handle_domain_errors(json_output):
        asset_svc = AssetService(session)
        a = asset_svc.get_asset(uid)

        if dry_run:
            # dry-run 预览不是 TransitionRead，不应用 --fields filter
            print_dry_run(
                {"would_retire": to_json_dict(AssetRead, a)},
                json_output,
                message=f"将退役 {a.name} ({a.id})",
            )
            return

        if not yes:
            confirm = typer.confirm(f"确定退役 {a.name}?")
            if not confirm:
                raise typer.Abort()

        svc = TransitionService(session)
        rec = svc.record_transition(
            asset_id=uid,
            kind=TransitionKind.RETIRE,
            to_holder=parse_unset_or_value(to_holder),
            to_location=parse_unset_or_value(to_location),
            note=note,
        )
    record = to_json_dict(TransitionRead, rec)
    record = filter_record_fields(
        record,
        parsed_fields,
        allowed=_TRANSITION_READ_FIELDS,
        json_output=json_output,
    )
    print_result(record, json_output)


@asset_app.command("dispose")
def asset_dispose(
    asset_id: Annotated[str, typer.Argument(help="资产 UUID")],
    note: Annotated[str | None, typer.Option(help="备注")] = None,
    yes: Annotated[bool, typer.Option("--yes", help="跳过确认")] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="预览，不实际执行")
    ] = False,
    fields: Annotated[
        str | None, typer.Option("--fields", help="逗号分隔字段名，按需返回")
    ] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """注销（终态，不可撤销，holder/location 将被清空）。仅可从 RETIRED/MAINTENANCE/BROKEN 出发。"""
    uid = parse_uuid(asset_id, json_output)
    parsed_fields = parse_cli_fields(fields)
    with cli_session() as session, handle_domain_errors(json_output):
        asset_svc = AssetService(session)
        a = asset_svc.get_asset(uid)

        if dry_run:
            # dry-run 预览不是 TransitionRead，不应用 --fields filter
            print_dry_run(
                {"would_dispose": to_json_dict(AssetRead, a)},
                json_output,
                message=f"将注销 {a.name} ({a.id})（终态、不可撤销）",
            )
            return

        if not yes:
            confirm = typer.confirm(
                f"⚠️ 确定注销 {a.name}？此操作不可撤销，holder 与 location 将被清空。"
            )
            if not confirm:
                raise typer.Abort()

        svc = TransitionService(session)
        rec = svc.record_transition(
            asset_id=uid,
            kind=TransitionKind.DISPOSE,
            note=note,
        )
    record = to_json_dict(TransitionRead, rec)
    record = filter_record_fields(
        record,
        parsed_fields,
        allowed=_TRANSITION_READ_FIELDS,
        json_output=json_output,
    )
    print_result(record, json_output)


@asset_app.command("list")
def asset_list(
    type_id: Annotated[str | None, typer.Option("--type-id", help="按类型筛选")] = None,
    status: Annotated[str | None, typer.Option(help="按状态筛选")] = None,
    holder: Annotated[str | None, typer.Option(help="按保管人筛选")] = None,
    q: Annotated[str | None, typer.Option(help="关键词搜索")] = None,
    include_retired: Annotated[
        bool,
        typer.Option(
            "--include-retired/--no-include-retired", help="是否包含已退役（默认排除）"
        ),
    ] = False,
    include_disposed: Annotated[
        bool,
        typer.Option(
            "--include-disposed/--no-include-disposed",
            help="是否包含已注销（默认排除）",
        ),
    ] = False,
    sort: Annotated[
        str | None,
        typer.Option(
            "--sort",
            help="排序字段：name/model/asset_code/serial_number/created_at/updated_at/acquired_at/idle_days",
        ),
    ] = None,
    order: Annotated[
        str,
        typer.Option("--order", help="asc/desc，默认 desc"),
    ] = "desc",
    limit: Annotated[
        int | None, typer.Option("--limit", help="返回上限，1-1000")
    ] = None,
    offset: Annotated[int | None, typer.Option("--offset", help=">=0")] = None,
    fields: Annotated[
        str | None, typer.Option("--fields", help="逗号分隔字段名，按需返回")
    ] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """列出资产。"""
    parsed_type_id = parse_uuid(type_id, json_output)
    parsed_status = parse_enum(AssetStatus, status, json_output)
    parsed_fields = parse_cli_fields(fields)

    with (
        cli_session() as session,
        handle_domain_errors(json_output, exit_2_on_validation=True),
    ):
        svc = AssetService(session)
        assets = svc.list_assets(
            type_id=parsed_type_id,
            status=parsed_status,
            holder=holder,
            q=q,
            include_retired=include_retired,
            include_disposed=include_disposed,
            sort_by=sort,
            sort_order=order,
            limit=limit,
            offset=offset,
        )
        annotated = svc.annotate_idle_days(assets)
    data = [to_json_dict(AssetRead, a) for a in annotated]
    data = filter_list_fields(
        data,
        parsed_fields,
        allowed=_ASSET_READ_FIELDS,
        json_output=json_output,
    )
    print_result(data, json_output, count=len(data))


@asset_app.command("show")
def asset_show(
    asset_id: Annotated[str, typer.Argument(help="资产 UUID")],
    fields: Annotated[
        str | None, typer.Option("--fields", help="逗号分隔字段名，按需返回")
    ] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """查看资产详情。"""
    uid = parse_uuid(asset_id, json_output)
    parsed_fields = parse_cli_fields(fields)

    with cli_session() as session, handle_domain_errors(json_output):
        svc = AssetService(session)
        a = svc.annotate_idle_days([svc.get_asset(uid)])[0]
    record = to_json_dict(AssetRead, a)
    record = filter_record_fields(
        record,
        parsed_fields,
        allowed=_ASSET_READ_FIELDS,
        json_output=json_output,
    )
    print_result(record, json_output)


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
        a = svc.annotate_idle_days([a])[0]
    print_result(to_json_dict(AssetRead, a), json_output)


@asset_app.command("delete")
def asset_delete(
    asset_id: Annotated[str, typer.Argument(help="资产 UUID")],
    yes: Annotated[bool, typer.Option("--yes", help="跳过确认")] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="预览，不实际删除")
    ] = False,
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
