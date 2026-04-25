from pathlib import Path
from typing import Annotated

import typer

from asset_hub.api.schemas.attachment import AttachmentRead
from asset_hub.cli.deps import cli_session, parse_uuid
from asset_hub.cli.envelope import handle_domain_errors, print_result, to_json_dict
from asset_hub.models.attachment import AttachmentKind
from asset_hub.services.attachment import AttachmentService
from asset_hub.storage import get_default_storage

attachment_app = typer.Typer(
    name="attachment", help="附件管理", no_args_is_help=True
)


@attachment_app.command("add")
def attachment_add(
    asset_id: Annotated[str, typer.Argument(help="资产 UUID")],
    file: Annotated[
        Path,
        typer.Option("--file", exists=True, dir_okay=False, readable=True, help="要上传的文件"),
    ],
    kind: Annotated[AttachmentKind, typer.Option(help="附件类型")] = AttachmentKind.OTHER,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """上传附件到指定资产。"""
    uid = parse_uuid(asset_id, json_output)
    storage = get_default_storage()
    with cli_session() as session, handle_domain_errors(json_output):
        svc = AttachmentService(session, storage)
        with file.open("rb") as fh:
            att = svc.add(
                asset_id=uid,
                kind=kind,
                original_name=file.name,
                stream=fh,
            )
    print_result(to_json_dict(AttachmentRead, att), json_output)


@attachment_app.command("list")
def attachment_list(
    asset_id: Annotated[str, typer.Argument(help="资产 UUID")],
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """列出某资产的全部附件。"""
    uid = parse_uuid(asset_id, json_output)
    storage = get_default_storage()
    with cli_session() as session, handle_domain_errors(json_output):
        svc = AttachmentService(session, storage)
        items = svc.list(asset_id=uid)
    data = [to_json_dict(AttachmentRead, a) for a in items]
    print_result(data, json_output, count=len(data))
