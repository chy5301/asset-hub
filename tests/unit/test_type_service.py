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
            {"key": "brand", "label": "品牌", "type": "string", "required": True},
            {"key": "os", "label": "操作系统", "type": "enum", "options": ["Windows", "macOS", "Linux"]},
        ]
        t = svc.create_type(name="笔记本电脑", code_prefix="NB", custom_fields=fields)
        assert len(t.custom_fields) == 2
        assert t.custom_fields[0].key == "brand"

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
        c = svc.create_type(name="C", code_prefix="CC")
        asset_svc = AssetService(session)
        asset_svc.register(name="a1", type_id=a.id, custom_data={})
        asset_svc.register(name="a2", type_id=a.id, custom_data={})
        asset_svc.register(name="b1", type_id=b.id, custom_data={})
        # c 无 asset
        result = {t.name: t.ref_count for t in svc.list_types()}
        assert result == {"A": 2, "B": 1, "C": 0}

    def test_update_returns_correct_ref_count(self, svc: TypeService, session: Session):
        t = svc.create_type(name="A", code_prefix="AA")
        asset_svc = AssetService(session)
        asset_svc.register(name="x", type_id=t.id, custom_data={})
        updated = svc.update_type(t.id, description="新描述")
        assert updated.ref_count == 1
