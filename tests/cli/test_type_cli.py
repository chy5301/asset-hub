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


def test_type_define_help_json_includes_valid_field_types():
    """type define --help-json 应在 --fields 参数下嵌套 valid_field_types（FieldType 9 个枚举值）。"""
    from asset_hub.services.field_type import FieldType

    result = runner.invoke(app, ["type", "define", "--help-json"])
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    fields_param = next((p for p in payload["params"] if p["name"] == "--fields"), None)
    assert fields_param is not None, f"未找到 --fields 参数：{payload}"
    assert "valid_field_types" in fields_param, (
        f"--fields 参数缺 valid_field_types：{fields_param}"
    )
    assert fields_param["valid_field_types"] == [t.value for t in FieldType]
    # 显式列 9 个值，防 FieldType 未来漂移悄悄改变 contract
    assert set(fields_param["valid_field_types"]) == {
        "string",
        "text",
        "url",
        "int",
        "float",
        "bool",
        "enum",
        "multi-enum",
        "date",
    }


def test_other_commands_help_json_no_valid_field_types():
    """非 type define 命令的 --help-json 不应被污染（registry 只匹配特定 command）。"""
    result = runner.invoke(app, ["asset", "register", "--help-json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    for p in payload["params"]:
        assert "valid_field_types" not in p, (
            f"asset register 的 {p['name']} 不应有 valid_field_types"
        )
