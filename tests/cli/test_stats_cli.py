import json

from typer.testing import CliRunner

from asset_hub.cli.main import app

runner = CliRunner()


def test_stats_default_json_envelope(populated_cli_db):
    result = runner.invoke(app, ["stats", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["success"] is True
    assert payload["error"] is None
    data = payload["data"]
    assert "type_distribution" in data
    assert "status_distribution" in data
    assert "holder_ranking" in data
    assert "idle_top" in data
    assert "summary" in data


def test_stats_fields_idle_top_only(populated_cli_db):
    result = runner.invoke(app, ["stats", "--fields", "idle_top", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)["data"]
    assert data.get("idle_top") is not None
    assert data.get("type_distribution") is None
    assert data["summary"] is not None


def test_stats_fields_multiple(populated_cli_db):
    result = runner.invoke(app, ["stats", "--fields", "idle_top,status_distribution", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)["data"]
    assert data.get("idle_top") is not None
    assert data.get("status_distribution") is not None


def test_stats_unknown_field_exits_2(isolated_db):
    result = runner.invoke(app, ["stats", "--fields", "foo", "--json"])
    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["success"] is False
    assert "fields" in payload["error"]


def test_stats_include_retired_reflects_in_summary(populated_cli_db):
    result = runner.invoke(app, ["stats", "--include-retired", "--json"])
    data = json.loads(result.stdout)["data"]
    assert data["summary"]["include_retired"] is True
