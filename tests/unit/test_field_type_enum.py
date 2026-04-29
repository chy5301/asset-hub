import pytest

from asset_hub.services.field_type import FieldType


def test_field_type_values():
    assert FieldType.STRING.value == "string"
    assert FieldType.TEXT.value == "text"
    assert FieldType.URL.value == "url"
    assert FieldType.INT.value == "int"
    assert FieldType.FLOAT.value == "float"
    assert FieldType.BOOL.value == "bool"
    assert FieldType.ENUM.value == "enum"
    assert FieldType.MULTI_ENUM.value == "multi-enum"
    assert FieldType.DATE.value == "date"


def test_field_type_from_legacy_string():
    assert FieldType("string") is FieldType.STRING
    assert FieldType("multi-enum") is FieldType.MULTI_ENUM


def test_field_type_unknown_raises():
    with pytest.raises(ValueError):
        FieldType("unknown")
