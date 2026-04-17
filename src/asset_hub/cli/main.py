import typer

from asset_hub.cli.asset_cmd import asset_app
from asset_hub.cli.attachment_cmd import attachment_app
from asset_hub.cli.type_cmd import type_app

app = typer.Typer(name="asset-hub", no_args_is_help=True)
app.add_typer(type_app, name="type")
app.add_typer(asset_app, name="asset")
app.add_typer(attachment_app, name="attachment")
