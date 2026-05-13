import json

from typer.testing import CliRunner

from asset_hub.cli.main import app

runner = CliRunner()


def _define_type(
    name: str = "笔记本电脑", code_prefix: str = "NB", fields: list | None = None
) -> str:
    """Helper: 创建类型并返回 type_id"""
    args = ["type", "define", "--name", name, "--prefix", code_prefix, "--json"]
    if fields:
        args += ["--fields", json.dumps(fields, ensure_ascii=False)]
    r = runner.invoke(app, args)
    return json.loads(r.stdout)["data"]["id"]


class TestAssetRegister:
    def test_register_minimal(self):
        type_id = _define_type()
        result = runner.invoke(
            app,
            [
                "asset",
                "register",
                "--name",
                "ThinkPad X1",
                "--type-id",
                type_id,
                "--json",
            ],
        )
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert data["data"]["name"] == "ThinkPad X1"
        assert data["data"]["status"] == "IDLE"

    def test_register_with_custom_data(self):
        type_id = _define_type(
            fields=[
                {"key": "brand", "label": "品牌", "type": "string", "required": True}
            ]
        )
        result = runner.invoke(
            app,
            [
                "asset",
                "register",
                "--name",
                "ThinkPad X1",
                "--type-id",
                type_id,
                "--custom",
                '{"brand": "Lenovo"}',
                "--json",
            ],
        )
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["data"]["custom_data"]["brand"] == "Lenovo"

    def test_register_bad_type_exits_3(self):
        from uuid import uuid4

        result = runner.invoke(
            app,
            [
                "asset",
                "register",
                "--name",
                "X",
                "--type-id",
                str(uuid4()),
                "--json",
            ],
        )
        assert result.exit_code == 3


class TestAssetRegisterAcquiredAt:
    def test_register_with_acquired_at(self):
        type_id = _define_type()
        result = runner.invoke(
            app,
            [
                "asset",
                "register",
                "--name",
                "X1",
                "--type-id",
                type_id,
                "--acquired-at",
                "2025-01-15",
                "--json",
            ],
        )
        assert result.exit_code == 0
        body = json.loads(result.stdout)
        assert body["success"] is True
        assert body["data"]["acquired_at"] == "2025-01-15"
        assert body["data"]["asset_code"].startswith("NB-")


class TestAssetRegisterModel:
    def test_register_with_model_flag(self):
        """asset register --model 'X' 持久化 model。"""
        type_id = _define_type()
        result = runner.invoke(
            app,
            [
                "asset",
                "register",
                "--name",
                "开发本-01",
                "--type-id",
                type_id,
                "--model",
                "ThinkPad X1 Carbon Gen 9",
                "--json",
            ],
        )
        assert result.exit_code == 0
        body = json.loads(result.stdout)
        assert body["success"] is True
        assert body["data"]["model"] == "ThinkPad X1 Carbon Gen 9"

    def test_register_without_model_flag(self):
        """asset register 不传 --model 时 model 是 None。"""
        type_id = _define_type()
        result = runner.invoke(
            app,
            [
                "asset",
                "register",
                "--name",
                "X",
                "--type-id",
                type_id,
                "--json",
            ],
        )
        assert result.exit_code == 0
        body = json.loads(result.stdout)
        assert body["success"] is True
        assert body["data"]["model"] is None


class TestAssetList:
    def test_list_empty(self):
        result = runner.invoke(app, ["asset", "list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["data"] == []

    def test_list_with_filter(self):
        type_id = _define_type()
        runner.invoke(app, ["asset", "register", "--name", "A", "--type-id", type_id])
        runner.invoke(app, ["asset", "register", "--name", "B", "--type-id", type_id])
        result = runner.invoke(app, ["asset", "list", "--json"])
        data = json.loads(result.stdout)
        assert data["metadata"]["count"] == 2


class TestAssetShow:
    def test_show_existing(self):
        type_id = _define_type()
        r = runner.invoke(
            app,
            [
                "asset",
                "register",
                "--name",
                "X1",
                "--type-id",
                type_id,
                "--json",
            ],
        )
        asset_id = json.loads(r.stdout)["data"]["id"]
        result = runner.invoke(app, ["asset", "show", asset_id, "--json"])
        assert result.exit_code == 0
        assert json.loads(result.stdout)["data"]["name"] == "X1"

    def test_show_nonexistent_exits_3(self):
        from uuid import uuid4

        result = runner.invoke(app, ["asset", "show", str(uuid4()), "--json"])
        assert result.exit_code == 3


class TestAssetUpdate:
    def test_update_notes(self):
        type_id = _define_type()
        r = runner.invoke(
            app,
            [
                "asset",
                "register",
                "--name",
                "X1",
                "--type-id",
                type_id,
                "--json",
            ],
        )
        asset_id = json.loads(r.stdout)["data"]["id"]
        result = runner.invoke(
            app,
            [
                "asset",
                "update",
                asset_id,
                "--set",
                '{"notes": "新备注"}',
                "--json",
            ],
        )
        assert result.exit_code == 0
        assert json.loads(result.stdout)["data"]["notes"] == "新备注"


class TestAssetListSort:
    def test_asset_list_with_sort_idle_days(self, isolated_db_with_idle_assets):
        """smoke test: --sort idle_days --limit 5 透传 + 输出含 idle_days
        （sort 顺序由 service 层 unit 测试覆盖；此处不做精确顺序断言）."""
        result = runner.invoke(
            app,
            [
                "asset",
                "list",
                "--status",
                "IDLE",
                "--sort",
                "idle_days",
                "--order",
                "desc",
                "--limit",
                "5",
                "--json",
            ],
        )
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["success"] is True
        assert len(payload["data"]) == 5
        # spec §2.6 等价性：data 中每个 IDLE asset 必须含非 null idle_days
        for asset in payload["data"]:
            assert asset["idle_days"] is not None

    def test_asset_list_unknown_sort_field_exits_2(self):
        result = runner.invoke(app, ["asset", "list", "--sort", "bogus", "--json"])
        assert result.exit_code == 2
        payload = json.loads(result.stdout)
        assert payload["success"] is False
        assert payload["error"]["code"] == "validation"
        assert "sort_by" in payload["error"]["message"]

    def test_asset_list_limit_over_max_exits_2(self):
        result = runner.invoke(app, ["asset", "list", "--limit", "2000", "--json"])
        assert result.exit_code == 2
        payload = json.loads(result.stdout)
        assert payload["success"] is False
        assert payload["error"]["code"] == "validation"
        assert "limit" in payload["error"]["message"]

    def test_asset_list_bad_order_exits_2(self):
        """--order 取无效值（非 asc/desc）走 service ValidationError → exit 2."""
        result = runner.invoke(app, ["asset", "list", "--order", "up", "--json"])
        assert result.exit_code == 2
        payload = json.loads(result.stdout)
        assert payload["success"] is False
        assert payload["error"]["code"] == "validation"
        assert "sort_order" in payload["error"]["message"]

    def test_asset_list_include_retired_returns_retired(self, isolated_db):
        """--include-retired flag 让 RETIRED 资产出现在结果中（spec §B.3）."""
        from asset_hub.cli.deps import cli_session
        from asset_hub.models.asset import Asset, AssetStatus
        from asset_hub.services.asset_type import TypeService

        with cli_session() as session:
            type_svc = TypeService(session)
            at = type_svc.create_type(
                name="RetTest", code_prefix="RTI", custom_fields=[]
            )
            retired = Asset(
                asset_code="RTI-001",
                name="R1",
                type_id=at.id,
                status=AssetStatus.RETIRED,
            )
            session.add(retired)
            session.commit()

        # 默认（不带 --include-retired）应排除 RETIRED
        result_default = runner.invoke(app, ["asset", "list", "--json"])
        assert result_default.exit_code == 0
        payload_default = json.loads(result_default.stdout)
        codes_default = [a["asset_code"] for a in payload_default["data"]]
        assert "RTI-001" not in codes_default

        # 带 --include-retired 应包含 RETIRED
        result_with = runner.invoke(
            app, ["asset", "list", "--include-retired", "--json"]
        )
        assert result_with.exit_code == 0
        payload_with = json.loads(result_with.stdout)
        codes_with = [a["asset_code"] for a in payload_with["data"]]
        assert "RTI-001" in codes_with


class TestAssetIdleDays:
    def test_asset_show_idle_asset_includes_idle_days(
        self, isolated_db_with_idle_assets
    ):
        """IDLE 资产 show CLI 输出必须含 idle_days int（与 API 一致）。"""
        list_result = runner.invoke(
            app,
            [
                "asset",
                "list",
                "--status",
                "IDLE",
                "--limit",
                "1",
                "--json",
            ],
        )
        asset_id = json.loads(list_result.stdout)["data"][0]["id"]

        show_result = runner.invoke(app, ["asset", "show", asset_id, "--json"])
        assert show_result.exit_code == 0
        payload = json.loads(show_result.stdout)
        assert payload["success"] is True
        assert isinstance(payload["data"]["idle_days"], int)
        assert payload["data"]["idle_days"] >= 0

    def test_asset_register_returns_idle_days(self):
        """register 创建的新资产（IDLE）应返 idle_days=0（刚登记）。"""
        type_id = _define_type(name="IdleDayType", code_prefix="IDT")
        result = runner.invoke(
            app,
            [
                "asset",
                "register",
                "--name",
                "IdleDayAsset",
                "--type-id",
                type_id,
                "--json",
            ],
        )
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["success"] is True
        assert isinstance(payload["data"]["idle_days"], int)
        assert payload["data"]["idle_days"] >= 0

    def test_asset_update_returns_idle_days(self):
        """update IDLE 资产后输出应含 idle_days int。"""
        type_id = _define_type(name="IdleDayType2", code_prefix="IDLT")
        r = runner.invoke(
            app,
            [
                "asset",
                "register",
                "--name",
                "IdleAsset2",
                "--type-id",
                type_id,
                "--json",
            ],
        )
        asset_id = json.loads(r.stdout)["data"]["id"]

        result = runner.invoke(
            app,
            [
                "asset",
                "update",
                asset_id,
                "--set",
                '{"notes": "idle update test"}',
                "--json",
            ],
        )
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["success"] is True
        assert isinstance(payload["data"]["idle_days"], int)
        assert payload["data"]["idle_days"] >= 0


class TestAssetUpdateModel:
    def _register_with_model(self, type_id: str, model_value: str = "原型号") -> str:
        r = runner.invoke(
            app,
            [
                "asset",
                "register",
                "--name",
                "X",
                "--type-id",
                type_id,
                "--model",
                model_value,
                "--json",
            ],
        )
        assert r.exit_code == 0
        return json.loads(r.stdout)["data"]["id"]

    def test_update_via_set_json_model(self):
        """asset update <id> --set '{"model": "新值"}' 设置 model。"""
        type_id = _define_type()
        asset_id = self._register_with_model(type_id)
        result = runner.invoke(
            app,
            [
                "asset",
                "update",
                asset_id,
                "--set",
                json.dumps({"model": "新型号"}),
                "--json",
            ],
        )
        assert result.exit_code == 0
        body = json.loads(result.stdout)
        assert body["success"] is True
        assert body["data"]["model"] == "新型号"

    def test_update_via_set_json_null_clears_model(self):
        """asset update <id> --set '{"model": null}' 显式清空 model。"""
        type_id = _define_type()
        asset_id = self._register_with_model(type_id)
        result = runner.invoke(
            app,
            [
                "asset",
                "update",
                asset_id,
                "--set",
                json.dumps({"model": None}),
                "--json",
            ],
        )
        assert result.exit_code == 0
        body = json.loads(result.stdout)
        assert body["success"] is True
        assert body["data"]["model"] is None


class TestAssetListModelSearch:
    def test_list_search_q_matches_model(self):
        """asset list -q 关键词命中 model。"""
        type_id = _define_type()
        runner.invoke(
            app,
            [
                "asset",
                "register",
                "--name",
                "A",
                "--type-id",
                type_id,
                "--model",
                "ThinkPad X1",
                "--json",
            ],
        )
        runner.invoke(
            app,
            [
                "asset",
                "register",
                "--name",
                "B",
                "--type-id",
                type_id,
                "--model",
                "MacBook Pro",
                "--json",
            ],
        )

        result = runner.invoke(
            app,
            [
                "asset",
                "list",
                "--q",
                "ThinkPad",
                "--json",
            ],
        )
        assert result.exit_code == 0
        body = json.loads(result.stdout)
        assert body["success"] is True
        items = body["data"]
        assert len(items) == 1
        assert items[0]["model"] == "ThinkPad X1"

    def test_list_sort_by_model(self):
        """asset list --sort model --order asc 透传 service，OK 返回。"""
        result = runner.invoke(
            app,
            [
                "asset",
                "list",
                "--sort",
                "model",
                "--order",
                "asc",
                "--json",
            ],
        )
        assert result.exit_code == 0
        body = json.loads(result.stdout)
        assert body["success"] is True

    def test_list_sort_by_serial_number(self):
        """v1 顺修：asset list --sort serial_number --order asc 透传 service，OK 返回。"""
        result = runner.invoke(
            app,
            [
                "asset",
                "list",
                "--sort",
                "serial_number",
                "--order",
                "asc",
                "--json",
            ],
        )
        assert result.exit_code == 0
        body = json.loads(result.stdout)
        assert body["success"] is True


class TestAssetDelete:
    def test_delete_existing(self):
        type_id = _define_type()
        r = runner.invoke(
            app,
            [
                "asset",
                "register",
                "--name",
                "X1",
                "--type-id",
                type_id,
                "--json",
            ],
        )
        asset_id = json.loads(r.stdout)["data"]["id"]
        result = runner.invoke(app, ["asset", "delete", asset_id, "--yes", "--json"])
        assert result.exit_code == 0

    def test_delete_dry_run_exits_10(self):
        type_id = _define_type()
        r = runner.invoke(
            app,
            [
                "asset",
                "register",
                "--name",
                "X1",
                "--type-id",
                type_id,
                "--json",
            ],
        )
        asset_id = json.loads(r.stdout)["data"]["id"]
        result = runner.invoke(
            app, ["asset", "delete", asset_id, "--dry-run", "--json"]
        )
        assert result.exit_code == 10
        # 验证资产仍然存在
        check = runner.invoke(app, ["asset", "show", asset_id, "--json"])
        assert check.exit_code == 0
