"""launcher.main() 预检路径测试：mock 掉 server/window，只验证 abort 逻辑。"""

import os
from pathlib import Path

from asset_hub.desktop import launcher


def test_main_aborts_when_data_dir_not_writable(monkeypatch):
    """不可写 → 弹 error_box + return 1，不走迁移。"""
    calls: dict = {}
    monkeypatch.setattr(launcher.runtime, "is_writable_dir", lambda p: False)
    monkeypatch.setattr(
        launcher.dialogs,
        "error_box",
        lambda title, text: calls.__setitem__("box", (title, text)),
    )
    monkeypatch.setattr(
        launcher.migrate,
        "run_migrations",
        lambda: calls.__setitem__("migrate", True),
    )

    rc = launcher.main()

    assert rc == 1
    assert "box" in calls  # 弹了提示
    assert "migrate" not in calls  # 没往下走到迁移/起服务


def test_main_aborts_when_migration_fails(monkeypatch):
    """迁移异常 → 弹 error_box（含异常信息） + return 1，不起 server。"""
    calls: dict = {}
    monkeypatch.setattr(launcher.runtime, "is_writable_dir", lambda p: True)

    def _boom():
        raise RuntimeError("migration broke")

    monkeypatch.setattr(launcher.migrate, "run_migrations", _boom)
    monkeypatch.setattr(
        launcher.dialogs,
        "error_box",
        lambda title, text: calls.__setitem__("box", (title, text)),
    )
    # 确保不会真去起 server
    monkeypatch.setattr(
        launcher,
        "BackgroundServer",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("不应起 server")),
    )

    rc = launcher.main()
    assert rc == 1
    assert "migration broke" in calls["box"][1]


def test_bootstrap_settings_frozen_propagates_env_to_bare_settings(monkeypatch, tmp_path):
    """frozen + exe 同级 .env 设 ASSET_HUB_DATA_DIR → 写回 os.environ，
    后续裸 Settings() 跟随（修 split-brain：预检与真实落点一致）。"""
    from asset_hub.config import Settings

    custom = tmp_path / "portable-data"
    exe = tmp_path / "asset-hub.exe"
    exe.write_text("")
    (tmp_path / ".env").write_text(f"ASSET_HUB_DATA_DIR={custom}\n")

    monkeypatch.setattr(launcher.runtime, "is_frozen", lambda: True)
    monkeypatch.setattr(launcher.sys, "executable", str(exe))
    monkeypatch.delenv("ASSET_HUB_DATA_DIR", raising=False)

    s = launcher._bootstrap_settings()

    assert s.data_dir == custom
    assert os.environ["ASSET_HUB_DATA_DIR"] == str(custom)
    assert Settings().data_dir == custom  # 后续裸 Settings() 跟随同一落点
