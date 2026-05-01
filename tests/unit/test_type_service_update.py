import pytest
from sqlmodel import Session

from asset_hub.errors import DuplicateError, NotFoundError, ValidationError
from asset_hub.services.asset_type import TypeService


@pytest.fixture()
def svc(session: Session) -> TypeService:
    return TypeService(session)


class TestUpdateType:
    def test_update_name_only(self, svc: TypeService):
        t = svc.create_type(name="原名", code_prefix="OO")
        updated = svc.update_type(t.id, name="新名")
        assert updated.name == "新名"
        assert updated.code_prefix == "OO"  # 不动
        assert updated.description is None  # 不动

    def test_update_description_only(self, svc: TypeService):
        t = svc.create_type(name="A", code_prefix="AA", description="原描述")
        updated = svc.update_type(t.id, description="新描述")
        assert updated.name == "A"
        assert updated.description == "新描述"

    def test_update_custom_fields_replace(self, svc: TypeService):
        t = svc.create_type(
            name="B", code_prefix="BB",
            custom_fields=[{"key": "old", "type": "string"}],
        )
        new_fields = [
            {"key": "cpu", "type": "string", "required": True},
            {"key": "ram", "type": "int"},
        ]
        updated = svc.update_type(t.id, custom_fields=new_fields)
        assert len(updated.custom_fields) == 2
        assert updated.custom_fields[0]["key"] == "cpu"
        # 旧字段完全替换（不是合并）
        assert all(f["key"] != "old" for f in updated.custom_fields)

    def test_update_combined_all_three(self, svc: TypeService):
        t = svc.create_type(name="C", code_prefix="CC", description="d1")
        updated = svc.update_type(
            t.id,
            name="C2",
            description="d2",
            custom_fields=[{"key": "x", "type": "string"}],
        )
        assert updated.name == "C2"
        assert updated.description == "d2"
        assert len(updated.custom_fields) == 1

    def test_update_partial_does_not_clear_unset_fields(self, svc: TypeService):
        # 三参数都默认 None → 不动任何字段
        t = svc.create_type(
            name="D", code_prefix="DD", description="orig",
            custom_fields=[{"key": "k1", "type": "string"}],
        )
        updated = svc.update_type(t.id)
        assert updated.name == "D"
        assert updated.description == "orig"
        assert len(updated.custom_fields) == 1

    def test_update_does_not_touch_code_prefix(self, svc: TypeService):
        # service 签名根本不接收 code_prefix
        t = svc.create_type(name="E", code_prefix="EE")
        updated = svc.update_type(t.id, name="E2")
        assert updated.code_prefix == "EE"

    def test_update_not_found_raises_404(self, svc: TypeService):
        import uuid
        with pytest.raises(NotFoundError):
            svc.update_type(uuid.uuid4(), name="x")

    def test_update_duplicate_name_raises(self, svc: TypeService):
        svc.create_type(name="占座", code_prefix="ZZ")
        t = svc.create_type(name="待改", code_prefix="WW")
        with pytest.raises(DuplicateError, match="名称"):
            svc.update_type(t.id, name="占座")  # name 撞车

    def test_update_invalid_field_def_raises_validation(self, svc: TypeService):
        t = svc.create_type(name="V", code_prefix="VV")
        # CustomFieldDef.type 是必填，缺字段会被 model_validate 拒
        bad = [{"key": "x"}]  # 缺 type
        with pytest.raises(ValidationError, match="custom_fields"):
            svc.update_type(t.id, custom_fields=bad)
