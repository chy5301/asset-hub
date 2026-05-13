"""envelope.py 升级后的 contract 测试。

验证 6 个域异常 → handle_domain_errors → envelope error shape {code, message} + exit_code。
M3e §2.6 Phase 1 验收点之一。
"""

from __future__ import annotations

import json

import pytest

from asset_hub.cli.envelope import (
    error_envelope,
    handle_domain_errors,
    print_error,
    success_envelope,
)
from asset_hub.errors import (
    ConflictError,
    DuplicateError,
    IllegalTransitionError,
    NotFoundError,
    StateError,
    ValidationError,
)


def test_success_envelope_shape():
    out = json.loads(success_envelope({"id": "abc"}, count=3, took_ms=12.5))
    assert out["success"] is True
    assert out["data"] == {"id": "abc"}
    assert out["metadata"] == {"count": 3, "took_ms": 12.5}
    assert out["error"] is None


def test_error_envelope_shape():
    out = json.loads(error_envelope("Asset 不存在", code="not_found"))
    assert out["success"] is False
    assert out["data"] is None
    assert out["metadata"] == {}
    assert out["error"] == {"code": "not_found", "message": "Asset 不存在"}


@pytest.mark.parametrize(
    "exc,expected_code,expected_exit",
    [
        (NotFoundError("x 不存在"), "not_found", 3),
        (DuplicateError("sn 重复"), "duplicate", 1),
        (ValidationError("字段非法"), "validation", 1),
        (StateError("状态不允许"), "state_conflict", 1),
        (ConflictError("被引用"), "conflict", 1),
        (IllegalTransitionError("非法转换"), "illegal_transition", 1),
    ],
)
def test_handle_domain_errors_maps_code_and_exit(
    capsys, exc, expected_code, expected_exit
):
    with pytest.raises(SystemExit) as ei:
        with handle_domain_errors(json_output=True):
            raise exc

    assert ei.value.code == expected_exit
    out = json.loads(capsys.readouterr().out)
    assert out["error"]["code"] == expected_code
    assert out["error"]["message"] == str(exc)


def test_validation_exit_2_when_usage_flag_set(capsys):
    with pytest.raises(SystemExit) as ei:
        with handle_domain_errors(json_output=True, exit_2_on_validation=True):
            raise ValidationError("无效 UUID")

    assert ei.value.code == 2
    out = json.loads(capsys.readouterr().out)
    assert out["error"] == {"code": "validation", "message": "无效 UUID"}


def test_print_error_requires_keyword_code(capsys):
    """code 是 keyword-only，禁止裸 print_error('失败') 漏 code。"""
    with pytest.raises(TypeError):
        print_error("oops", True)  # 未传 code，应报 TypeError


# ---- v2.0 §4.2: envelope.error 深度结构化（hint / fields_missing / ...） ----

from asset_hub.cli.envelope import _cli_error_payload  # noqa: E402


def test_cli_envelope_error_with_hint_and_fields_missing():
    exc = IllegalTransitionError(
        "REASSIGN 必须改 holder 或 location 至少一项",
        hint="传入 to_holder 或 to_location 至少一项",
        fields_missing=["to_holder", "to_location"],
    )
    payload = _cli_error_payload(exc)
    assert payload == {
        "code": "illegal_transition",
        "message": "REASSIGN 必须改 holder 或 location 至少一项",
        "hint": "传入 to_holder 或 to_location 至少一项",
        "fields_missing": ["to_holder", "to_location"],
    }


def test_cli_envelope_error_excludes_none_fields():
    """无 hint 等可选字段时，envelope.error 不含相应 key（exclude None）。"""
    exc = NotFoundError("asset not found")
    payload = _cli_error_payload(exc)
    assert payload == {"code": "not_found", "message": "asset not found"}
    assert "hint" not in payload
    assert "fields_missing" not in payload
    assert "fields_invalid" not in payload
    assert "affected_resource_id" not in payload


def test_cli_envelope_error_with_fields_invalid():
    exc = ValidationError(
        "validation failed",
        fields_invalid={"sn": "格式错误"},
    )
    payload = _cli_error_payload(exc)
    assert payload["fields_invalid"] == {"sn": "格式错误"}


def test_cli_envelope_error_with_affected_resource_id():
    exc = NotFoundError("asset not found", affected_resource_id="abc-123")
    payload = _cli_error_payload(exc)
    assert payload["affected_resource_id"] == "abc-123"


def test_handle_domain_errors_threads_hint_into_envelope(capsys):
    """handle_domain_errors 把 exc 透传给 print_error，最终 envelope.error 含 hint。"""
    exc = IllegalTransitionError(
        "boom",
        hint="do X",
        fields_missing=["foo"],
    )
    with pytest.raises(SystemExit) as ei:
        with handle_domain_errors(json_output=True):
            raise exc
    assert ei.value.code == 1
    out = json.loads(capsys.readouterr().out)
    assert out["error"]["code"] == "illegal_transition"
    assert out["error"]["hint"] == "do X"
    assert out["error"]["fields_missing"] == ["foo"]
