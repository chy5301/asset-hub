import pytest

from asset_hub.errors import ValidationError
from asset_hub.services.validation import validate_custom_data


def _spec(t: str, label: str = "网址", required: bool = False, **extra) -> dict:
    return {
        "key": "url_field",
        "label": label,
        "type": t,
        "required": required,
        **extra,
    }


def test_url_accepts_https():
    result = validate_custom_data(
        [_spec("url")], {"url_field": "https://example.com/path?q=1"}
    )
    assert result["url_field"] == "https://example.com/path?q=1"


def test_url_accepts_http():
    result = validate_custom_data([_spec("url")], {"url_field": "http://example.com"})
    assert result["url_field"] == "http://example.com"


def test_url_rejects_missing_scheme():
    with pytest.raises(ValidationError, match="网址"):
        validate_custom_data([_spec("url")], {"url_field": "example.com"})


def test_url_rejects_unsupported_scheme():
    with pytest.raises(ValidationError, match="网址"):
        validate_custom_data([_spec("url")], {"url_field": "ftp://example.com"})


def test_url_rejects_missing_netloc():
    with pytest.raises(ValidationError, match="网址"):
        validate_custom_data([_spec("url")], {"url_field": "http://"})


def test_url_rejects_non_string():
    with pytest.raises(ValidationError, match="网址"):
        validate_custom_data([_spec("url")], {"url_field": 123})
