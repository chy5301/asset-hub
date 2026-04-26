import json
from pathlib import Path
from uuid import uuid4

from typer.testing import CliRunner

from asset_hub.cli.main import app

runner = CliRunner()


def _define_type_and_asset() -> str:
    r = runner.invoke(app, ["type", "define", "--name", "笔记本", "--code-prefix", "NB", "--json"])
    type_id = json.loads(r.stdout)["data"]["id"]
    r = runner.invoke(
        app,
        ["asset", "register", "--name", "X1", "--type-id", type_id, "--json"],
    )
    return json.loads(r.stdout)["data"]["id"]


class TestAttachmentAdd:
    def test_add_photo(self, tmp_path: Path):
        asset_id = _define_type_and_asset()

        photo = tmp_path / "photo.jpg"
        photo.write_bytes(b"fake-jpeg-bytes")

        result = runner.invoke(
            app,
            [
                "attachment",
                "add",
                asset_id,
                "--file",
                str(photo),
                "--kind",
                "photo",
                "--json",
            ],
        )
        assert result.exit_code == 0, result.stdout
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert data["data"]["kind"] == "photo"
        assert data["data"]["size"] == len(b"fake-jpeg-bytes")
        assert data["data"]["mime_type"] == "image/jpeg"
        assert data["data"]["original_name"] == "photo.jpg"
        assert len(data["data"]["sha256"]) == 64

    def test_add_to_nonexistent_asset_exits_3(self, tmp_path: Path):
        photo = tmp_path / "a.jpg"
        photo.write_bytes(b"x")
        result = runner.invoke(
            app,
            [
                "attachment",
                "add",
                str(uuid4()),
                "--file",
                str(photo),
                "--kind",
                "photo",
                "--json",
            ],
        )
        assert result.exit_code == 3

    def test_add_duplicate_exits_1(self, tmp_path: Path):
        asset_id = _define_type_and_asset()
        photo = tmp_path / "a.jpg"
        photo.write_bytes(b"same")

        first = runner.invoke(
            app,
            [
                "attachment", "add", asset_id,
                "--file", str(photo), "--kind", "photo", "--json",
            ],
        )
        assert first.exit_code == 0

        second = runner.invoke(
            app,
            [
                "attachment", "add", asset_id,
                "--file", str(photo), "--kind", "photo", "--json",
            ],
        )
        assert second.exit_code == 1
        data = json.loads(second.stdout)
        assert data["success"] is False
        assert "相同内容" in data["error"]

    def test_add_bad_uuid_exits_2(self, tmp_path: Path):
        photo = tmp_path / "a.jpg"
        photo.write_bytes(b"x")
        result = runner.invoke(
            app,
            [
                "attachment", "add", "not-a-uuid",
                "--file", str(photo), "--kind", "photo", "--json",
            ],
        )
        assert result.exit_code == 2

    def test_add_missing_file_exits_2(self):
        asset_id = _define_type_and_asset()
        result = runner.invoke(
            app,
            [
                "attachment", "add", asset_id,
                "--file", "/no/such/file.jpg", "--kind", "photo", "--json",
            ],
        )
        # typer 的 exists=True 校验会以 usage error（exit 2）退出
        assert result.exit_code == 2


class TestAttachmentList:
    def test_list_empty(self):
        asset_id = _define_type_and_asset()
        result = runner.invoke(
            app, ["attachment", "list", asset_id, "--json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["data"] == []
        assert data["metadata"]["count"] == 0

    def test_list_newest_first(self, tmp_path: Path):
        asset_id = _define_type_and_asset()
        a = tmp_path / "a.jpg"
        a.write_bytes(b"a-bytes")
        b = tmp_path / "b.jpg"
        b.write_bytes(b"b-bytes")

        runner.invoke(app, [
            "attachment", "add", asset_id, "--file", str(a),
            "--kind", "photo", "--json",
        ])
        runner.invoke(app, [
            "attachment", "add", asset_id, "--file", str(b),
            "--kind", "photo", "--json",
        ])

        result = runner.invoke(app, [
            "attachment", "list", asset_id, "--json",
        ])
        data = json.loads(result.stdout)
        assert data["metadata"]["count"] == 2
        assert data["data"][0]["original_name"] == "b.jpg"
        assert data["data"][1]["original_name"] == "a.jpg"

    def test_list_nonexistent_exits_3(self):
        result = runner.invoke(
            app, ["attachment", "list", str(uuid4()), "--json"]
        )
        assert result.exit_code == 3
