import pytest
from sqlmodel import Session

from asset_hub.errors import DuplicateError, NotFoundError
from asset_hub.services.asset_type import TypeService


@pytest.fixture()
def svc(session: Session) -> TypeService:
    return TypeService(session)


class TestCreateType:
    def test_create_minimal(self, svc: TypeService):
        t = svc.create_type(name="笔记本电脑")
        assert t.id is not None
        assert t.name == "笔记本电脑"
        assert t.custom_fields == []
        assert t.created_at is not None

    def test_create_with_custom_fields(self, svc: TypeService):
        fields = [
            {"key": "brand", "label": "品牌", "type": "string", "required": True},
            {"key": "os", "label": "操作系统", "type": "enum", "options": ["Windows", "macOS", "Linux"]},
        ]
        t = svc.create_type(name="笔记本电脑", custom_fields=fields)
        assert len(t.custom_fields) == 2
        assert t.custom_fields[0]["key"] == "brand"

    def test_create_duplicate_name_raises(self, svc: TypeService):
        svc.create_type(name="显卡")
        with pytest.raises(DuplicateError):
            svc.create_type(name="显卡")


class TestGetType:
    def test_get_existing(self, svc: TypeService):
        created = svc.create_type(name="硬盘")
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
        svc.create_type(name="A")
        svc.create_type(name="B")
        result = svc.list_types()
        assert len(result) == 2
        names = {t.name for t in result}
        assert names == {"A", "B"}
