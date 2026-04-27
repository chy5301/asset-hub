from datetime import date
from typing import Any

from asset_hub.errors import ValidationError


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


def _coerce(value: Any, spec: dict) -> Any:
    t = spec["type"]
    label = spec["label"]
    try:
        if t in ("string", "text"):
            return str(value)
        if t == "int":
            return int(value)
        if t == "float":
            return float(value)
        if t == "bool":
            if isinstance(value, str):
                return value.lower() in ("true", "1", "yes")
            return bool(value)
        if t == "enum":
            s = str(value)
            options = spec.get("options", [])
            if s not in options:
                raise ValidationError(f"{label}: '{s}' 不在可选值 {options} 中")
            return s
        if t == "date":
            if isinstance(value, str):
                date.fromisoformat(value)
                return value
            raise ValidationError(f"{label}: 需要 ISO 日期字符串")
    except (ValueError, TypeError) as e:
        raise ValidationError(f"{label}: 类型转换失败 ({e})") from e
    raise ValidationError(f"未知字段类型: {t}")
