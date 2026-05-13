"""v2.0 域异常 class 可选字段单元测试（spec §4.2）。

每个域异常应支持：
- positional message（与 v1.0 backward compat）
- 可选 kwargs: hint / fields_missing / fields_invalid / affected_resource_id
- 类属性 code（envelope 序列化时取代 _DOMAIN_ERROR_CODES dict 查询）
"""
from __future__ import annotations

from asset_hub.errors import (
    AssetHubError,
    ConflictError,
    DuplicateError,
    IllegalTransitionError,
    NotFoundError,
    StateError,
    ValidationError,
)


def test_illegal_transition_with_hint():
    err = IllegalTransitionError(
        "REASSIGN 必须改 holder 或 location 至少一项",
        hint="传入 --to-holder 或 --to-location 至少一项",
        fields_missing=["to_holder", "to_location"],
    )
    assert err.message == "REASSIGN 必须改 holder 或 location 至少一项"
    assert err.hint == "传入 --to-holder 或 --to-location 至少一项"
    assert err.fields_missing == ["to_holder", "to_location"]
    assert err.fields_invalid is None
    assert err.affected_resource_id is None


def test_validation_with_fields_invalid():
    err = ValidationError(
        "type field validation failed",
        fields_invalid={"sn": "格式错误，预期 [A-Z]{3}-\\d{4}"},
    )
    assert err.fields_invalid == {"sn": "格式错误，预期 [A-Z]{3}-\\d{4}"}
    assert err.hint is None
    assert err.fields_missing is None


def test_not_found_with_affected_resource_id():
    err = NotFoundError("asset not found", affected_resource_id="abc-123")
    assert err.affected_resource_id == "abc-123"
    assert err.message == "asset not found"


def test_error_class_backward_compatible():
    """旧调用方式仍可用（仅 positional message），所有新字段默认 None。"""
    err = IllegalTransitionError("foo")
    assert err.message == "foo"
    assert err.hint is None
    assert err.fields_missing is None
    assert err.fields_invalid is None
    assert err.affected_resource_id is None
    # str(err) 仍然返回 message（Exception 默认行为）
    assert str(err) == "foo"


def test_all_subclasses_have_code_attr():
    """6 个子类各自有 class-level code 属性，envelope 序列化时取代 dict 查询。"""
    assert NotFoundError.code == "not_found"
    assert DuplicateError.code == "duplicate"
    assert ValidationError.code == "validation"
    assert StateError.code == "state_conflict"
    assert ConflictError.code == "conflict"
    assert IllegalTransitionError.code == "illegal_transition"


def test_base_class_no_code():
    """AssetHubError base class 不应自带 code（仅子类有）。"""
    assert not hasattr(AssetHubError, "code") or AssetHubError.code is None or AssetHubError.code == ""
