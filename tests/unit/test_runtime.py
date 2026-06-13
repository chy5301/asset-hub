import sys
from pathlib import Path

import asset_hub.runtime as rt


def test_is_frozen_false_in_source(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert rt.is_frozen() is False


def test_is_frozen_true_when_sys_frozen_set(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    assert rt.is_frozen() is True


def test_resource_root_source_is_repo_root(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    expected = Path(rt.__file__).resolve().parents[2]
    assert rt.resource_root() == expected


def test_resource_root_frozen_is_meipass(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert rt.resource_root() == tmp_path


def test_resource_path_joins(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert (
        rt.resource_path("frontend", "dist") == rt.resource_root() / "frontend" / "dist"
    )


def test_data_root_source_is_cwd_data(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert rt.data_root() == Path("data")


def test_data_root_frozen_is_exe_adjacent(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(
        sys, "executable", str(tmp_path / "asset-hub.exe"), raising=False
    )
    assert rt.data_root() == tmp_path / "data"


def test_is_writable_dir_true_for_tmp(tmp_path):
    assert rt.is_writable_dir(tmp_path) is True


def test_is_writable_dir_false_for_nonexistent_uncreatable(tmp_path, monkeypatch):
    target = tmp_path / "a-file"
    target.write_text("x")
    assert rt.is_writable_dir(target / "sub") is False
