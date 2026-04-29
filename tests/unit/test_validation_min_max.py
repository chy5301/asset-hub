import pytest

from asset_hub.errors import ValidationError
from asset_hub.services.validation import validate_custom_data


def test_int_within_min_max():
    spec = {"key": "n", "label": "数量", "type": "int", "min": 1, "max": 10}
    result = validate_custom_data([spec], {"n": 5})
    assert result["n"] == 5


def test_int_below_min_raises():
    spec = {"key": "n", "label": "数量", "type": "int", "min": 1}
    with pytest.raises(ValidationError, match="不得小于"):
        validate_custom_data([spec], {"n": 0})


def test_int_above_max_raises():
    spec = {"key": "n", "label": "数量", "type": "int", "max": 10}
    with pytest.raises(ValidationError, match="不得大于"):
        validate_custom_data([spec], {"n": 11})


def test_float_within_range():
    spec = {"key": "x", "label": "比率", "type": "float", "min": 0.0, "max": 1.0}
    result = validate_custom_data([spec], {"x": 0.5})
    assert result["x"] == 0.5


def test_float_above_max_raises():
    spec = {"key": "x", "label": "比率", "type": "float", "max": 1.0}
    with pytest.raises(ValidationError, match="不得大于"):
        validate_custom_data([spec], {"x": 1.5})


def test_int_no_min_max_unbounded():
    spec = {"key": "n", "label": "数量", "type": "int"}
    result = validate_custom_data([spec], {"n": 9999})
    assert result["n"] == 9999
