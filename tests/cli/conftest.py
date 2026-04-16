import pytest

import asset_hub.db as db_mod


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSET_HUB_DATA_DIR", str(tmp_path))
    db_mod.reset_engine()
    yield tmp_path
    db_mod.reset_engine()
