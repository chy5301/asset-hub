from asset_hub.cli.deps import parse_unset_or_value
from asset_hub.services.transition import _UNSET, _UnsetType


def test_parse_unset_or_value_none_returns_unset():
    """Typer 默认 None（未传）→ _UNSET 哨兵。"""
    result = parse_unset_or_value(None)
    assert isinstance(result, _UnsetType)
    assert result is _UNSET  # 单例


def test_parse_unset_or_value_empty_string_returns_none():
    """显式空字符串 ""（清空约定）→ None。"""
    assert parse_unset_or_value("") is None


def test_parse_unset_or_value_value_returns_value():
    """非空字符串 → 原值。"""
    assert parse_unset_or_value("X") == "X"
    assert parse_unset_or_value("张三") == "张三"
