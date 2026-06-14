import sys
from pathlib import Path

from asset_hub.config import Settings


def test_default_data_dir_source_is_data(monkeypatch):
    """源码态默认 data_dir 等价现状 Path("data")，不破坏 Agent/测试行为。"""
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.delenv("ASSET_HUB_DATA_DIR", raising=False)
    assert Settings(_env_file=None).data_dir == Path("data")


def test_env_override_still_wins(monkeypatch):
    """ASSET_HUB_DATA_DIR 显式覆盖优先于 default_factory。"""
    monkeypatch.setenv("ASSET_HUB_DATA_DIR", "/tmp/custom-asset-data")
    assert Settings(_env_file=None).data_dir == Path("/tmp/custom-asset-data")
