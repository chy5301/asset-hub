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


class TestUpdateExitCodes:
    def test_update_no_change_source_exit_2(self, isolated_db):
        tid = _make_type()
        res = runner.invoke(app, ["type", "update", str(tid), "--json"])
        assert res.exit_code == 2

    def test_update_from_and_name_conflict_exit_2(self, isolated_db, tmp_path):
        tid = _make_type()
        f = tmp_path / "x.json"
        f.write_text('{"name":"x","custom_fields":[]}', encoding="utf-8")
        res = runner.invoke(
            app,
            ["type", "update", str(tid), "--from", str(f), "--name", "y", "--json"],
        )
        assert res.exit_code == 2

    def test_update_invalid_uuid_exit_2(self, isolated_db):
        res = runner.invoke(app, ["type", "update", "not-a-uuid", "--name", "x", "--json"])
        assert res.exit_code == 2

    def test_update_invalid_json_in_file_exit_2(self, isolated_db, tmp_path):
        tid = _make_type()
        f = tmp_path / "bad.json"
        f.write_text("{not json", encoding="utf-8")
        res = runner.invoke(
            app, ["type", "update", str(tid), "--from", str(f), "--json"]
        )
        assert res.exit_code == 2

    def test_update_unknown_id_exit_3(self, isolated_db):
        random_id = uuid.uuid4()
        res = runner.invoke(
            app, ["type", "update", str(random_id), "--name", "x", "--json"]
        )
        assert res.exit_code == 3

    def test_update_duplicate_name_exit_1(self, isolated_db):
        with cli_session() as s:
            TypeService(s).create_type(name="占座", code_prefix="ZZ")
        tid = _make_type(name="待改", prefix="WW")
        res = runner.invoke(
            app, ["type", "update", str(tid), "--name", "占座", "--json"]
        )
        assert res.exit_code == 1
        assert json.loads(res.stdout)["success"] is False


class TestUpdateDryRun:
    def test_update_dry_run_exit_10_outputs_diff(self, isolated_db, tmp_path):
        with cli_session() as s:
            t = TypeService(s).create_type(
                name="原",
                code_prefix="OO",
                description="原描述",
                custom_fields=[{"key": "cpu", "type": "string"}],
            )
            tid = t.id

        schema = {
            "name": "改",
            "description": "新描述",
            "custom_fields": [
                {"key": "ram", "type": "int"},  # 加
                # cpu 删
            ],
        }
        f = tmp_path / "new.json"
        f.write_text(json.dumps(schema), encoding="utf-8")

        res = runner.invoke(
            app,
            ["type", "update", str(tid), "--from", str(f), "--dry-run", "--json"],
        )
        assert res.exit_code == 10
        payload = json.loads(res.stdout)
        assert payload["success"] is True
        diff = payload["data"]["diff"]
        assert diff["name"]["from"] == "原"
        assert diff["name"]["to"] == "改"
        assert len(diff["custom_fields"]["added"]) == 1
        assert diff["custom_fields"]["added"][0]["key"] == "ram"
        assert len(diff["custom_fields"]["removed"]) == 1
        assert diff["custom_fields"]["removed"][0]["key"] == "cpu"
        assert payload["data"]["affected_assets_count"] == 0  # 无引用资产

    def test_update_json_envelope_shape(self, isolated_db):
        tid = _make_type()
        res = runner.invoke(
            app, ["type", "update", str(tid), "--name", "X", "--json"]
        )
        payload = json.loads(res.stdout)
        # success envelope 标准 4 字段
        assert set(payload.keys()) == {"success", "data", "metadata", "error"}
        assert payload["success"] is True
        assert payload["error"] is None
