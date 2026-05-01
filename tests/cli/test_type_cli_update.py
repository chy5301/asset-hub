import json
import uuid

from typer.testing import CliRunner

from asset_hub.cli.deps import cli_session
from asset_hub.cli.main import app
from asset_hub.services.asset_type import TypeService

runner = CliRunner()


def _make_type(name="原名", prefix="OO") -> uuid.UUID:
    with cli_session() as s:
        return TypeService(s).create_type(name=name, code_prefix=prefix).id


class TestUpdateBasic:
    def test_update_with_name_only(self, isolated_db):
        tid = _make_type()
        res = runner.invoke(
            app, ["type", "update", str(tid), "--name", "新名", "--json"]
        )
        assert res.exit_code == 0
        payload = json.loads(res.stdout)
        assert payload["success"] is True
        assert payload["data"]["name"] == "新名"
        assert payload["data"]["code_prefix"] == "OO"

    def test_update_with_description_only(self, isolated_db):
        tid = _make_type()
        res = runner.invoke(
            app,
            ["type", "update", str(tid), "--description", "新描述", "--json"],
        )
        assert res.exit_code == 0
        assert json.loads(res.stdout)["data"]["description"] == "新描述"

    def test_update_with_from_file(self, isolated_db, tmp_path):
        tid = _make_type()
        schema = {
            "name": "改自 from",
            "code_prefix": "OO",  # 被忽略（spec §5.3）
            "description": "from 来",
            "custom_fields": [
                {"key": "cpu", "type": "string", "required": True}
            ],
        }
        f = tmp_path / "new.json"
        f.write_text(json.dumps(schema), encoding="utf-8")
        res = runner.invoke(
            app, ["type", "update", str(tid), "--from", str(f), "--json"]
        )
        assert res.exit_code == 0
        payload = json.loads(res.stdout)
        assert payload["data"]["name"] == "改自 from"
        assert len(payload["data"]["custom_fields"]) == 1
