"""asset-hub stats — 看板 4 段聚合 / Agent 友好 fields 段选择.

命名说明（spec §B.an5）：单 token 'stats' 是项目其它命令 <resource> <action>
模式的有意例外。聚合查询 CLI 惯例（git stats / npm stats）；如未来需扩展
（如 stats refresh 缓存触发），届时升为 'stats show' 等子命令。
"""
from typing import Annotated

import typer

from asset_hub.api.schemas.stats import StatsRead
from asset_hub.cli.deps import cli_session
from asset_hub.cli.envelope import handle_domain_errors, print_result
from asset_hub.errors import ValidationError
from asset_hub.services.stats import ALL_FIELDS, StatsService

stats_app = typer.Typer(
    name="stats",
    help=(
        "看板统计：4 段聚合 (类型/状态/保管人/闲置 Top 10) + summary 业务摘要。"
        "支持 --fields 段选择，Agent 仅需单段时省 token。"
    ),
    invoke_without_command=True,
    no_args_is_help=False,
)


def _parse_fields_cli(raw: str | None) -> set | None:
    """解析 --fields 逗号分隔；未知段 raise ValidationError 由 handle_domain_errors 兜底."""
    if raw is None or raw == "":
        return None
    parts = {p.strip() for p in raw.split(",") if p.strip()}
    unknown = parts - ALL_FIELDS
    if unknown:
        raise ValidationError(
            f"--fields 含未知段：{sorted(unknown)}；可选：{sorted(ALL_FIELDS)}"
        )
    return parts


@stats_app.callback(invoke_without_command=True)
def stats_root(
    ctx: typer.Context,
    include_retired: Annotated[
        bool,
        typer.Option(
            "--include-retired/--no-include-retired",
            help="统计中是否包含 RETIRED 资产 (默认排除)",
        ),
    ] = False,
    include_disposed: Annotated[
        bool,
        typer.Option(
            "--include-disposed/--no-include-disposed",
            help="统计中是否包含 DISPOSED 资产 (默认排除)",
        ),
    ] = False,
    fields: Annotated[
        str | None,
        typer.Option(
            "--fields",
            help=(
                "按段选择，逗号分隔；可选 type_distribution/status_distribution/"
                "holder_ranking/idle_top；不传 = 返全部 4 段；summary 始终返回"
            ),
        ),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """看板 4 段聚合查询（CLI 入口）。"""
    if ctx.invoked_subcommand is not None:
        return

    with cli_session() as session, handle_domain_errors(json_output, exit_2_on_validation=True):
        parsed_fields = _parse_fields_cli(fields)
        svc = StatsService(session)
        stats = svc.get_dashboard_stats(
            include_retired=include_retired,
            include_disposed=include_disposed,
            fields=parsed_fields,
        )

    if json_output:
        # exclude_none=True：段未查询时值为 None，dump 时排除，让 Agent 只看到实际段
        data = stats.model_dump(mode="json", exclude_none=True)
        print_result(data, json_output=True)
    else:
        _render_human_table(stats)


def _render_human_table(stats: StatsRead) -> None:
    """rich 双列表格输出占位（Task 11 实现）."""
    from rich import print as rprint

    rprint(stats.model_dump(mode="python"))  # Task 11 替换为 rich Table
