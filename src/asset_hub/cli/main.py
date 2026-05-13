import typer

# --- --help-json 双模（spec §4.3 / v2.0 PR-2 T16）---


def _install_help_json_patches() -> None:
    """Install monkey patches that inject ``--help-json`` into every Click command.

    Why: Typer 不支持 ``<group> <sub> --flag`` argv 顺序（Click 要求 group options 前置），
    所以 group-level callback 走不通。每命令加 flag 要触 20+ leaf。最干净是 patch
    ``typer.main.get_command`` 在 Typer 包装 Click tree 时一次性递归注入。同时 patch
    ``typer.testing._get_command``，让 CliRunner 共享同样的注入逻辑（typer.testing 在
    import 时已绑定旧引用，必须二次 patch）。

    Risk: 依赖 ``typer.main.get_command``（公开但无 stability 保证）+
    ``typer.testing._get_command``（单下划线私有）。Typer 升级时可能需要 revisit。
    typer 版本 pin (`<0.30`) 已加上限缓解。
    """
    import typer.main
    import typer.testing

    from asset_hub.cli.deps import inject_help_json_recursive

    _original_get_command = typer.main.get_command

    def _patched_get_command(typer_instance: typer.Typer):  # type: ignore[no-untyped-def]
        cmd = _original_get_command(typer_instance)
        inject_help_json_recursive(cmd)
        return cmd

    typer.main.get_command = _patched_get_command  # type: ignore[assignment]
    typer.testing._get_command = _patched_get_command  # type: ignore[attr-defined]  # noqa: SLF001


# 模块加载时立即应用 —— 必须在 import sub-apps + create app 之前，
# 否则 Typer 已构建 Click tree，patch 不会被触发。
_install_help_json_patches()


# 必须放在 patch 之后 import，确保 Typer 构造 Click 树时走 patched get_command。
from asset_hub.cli.asset_cmd import asset_app  # noqa: E402
from asset_hub.cli.attachment_cmd import attachment_app  # noqa: E402
from asset_hub.cli.serve.cmd import serve_app  # noqa: E402
from asset_hub.cli.stats_cmd import stats_app  # noqa: E402
from asset_hub.cli.type_cmd import type_app  # noqa: E402

app = typer.Typer(name="asset-hub", no_args_is_help=True)
app.add_typer(type_app, name="type")
app.add_typer(asset_app, name="asset")
app.add_typer(attachment_app, name="attachment")
app.add_typer(serve_app, name="serve")
app.add_typer(stats_app, name="stats")
