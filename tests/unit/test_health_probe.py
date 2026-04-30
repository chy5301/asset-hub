from unittest.mock import MagicMock, patch
from urllib.error import URLError

from asset_hub.cli.serve.probe import (
    SLEEP_INTERVALS,
    probe_once,
    probe_until_ready,
)


def test_probe_returns_ok_on_first_success():
    fake_response = MagicMock()
    fake_response.__enter__.return_value = fake_response
    fake_response.__exit__.return_value = False
    fake_response.status = 200

    with patch("asset_hub.cli.serve.probe._open", return_value=fake_response), \
         patch("asset_hub.cli.serve.probe.time.sleep"):
        result = probe_until_ready("http://x/healthz")
    assert result.ok is True


def test_probe_returns_timeout_after_all_intervals():
    with patch(
        "asset_hub.cli.serve.probe._open",
        side_effect=URLError("conn refused"),
    ), patch("asset_hub.cli.serve.probe.time.sleep"):
        result = probe_until_ready("http://x/healthz")
    assert result.ok is False


def test_probe_succeeds_mid_loop():
    fake_response = MagicMock()
    fake_response.__enter__.return_value = fake_response
    fake_response.__exit__.return_value = False
    fake_response.status = 200

    side_effects = [URLError("not yet"), URLError("not yet"), fake_response]

    with patch(
        "asset_hub.cli.serve.probe._open", side_effect=side_effects
    ), patch("asset_hub.cli.serve.probe.time.sleep"):
        result = probe_until_ready("http://x/healthz")
    assert result.ok is True


def test_sleep_intervals_total_about_10s():
    assert 9.0 < sum(SLEEP_INTERVALS) < 11.0


def test_probe_once_returns_true_on_200():
    fake_response = MagicMock()
    fake_response.__enter__.return_value = fake_response
    fake_response.__exit__.return_value = False
    fake_response.status = 200
    with patch("asset_hub.cli.serve.probe._open", return_value=fake_response):
        assert probe_once("http://x/healthz") is True


def test_probe_once_returns_false_on_error():
    with patch("asset_hub.cli.serve.probe._open", side_effect=URLError("x")):
        assert probe_once("http://x/healthz") is False
