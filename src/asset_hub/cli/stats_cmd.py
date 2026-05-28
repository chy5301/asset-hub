"""asset-hub stats — 看板 4 段聚合 / Agent 友好 fields 段选择.

命名说明（spec §B.an5）：单 token 'stats' 是项目其它命令 <resource> <action>
模式的有意例外。聚合查询 CLI 惯例（git stats / npm stats）；如未来需扩展
（如 stats refresh 缓存触发），届时升为 'stats show' 等子命令。
"""

from typing import Annotated

import typer
from rich.columns import Columns
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table

from asset_hub.api.schemas.stats import StatsRead
from asset_hub.cli.deps import cli_session
from asset_hub.cli.envelope import handle_domain_errors, print_result
from asset_hub.services.stats import StatsService, parse_stats_fields

stats_app = typer.Typer(
    name="stats",
    help=(
        "看板统计：4 段聚合 (类型/状态/保管人/闲置 Top 10) + summary 业务摘要。"
        "支持 --fields 段选择，Agent 仅需单段时省 token。"
    ),
    invoke_without_command=True,
    no_args_is_help=False,
)


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
    """看板 4 段聚合查询（CLI 入口）。

    Examples:
        asset-hub stats --json
        asset-hub stats --fields idle_top,status_distribution --json
    """
    if ctx.invoked_subcommand is not None:
        return

    with (
        cli_session() as session,
        handle_domain_errors(json_output, exit_2_on_validation=True),
    ):
        parsed_fields = parse_stats_fields(fields)
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
    """双列布局：左列 类型分布 + 状态分布；右列 保管人持有 + 闲置 Top 10；
    顶部 summary 摘要面板；--fields 限定时未请求段不渲染."""
    console = Console()

    # Summary panel
    summary = stats.summary
    summary_lines = [
        f"总资产 [bold]{summary.total_assets}[/bold]   "
        f"在册 [bold]{summary.registered_assets}[/bold]   "
        f"闲置 [bold]{summary.idle_count}[/bold]"
    ]
    if summary.include_retired:
        summary_lines.append("[dim]含 RETIRED[/dim]")
    if summary.include_disposed:
        summary_lines.append("[dim]含 DISPOSED[/dim]")
    console.print(Panel("\n".join(summary_lines), title="概览", border_style="blue"))

    left: list = []
    right: list = []

    if stats.type_distribution is not None:
        t = Table(title="类型分布", show_header=True, header_style="bold cyan")
        t.add_column("Type")
        t.add_column("Count", justify="right")
        for item in stats.type_distribution:
            t.add_row(item.type_name, str(item.count))
        left.append(t)

    if stats.status_distribution is not None:
        t = Table(title="状态分布", show_header=True, header_style="bold cyan")
        t.add_column("Status")
        t.add_column("Count", justify="right")
        for status_name, count in stats.status_distribution.items():
            t.add_row(status_name, str(count))
        left.append(t)

    if stats.holder_ranking is not None:
        t = Table(title="保管人持有", show_header=True, header_style="bold cyan")
        t.add_column("Holder")
        t.add_column("Count", justify="right")
        for h in stats.holder_ranking:
            t.add_row(h.holder, str(h.count))
        right.append(t)

    if stats.idle_top is not None:
        t = Table(title="闲置时长 Top 10", show_header=True, header_style="bold yellow")
        t.add_column("Code")
        t.add_column("Type")
        t.add_column("Days", justify="right")
        for it in stats.idle_top:
            days_text = (
                f"[red]{it.idle_days}d[/red]"
                if it.idle_days > 90
                else f"{it.idle_days}d"
            )
            t.add_row(it.asset_code, it.type_name or "-", days_text)
        right.append(t)

    # 双列展示——某段未渲染时那列就少
    if left and right:
        console.print(Columns([Panel.fit(Group(*left)), Panel.fit(Group(*right))]))
    elif left:
        for tbl in left:
            console.print(tbl)
    elif right:
        for tbl in right:
            console.print(tbl)
