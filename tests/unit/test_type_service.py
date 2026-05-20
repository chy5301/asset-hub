import pytest
from sqlmodel import Session

from asset_hub.errors import DuplicateError, NotFoundError, ValidationError
from asset_hub.services.asset import AssetService
from asset_hub.services.asset_type import TypeService


@pytest.fixture()
def svc(session: Session) -> TypeService:
    return TypeService(session)


class TestCreateType:
    def test_create_minimal(self, svc: TypeService):
        t = svc.create_type(name="笔记本电脑", code_prefix="NB")
        assert t.id is not None
        assert t.name == "笔记本电脑"
        assert t.custom_fields == []
        assert t.created_at is not None

    def test_create_with_custom_fields(self, svc: TypeService):
        fields = [
            {"key": "cpu", "label": "处理器", "type": "string", "required": True},
            {
                "key": "os",
                "label": "操作系统",
                "type": "enum",
                "options": ["Windows", "macOS", "Linux"],
            },
        ]
        t = svc.create_type(name="笔记本电脑", code_prefix="NB", custom_fields=fields)
        assert len(t.custom_fields) == 2
        assert t.custom_fields[0].key == "cpu"

    def test_create_duplicate_name_raises(self, svc: TypeService):
        svc.create_type(name="显卡", code_prefix="GPU")
        with pytest.raises(DuplicateError):
            svc.create_type(name="显卡", code_prefix="GPX")


class TestCreateTypeCodePrefix:
    def test_create_type_requires_code_prefix(self, svc: TypeService):
        with pytest.raises(ValidationError, match="code_prefix"):
            svc.create_type(name="笔记本电脑", code_prefix="")  # 空值

    def test_create_type_validates_prefix_format(self, svc: TypeService):
        with pytest.raises(ValidationError, match="code_prefix.*格式"):
            svc.create_type(name="笔记本电脑", code_prefix="N")  # 仅 1 字符
        with pytest.raises(ValidationError, match="code_prefix.*格式"):
            svc.create_type(name="笔记本电脑", code_prefix="LAPTOP")  # 5+ 字符

    def test_create_type_normalizes_prefix_to_upper(self, svc: TypeService):
        t = svc.create_type(name="笔记本电脑", code_prefix="nb")  # 用户输入小写
        assert t.code_prefix == "NB"

    def test_create_type_unique_prefix(self, svc: TypeService):
        svc.create_type(name="笔记本", code_prefix="NB")
        with pytest.raises(DuplicateError, match="code_prefix"):
            svc.create_type(name="笔记本电脑", code_prefix="NB")


class TestGetType:
    def test_get_existing(self, svc: TypeService):
        created = svc.create_type(name="硬盘", code_prefix="HD")
        fetched = svc.get_type(created.id)
        assert fetched.name == "硬盘"

    def test_get_nonexistent_raises(self, svc: TypeService):
        from uuid import uuid4

        with pytest.raises(NotFoundError):
            svc.get_type(uuid4())


class TestListTypes:
    def test_list_empty(self, svc: TypeService):
        assert svc.list_types() == []

    def test_list_multiple(self, svc: TypeService):
        svc.create_type(name="A", code_prefix="AAA")
        svc.create_type(name="B", code_prefix="BBB")
        result = svc.list_types()
        assert len(result) == 2
        names = {t.name for t in result}
        assert names == {"A", "B"}


class TestRefCount:
    """§Q：TypeRead.ref_count 经 service 层批量 GROUP BY 富化"""

    def test_create_returns_zero_ref_count(self, svc: TypeService):
        t = svc.create_type(name="A", code_prefix="AA")
        assert t.ref_count == 0

    def test_get_includes_ref_count_zero(self, svc: TypeService):
        t = svc.create_type(name="A", code_prefix="AA")
        fetched = svc.get_type(t.id)
        assert fetched.ref_count == 0

    def test_get_includes_ref_count_with_assets(
        self, svc: TypeService, session: Session
    ):
        t = svc.create_type(name="A", code_prefix="AA")
        asset_svc = AssetService(session)
        for i in range(3):
            asset_svc.register(name=f"asset-{i}", type_id=t.id, custom_data={})
        fetched = svc.get_type(t.id)
        assert fetched.ref_count == 3

    def test_list_batch_count_per_type(self, svc: TypeService, session: Session):
        a = svc.create_type(name="A", code_prefix="AA")
        b = svc.create_type(name="B", code_prefix="BB")
        svc.create_type(
            name="C", code_prefix="CC"
        )  # C 无 asset，验证 GROUP BY 包含 0 计数
        asset_svc = AssetService(session)
        asset_svc.register(name="a1", type_id=a.id, custom_data={})
        asset_svc.register(name="a2", type_id=a.id, custom_data={})
        asset_svc.register(name="b1", type_id=b.id, custom_data={})
        result = {t.name: t.ref_count for t in svc.list_types()}
        assert result == {"A": 2, "B": 1, "C": 0}

    def test_update_returns_correct_ref_count(self, svc: TypeService, session: Session):
        t = svc.create_type(name="A", code_prefix="AA")
        asset_svc = AssetService(session)
        asset_svc.register(name="x", type_id=t.id, custom_data={})
        updated = svc.update_type(t.id, description="新描述")
        assert updated.ref_count == 1


class TestReservedKeys:
    """CL-1：AssetType custom_fields[].key 加 reserved 全集 16 项校验。"""

    def test_create_type_rejects_reserved_custom_field_key_brand(
        self, svc: TypeService
    ):
        """create_type 含 reserved key 'brand' 的 custom_field 应 ValidationError + hint。"""
        with pytest.raises(ValidationError) as exc:
            svc.create_type(
                name="Test",
                code_prefix="TST",
                custom_fields=[{"key": "brand", "label": "品牌", "type": "string"}],
            )
        msg = str(exc.value)
        assert "brand" in msg
        assert "reserved" in msg.lower() or "顶层" in msg

    @pytest.mark.parametrize(
        "reserved_key",
        [
            # Asset 顶层 user-writable 字段
            "asset_code",
            "serial_number",
            "name",
            "model",
            "brand",
            "holder",
            "location",
            "notes",
            "acquired_at",
            # CLI 直觉别名
            "sn",
            # 系统/关系字段
            "type",
            "type_name",
            "type_id",
            "status",
            "id",
            "custom_data",
        ],
    )
    def test_create_type_rejects_all_reserved_keys(
        self, svc: TypeService, reserved_key: str
    ):
        """全集 16 项 reserved 都应被拒。"""
        with pytest.raises(ValidationError):
            svc.create_type(
                name=f"Test-{reserved_key}",
                code_prefix="TST",
                custom_fields=[{"key": reserved_key, "label": "x", "type": "string"}],
            )

    def test_create_type_accepts_non_reserved_key(self, svc: TypeService):
        """非 reserved key 应通过。"""
        result = svc.create_type(
            name="Test-OK",
            code_prefix="TOK",
            custom_fields=[
                {"key": "warranty_until", "label": "保修截止", "type": "date"}
            ],
        )
        assert result.id is not None

    def test_update_type_also_rejects_reserved_key(self, svc: TypeService):
        """update_type 同样应校验 reserved。"""
        t = svc.create_type(name="T1", code_prefix="TBB", custom_fields=[])
        with pytest.raises(ValidationError):
            svc.update_type(
                type_id=t.id,
                custom_fields=[{"key": "model", "label": "型号", "type": "string"}],
            )
