import json

from typer.testing import CliRunner

from asset_hub.cli.main import app

runner = CliRunner()


class TestTypeDefine:
    def test_define_with_name(self):
        result = runner.invoke(
            app, ["type", "define", "--name", "笔记本电脑", "--prefix", "NB", "--json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert data["data"]["name"] == "笔记本电脑"
        assert data["data"]["code_prefix"] == "NB"
        assert "id" in data["data"]

    def test_define_from_file(self, isolated_db):
        schema = {
            "name": "显卡",
            "code_prefix": "GPU",
            "description": "GPU",
            "custom_fields": [
                {"key": "brand", "label": "品牌", "type": "string", "required": True}
            ],
        }
        schema_path = isolated_db / "gpu.json"
        schema_path.write_text(json.dumps(schema, ensure_ascii=False), encoding="utf-8")

        result = runner.invoke(
            app, ["type", "define", "--from", str(schema_path), "--json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["data"]["name"] == "显卡"
        assert data["data"]["code_prefix"] == "GPU"
        assert len(data["data"]["custom_fields"]) == 1

    def test_define_duplicate_exits_1(self):
        runner.invoke(app, ["type", "define", "--name", "硬盘", "--prefix", "HD"])
        # 不同 prefix 但同 name → DuplicateError
        result = runner.invoke(
            app, ["type", "define", "--name", "硬盘", "--prefix", "HDX", "--json"]
        )
        assert result.exit_code == 1
        data = json.loads(result.stdout)
        assert data["success"] is False

    def test_define_requires_prefix(self):
        """缺 --prefix → exit_code=2（用法错）"""
        result = runner.invoke(
            app,
            [
                "type",
                "define",
                "--name",
                "笔记本电脑",
                "--json",
            ],
        )
        assert result.exit_code == 2


class TestTypeList:
    def test_list_empty(self):
        result = runner.invoke(app, ["type", "list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["data"] == []
        assert data["metadata"]["count"] == 0

    def test_list_after_define(self):
        runner.invoke(app, ["type", "define", "--name", "A", "--prefix", "AA"])
        runner.invoke(app, ["type", "define", "--name", "B", "--prefix", "BB"])
        result = runner.invoke(app, ["type", "list", "--json"])
        data = json.loads(result.stdout)
        assert data["metadata"]["count"] == 2


class TestTypeShow:
    def test_show_existing(self):
        r = runner.invoke(
            app, ["type", "define", "--name", "硬盘", "--prefix", "HD", "--json"]
        )
        type_id = json.loads(r.stdout)["data"]["id"]
        result = runner.invoke(app, ["type", "show", type_id, "--json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["data"]["name"] == "硬盘"

    def test_show_nonexistent_exits_3(self):
        from uuid import uuid4

        result = runner.invoke(app, ["type", "show", str(uuid4()), "--json"])
        assert result.exit_code == 3
