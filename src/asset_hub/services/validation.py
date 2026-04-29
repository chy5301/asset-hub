from datetime import date
from typing import Any, Callable
from urllib.parse import urlparse

from asset_hub.errors import ValidationError
from asset_hub.services.field_type import FieldType


def validate_custom_data(custom_fields: list[dict], custom_data: dict) -> dict:
    field_map = {f["key"]: f for f in custom_fields}

    unknown = set(custom_data) - set(field_map)
    if unknown:
        raise ValidationError(f"未知字段: {', '.join(sorted(unknown))}")

    validated: dict[str, Any] = {}
    for key, spec in field_map.items():
        value = custom_data.get(key)
        if value is None:
            if spec.get("required", False):
                raise ValidationError(f"缺少必填字段: {spec['label']}")
            continue
        validated[key] = _coerce(value, spec)

    return validated


def _coerce_string(value: Any, spec: dict) -> Any:
    return str(value)


def _coerce_int(value: Any, spec: dict) -> Any:
    label = spec["label"]
    try:
        n = int(value)
    except (ValueError, TypeError) as e:
        raise ValidationError(f"{label}: 类型转换失败 ({e})") from e
    _check_range(n, spec, label)
    return n


def _coerce_float(value: Any, spec: dict) -> Any:
    label = spec["label"]
    try:
        n = float(value)
    except (ValueError, TypeError) as e:
        raise ValidationError(f"{label}: 类型转换失败 ({e})") from e
    _check_range(n, spec, label)
    return n


def _check_range(n: int | float, spec: dict, label: str) -> None:
    lo = spec.get("min")
    if lo is not None and n < lo:
        raise ValidationError(f"{label}: 不得小于 {lo}（实际 {n}）")
    hi = spec.get("max")
    if hi is not None and n > hi:
        raise ValidationError(f"{label}: 不得大于 {hi}（实际 {n}）")


def _coerce_bool(value: Any, spec: dict) -> Any:
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes")
    return bool(value)


def _coerce_enum(value: Any, spec: dict) -> Any:
    label = spec["label"]
    options = spec.get("options", [])
    s = str(value)
    if s not in options:
        raise ValidationError(f"{label}: '{s}' 不在可选值 {options} 中")
    return s


def _coerce_multi_enum(value: Any, spec: dict) -> Any:
    label = spec["label"]
    options = spec.get("options", [])
    if not isinstance(value, list):
        raise ValidationError(f"{label}: 需要数组")
    coerced: list[str] = []
    for item in value:
        s = str(item)
        if s not in options:
            raise ValidationError(f"{label}: '{s}' 不在可选值 {options} 中")
        coerced.append(s)
    return coerced


def _coerce_date(value: Any, spec: dict) -> Any:
    label = spec["label"]
    if isinstance(value, str):
        try:
            date.fromisoformat(value)
        except ValueError as e:
            raise ValidationError(f"{label}: 类型转换失败 ({e})") from e
        return value
    raise ValidationError(f"{label}: 需要 ISO 日期字符串")


def _coerce_url(value: Any, spec: dict) -> Any:
    label = spec["label"]
    if not isinstance(value, str):
        raise ValidationError(f"{label}: 需要字符串")
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https"):
        raise ValidationError(
            f"{label}: 需要 http/https 协议（实际 '{parsed.scheme or value}'）"
        )
    if not parsed.netloc:
        raise ValidationError(f"{label}: 缺少域名（实际 '{value}'）")
    return value


_DISPATCH: dict[FieldType, Callable[[Any, dict], Any]] = {
    FieldType.STRING: _coerce_string,
    FieldType.TEXT: _coerce_string,
    FieldType.URL: _coerce_url,
    FieldType.INT: _coerce_int,
    FieldType.FLOAT: _coerce_float,
    FieldType.BOOL: _coerce_bool,
    FieldType.ENUM: _coerce_enum,
    FieldType.MULTI_ENUM: _coerce_multi_enum,
    FieldType.DATE: _coerce_date,
}


def _coerce(value: Any, spec: dict) -> Any:
    raw_type = spec["type"]
    try:
        ft = FieldType(raw_type)
    except ValueError:
        raise ValidationError(f"未知字段类型: {raw_type}") from None
    handler = _DISPATCH[ft]
    return handler(value, spec)
