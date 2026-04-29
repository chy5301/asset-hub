import pytest

from asset_hub.errors import ValidationError
from asset_hub.services.validation import validate_custom_data


def _spec(options: list[str], required: bool = False) -> dict:
    return {
        "key": "tags",
        "label": "标签",
        "type": "multi-enum",
        "required": required,
        "options": options,
    }


def test_multi_enum_accepts_subset():
    result = validate_custom_data(
        [_spec(["a", "b", "c"])], {"tags": ["a", "c"]}
    )
    assert result["tags"] == ["a", "c"]


def test_multi_enum_accepts_empty_list():
    result = validate_custom_data([_spec(["a", "b"])], {"tags": []})
    assert result["tags"] == []


def test_multi_enum_rejects_non_list():
    with pytest.raises(ValidationError, match="标签"):
        validate_custom_data([_spec(["a", "b"])], {"tags": "a"})


def test_multi_enum_rejects_unknown_option():
    with pytest.raises(ValidationError, match="标签"):
        validate_custom_data([_spec(["a", "b"])], {"tags": ["a", "z"]})


def test_multi_enum_required_missing_raises():
    with pytest.raises(ValidationError, match="缺少必填"):
        validate_custom_data(
            [_spec(["a", "b"], required=True)], {}
        )
