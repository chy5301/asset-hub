# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules, copy_metadata

ROOT = Path(SPECPATH).resolve().parent  # packaging/ 的上一级 = 仓库根

datas = [
    (str(ROOT / "frontend" / "dist"), "frontend/dist"),
    (str(ROOT / "src" / "asset_hub" / "alembic"), "asset_hub/alembic"),
]
datas += copy_metadata("asset-hub")  # app.py 用 importlib.metadata.version("asset-hub")

hiddenimports = [
    # uvicorn auto 选择层（懒 try-import，静态图抓不到）；Windows 不打 uvloop/watchfiles。
    # 不列 wsproto_impl：本项目无 WS 路由且未必装 wsproto，列了只多一条构建告警。
    "uvicorn.loops.asyncio",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.http.httptools_impl",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.lifespan.on",
    "uvicorn.lifespan.off",
    # 迁移/方言
    "alembic.ddl.sqlite",
    "sqlalchemy.dialects.sqlite",
]
hiddenimports += collect_submodules("asset_hub.alembic.versions")  # 运行时按目录加载
# pywebview 在 window.open_window 内惰性 import（避免 Linux CI 崩）：PyInstaller 字节码扫描
# 通常能抓到函数内 import，但显式收集 webview + 其平台后端子模块更稳，避免漏 winforms 等。
hiddenimports += collect_submodules("webview")

a = Analysis(
    [str(ROOT / "packaging" / "desktop_entry.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["asset_hub.cli"],  # 桌面版不含 CLI
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="asset-hub",
    console=False,  # 无黑窗（GUI app）
    icon=None,
)
coll = COLLECT(
    exe, a.binaries, a.datas,
    name="asset-hub",  # onedir 输出目录 dist/asset-hub/
)
