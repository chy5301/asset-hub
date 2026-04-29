import json

from typer.testing import CliRunner

from asset_hub.cli.main import app

runner = CliRunner()


def test_return_with_location_and_receiver(isolated_db):
    from asset_hub.cli.deps import cli_session
    from asset_hub.services.asset import AssetService
    from asset_hub.services.asset_type import TypeService
    from asset_hub.services.checkout import CheckoutService

    with cli_session() as session:
        t = TypeService(session).create_type(name="CLI-RT", code_prefix="CR")
        a = AssetService(session).register(type_id=t.id, name="C1", custom_data={})
        CheckoutService(session).checkout(a.id, holder="张三")
        asset_id = a.id

    res = runner.invoke(
        app,
        [
            "asset",
            "return",
            str(asset_id),
            "--location",
            "仓库D",
            "--receiver",
            "管理员丁",
            "--note",
            "CLI test",
            "--json",
        ],
    )
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)
    assert payload["success"] is True
    assert payload["data"]["return_location"] == "仓库D"
    assert payload["data"]["return_receiver"] == "管理员丁"


def test_return_without_extra_fields_backward_compat(isolated_db):
    """不传新 flag 时仍按旧行为（清空 location）"""
    from asset_hub.cli.deps import cli_session
    from asset_hub.services.asset import AssetService
    from asset_hub.services.asset_type import TypeService
    from asset_hub.services.checkout import CheckoutService

    with cli_session() as session:
        t = TypeService(session).create_type(name="CLI-BC2", code_prefix="BC")
        a = AssetService(session).register(type_id=t.id, name="C2", custom_data={})
        CheckoutService(session).checkout(a.id, holder="李四")
        asset_id = a.id

    res = runner.invoke(
        app, ["asset", "return", str(asset_id), "--note", "归还", "--json"]
    )
    assert res.exit_code == 0
    payload = json.loads(res.stdout)
    assert payload["data"]["return_location"] is None
    assert payload["data"]["return_receiver"] is None
