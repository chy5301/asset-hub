import json

from asset_hub.cli.serve.output import (
    ServeError,
    ServiceInfo,
    StartResult,
    StatusReport,
    StopResult,
    render_json_envelope,
    render_plain_start,
    render_plain_status,
    render_plain_stop,
)


def test_start_result_json_envelope_success():
    result = StartResult(
        mode="prod",
        backend=ServiceInfo(pid=12345, port=8000, host="127.0.0.1", log="data/logs/backend.log"),
        frontend=None,
        took_ms=4231,
        build_ran=True,
    )
    out = render_json_envelope(success=True, data=result.to_dict(), metadata=result.metadata())
    parsed = json.loads(out)
    assert parsed["success"] is True
    assert parsed["data"]["backend"]["pid"] == 12345
    assert parsed["data"]["frontend"] is None
    assert parsed["metadata"]["build_ran"] is True


def test_start_result_json_envelope_failure():
    err = ServeError(code="serve.port_occupied", message="port 8000 in use")
    out = render_json_envelope(success=False, error=err.to_dict(), metadata={"took_ms": 12})
    parsed = json.loads(out)
    assert parsed["success"] is False
    assert parsed["error"]["code"] == "serve.port_occupied"


def test_render_plain_start_prod():
    result = StartResult(
        mode="prod",
        backend=ServiceInfo(pid=12345, port=8000, host="127.0.0.1", log="data/logs/backend.log"),
        frontend=None,
        took_ms=100,
        build_ran=False,
    )
    text = render_plain_start(result)
    assert "Backend started" in text
    assert "12345" in text
    assert "Frontend" not in text  # prod 模式无前端


def test_render_plain_start_dev():
    result = StartResult(
        mode="dev",
        backend=ServiceInfo(pid=12345, port=8000, host="127.0.0.1", log="data/logs/backend.log"),
        frontend=ServiceInfo(pid=12346, port=5173, host="127.0.0.1", log="data/logs/frontend.log"),
        took_ms=100,
        build_ran=False,
    )
    text = render_plain_start(result)
    assert "Backend started" in text
    assert "Frontend started" in text


def test_render_plain_status_running():
    report = StatusReport(
        running=True, mode="prod",
        backend={"status": "running", "pid": 12345, "port": 8000, "uptime_sec": 7980, "healthy": True},
        frontend=None, probed=True, took_ms=234,
    )
    text = render_plain_status(report)
    assert "running" in text
    assert "8000" in text


def test_render_plain_stop_normal():
    result = StopResult(stopped=[{"service": "backend", "pid": 12345, "method": "sigterm"}], stale_cleaned=[])
    text = render_plain_stop(result)
    assert "Backend stopped" in text


def test_render_plain_stop_not_running():
    result = StopResult(stopped=[], stale_cleaned=[])
    text = render_plain_stop(result)
    assert "Not running" in text
