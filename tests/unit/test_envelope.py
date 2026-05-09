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
def test_handle_domain_errors_maps_code_and_exit(capsys, exc, expected_code, expected_exit):
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
