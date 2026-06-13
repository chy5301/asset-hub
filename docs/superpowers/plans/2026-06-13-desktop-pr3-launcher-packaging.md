# 桌面便携版 PR3 — 桌面入口 + PyInstaller 打包 + CI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增 `desktop/` 接口层（进程内 uvicorn + pywebview 原生窗口 + 启动预检），用单一 PyInstaller onedir spec 打成 Windows 便携 exe，并加 CI 构建 job。

**Architecture:** `desktop/server.py`（uvicorn 跑后台线程 + 健康轮询，可测）→ `desktop/launcher.py::main()` 编排「预检可写性 → `migrate.run_migrations()` → 起 server → 就绪后开窗」→ `desktop/window.py`（pywebview，**惰性** import）。打包入口 `packaging/desktop_entry.py`，spec 排除 `cli`、收 `frontend/dist` + `asset_hub/alembic` 数据、补 uvicorn 动态 import。

**Tech Stack:** uvicorn（进程内 `Server`）/ pywebview（可选依赖，Windows WebView2）/ PyInstaller onedir / GitHub Actions Windows runner。

**关键约束:** `pywebview` 在 `[desktop]` extra 里，后端 CI（Linux）不装它。**所有 `import webview` 必须放在函数内部惰性导入**，否则 `import asset_hub.desktop.*` 会让 Linux 上的 `uv run pytest` 崩。`server.py` / `launcher.py` / `dialogs.py` 顶层不得 import webview。

**设计依据:** spec §5 / §7.1 / §7.2 / §7.6 / §7.7 / §8 / §9。

**前置:** PR1（`runtime` / `migrate` / `config`）必须先合。**分支:** `feat/desktop-release`。

---

### Task 1: `desktop/server.py` — 进程内 uvicorn + 健康轮询

**Files:**
- Create: `src/asset_hub/desktop/__init__.py`（空）
- Create: `src/asset_hub/desktop/server.py`
- Test: `tests/unit/test_desktop_server.py`

- [ ] **Step 1: 写失败测试**

`tests/unit/test_desktop_server.py`：

```python
import urllib.request


def test_find_free_port_returns_bindable_int():
    from asset_hub.desktop.server import find_free_port

    port = find_free_port()
    assert isinstance(port, int) and 1024 < port < 65536


def test_background_server_serves_healthz():
    """真起一个后台 uvicorn，健康探测通过后访问 /api/healthz。"""
    from asset_hub.desktop.server import BackgroundServer

    srv = BackgroundServer()
    srv.start()
    try:
        assert srv.wait_until_ready(timeout=15.0) is True
        with urllib.request.urlopen(srv.url + "api/healthz", timeout=2.0) as r:
            assert r.status == 200
    finally:
        srv.stop()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/test_desktop_server.py -v`
Expected: FAIL（模块/类不存在）。

- [ ] **Step 3: 实现 `server.py`**

```python
"""进程内 uvicorn：后台线程跑 Server + /api/healthz 轮询判就绪。

不传字符串 app 路径（"asset_hub.api.app:app"），直接传 create_app() 对象——
绕开 uvicorn 字符串动态 import，让 PyInstaller 走静态图收集 routers。
"""

import socket
import threading
import time
import urllib.request

import uvicorn

from asset_hub.api.app import create_app


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class BackgroundServer:
    def __init__(self, host: str = "127.0.0.1", port: int | None = None) -> None:
        self.host = host
        self.port = port or find_free_port()
        config = uvicorn.Config(
            create_app(), host=self.host, port=self.port,
            log_level="warning", reload=False, workers=1,
        )
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(target=self._server.run, daemon=True)

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}/"

    def start(self) -> None:
        self._thread.start()

    def wait_until_ready(self, timeout: float = 15.0) -> bool:
        deadline = time.monotonic() + timeout
        health = f"http://{self.host}:{self.port}/api/healthz"
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(health, timeout=1.0) as r:
                    if r.status == 200:
                        return True
            except OSError:
                time.sleep(0.2)
        return False

    def stop(self) -> None:
        self._server.should_exit = True
```

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run pytest tests/unit/test_desktop_server.py -v`
Expected: PASS（2 passed）。

- [ ] **Step 5: 提交**

```bash
git add src/asset_hub/desktop/__init__.py src/asset_hub/desktop/server.py tests/unit/test_desktop_server.py
git commit -m "feat(desktop): 进程内 uvicorn BackgroundServer + 健康轮询"
```

---

### Task 2: `desktop/dialogs.py` + `desktop/window.py`（惰性 import webview）

**Files:**
- Create: `src/asset_hub/desktop/dialogs.py`
- Create: `src/asset_hub/desktop/window.py`
- Test: `tests/unit/test_desktop_window.py`

- [ ] **Step 1: 写失败测试**

`tests/unit/test_desktop_window.py`（不依赖 pywebview/WebView2，只验消息常量与惰性导入约定）：

```python
import importlib


def test_window_module_imports_without_pywebview():
    """window.py 顶层不得 import webview，否则 Linux 后端 CI 崩。"""
    mod = importlib.import_module("asset_hub.desktop.window")
    assert hasattr(mod, "open_window")
    assert isinstance(mod.WEBVIEW2_HELP, str) and "WebView2" in mod.WEBVIEW2_HELP


def test_dialogs_error_box_callable():
    from asset_hub.desktop import dialogs

    assert callable(dialogs.error_box)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/test_desktop_window.py -v`
Expected: FAIL（模块不存在）。

- [ ] **Step 3: 实现 `dialogs.py` 与 `window.py`**

`dialogs.py`（Windows 原生消息框，非 Windows 退化为 stderr 打印；ctypes 在 stdlib，顶层 import 安全）：

```python
"""原生错误提示框（无需 GUI 框架）。Windows 用 MessageBoxW；其他平台打印到 stderr。"""

import sys


def error_box(title: str, text: str) -> None:
    if sys.platform == "win32":
        import ctypes  # 惰性，避免非 win 平台告警

        ctypes.windll.user32.MessageBoxW(0, text, title, 0x10)  # MB_ICONERROR
    else:
        print(f"[{title}] {text}", file=sys.stderr)
```

`window.py`（**webview 惰性 import**）：

```python
"""pywebview 原生窗口。webview 仅在 open_window 内惰性 import——
它是 [desktop] 可选依赖，后端 CI 不装；顶层 import 会让 Linux pytest 崩。"""

WEBVIEW2_HELP = (
    "asset-hub 需要 Microsoft Edge WebView2 Runtime 才能显示界面。\n"
    "请从 https://developer.microsoft.com/microsoft-edge/webview2/ 安装后重新运行。"
)


def open_window(title: str, url: str) -> None:
    import webview  # 惰性导入

    webview.create_window(title, url)
    webview.start()
```

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run pytest tests/unit/test_desktop_window.py -v`
Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add src/asset_hub/desktop/dialogs.py src/asset_hub/desktop/window.py tests/unit/test_desktop_window.py
git commit -m "feat(desktop): 原生错误框 dialogs + pywebview window（惰性 import）"
```

---

### Task 3: `desktop/launcher.py` — main() 编排 + 预检

**Files:**
- Create: `src/asset_hub/desktop/launcher.py`
- Test: `tests/unit/test_desktop_launcher.py`

- [ ] **Step 1: 写失败测试**

`tests/unit/test_desktop_launcher.py`（验预检 abort 路径，不真起 server/窗口）：

```python
def test_main_aborts_when_data_dir_not_writable(monkeypatch):
    from asset_hub.desktop import launcher

    calls = {}
    monkeypatch.setattr(launcher.runtime, "is_writable_dir", lambda p: False)
    monkeypatch.setattr(
        launcher.dialogs, "error_box",
        lambda title, text: calls.__setitem__("box", (title, text)),
    )
    monkeypatch.setattr(
        launcher.migrate, "run_migrations",
        lambda: calls.__setitem__("migrate", True),
    )

    rc = launcher.main()

    assert rc == 1
    assert "box" in calls  # 弹了提示
    assert "migrate" not in calls  # 没往下走到迁移/起服务


def test_main_aborts_when_migration_fails(monkeypatch):
    from asset_hub.desktop import launcher

    calls = {}
    monkeypatch.setattr(launcher.runtime, "is_writable_dir", lambda p: True)
    def _boom():
        raise RuntimeError("migration broke")
    monkeypatch.setattr(launcher.migrate, "run_migrations", _boom)
    monkeypatch.setattr(
        launcher.dialogs, "error_box",
        lambda title, text: calls.__setitem__("box", (title, text)),
    )
    # 确保不会真去起 server
    monkeypatch.setattr(
        launcher, "BackgroundServer",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("不应起 server")),
    )

    rc = launcher.main()
    assert rc == 1
    assert "migration broke" in calls["box"][1]
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/test_desktop_launcher.py -v`
Expected: FAIL（launcher 不存在）。

- [ ] **Step 3: 实现 `launcher.py`**

```python
"""桌面入口编排：预检可写性 → 迁移 → 起 server → 就绪后开窗。

与 cli/serve 完全独立，不复用 subprocess/PID/detach 那套。
"""

import sys
from pathlib import Path

from asset_hub import migrate, runtime
from asset_hub.config import Settings
from asset_hub.desktop import dialogs, window
from asset_hub.desktop.server import BackgroundServer

_TITLE = "asset-hub"


def _load_settings() -> Settings:
    """frozen 下按 exe 同级解析 .env（pydantic 默认按 cwd 找，双击 exe 不可控）。"""
    if runtime.is_frozen():
        env_file = Path(sys.executable).resolve().parent / ".env"
        return Settings(_env_file=str(env_file) if env_file.exists() else None)
    return Settings()


def main() -> int:
    settings = _load_settings()

    # 预检 1：可写性（不可写不自动搬家，提示用户移动文件夹）
    if not runtime.is_writable_dir(settings.data_dir):
        dialogs.error_box(
            _TITLE,
            f"当前位置不可写：{settings.data_dir}\n\n"
            "请把整个 asset-hub 文件夹移动到文档/桌面等你有权限的位置后重新运行。\n"
            "（高级用户可在 exe 同级 .env 设 ASSET_HUB_DATA_DIR 指定别处。）",
        )
        return 1

    # 迁移：编程式 upgrade head
    try:
        migrate.run_migrations()
    except Exception as e:  # noqa: BLE001 — 顶层兜底，任何迁移异常都要弹框而非裸崩
        dialogs.error_box(_TITLE + " 迁移失败", f"数据库升级失败：\n{e}")
        return 1

    # 起服务
    server = BackgroundServer()
    server.start()
    if not server.wait_until_ready():
        dialogs.error_box(_TITLE, "后端启动超时，请重试或查看是否被防火墙拦截。")
        server.stop()
        return 1

    # 就绪后再开窗（避免首帧连接被拒）
    try:
        window.open_window(_TITLE, server.url)
    except Exception:  # noqa: BLE001 — pywebview/WebView2 缺失兜底
        dialogs.error_box(_TITLE, window.WEBVIEW2_HELP)
        return 1
    finally:
        server.stop()
    return 0
```

- [ ] **Step 4: 跑测试确认通过 + 全量回归**

Run: `uv run pytest tests/unit/test_desktop_launcher.py -v && uv run pytest -q`
Expected: 新测试 PASS；**全量 pytest 在本机全绿**（确认 desktop 包的惰性 import 约定没破坏后端测试）。

- [ ] **Step 5: 提交**

```bash
git add src/asset_hub/desktop/launcher.py tests/unit/test_desktop_launcher.py
git commit -m "feat(desktop): launcher.main() 编排预检/迁移/起服务/开窗"
```

---

### Task 4: 打包入口 + `pyproject` desktop extra

**Files:**
- Create: `packaging/desktop_entry.py`
- Modify: `pyproject.toml`（加 optional-dependencies）

- [ ] **Step 1: 写打包入口脚本**

`packaging/desktop_entry.py`（PyInstaller 分析的入口；`freeze_support` 防 frozen 下 spawn 子进程递归起进程）：

```python
"""PyInstaller 入口：桌面便携版。"""

import multiprocessing
import sys

from asset_hub.desktop.launcher import main

if __name__ == "__main__":
    multiprocessing.freeze_support()
    sys.exit(main())
```

- [ ] **Step 2: 加 desktop extra**

在 `pyproject.toml` 的 `[project]` 后追加：

```toml
[project.optional-dependencies]
desktop = ["pywebview>=5"]
```

- [ ] **Step 3: 同步依赖 + 确认可装**

Run: `uv sync --extra desktop`
Expected: 装上 pywebview，无冲突。

- [ ] **Step 4: 确认源码态可直接跑桌面入口（手验，需 WebView2）**

Run: `uv run python packaging/desktop_entry.py`
Expected: 打开 asset-hub 窗口（源码态 data_root=`./data`）。关窗即退。若环境无 WebView2 则弹安装提示——也算预期路径验证通过。

- [ ] **Step 5: 提交**

```bash
git add packaging/desktop_entry.py pyproject.toml uv.lock
git commit -m "build(desktop): PyInstaller 入口脚本 + pywebview 可选依赖组"
```

---

### Task 5: PyInstaller spec（onedir，排除 cli）

**Files:**
- Create: `packaging/asset_hub.spec`

- [ ] **Step 1: 写 spec**

`packaging/asset_hub.spec`：

```python
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
    # uvicorn auto 选择层（懒 try-import，静态图抓不到）；Windows 不打 uvloop/watchfiles
    "uvicorn.loops.asyncio",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.http.httptools_impl",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.protocols.websockets.wsproto_impl",
    "uvicorn.lifespan.on",
    "uvicorn.lifespan.off",
    # 迁移/方言
    "alembic.ddl.sqlite",
    "sqlalchemy.dialects.sqlite",
]
hiddenimports += collect_submodules("asset_hub.alembic.versions")  # 运行时按目录加载

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
```

> 若 `pydantic_core` 的 `.pyd` 未被自动收齐，构建后冒烟报 `ModuleNotFoundError: pydantic_core._pydantic_core`，则在命令行加 `--collect-all pydantic`（或 spec 里 `datas += collect_data_files("pydantic_core")` + `hiddenimports += collect_submodules("pydantic")`）。openpyxl 同理，导出报缺资源时加 `collect_data_files("openpyxl")`。

- [ ] **Step 2: 构建前先 build 前端**

Run: `pnpm --dir frontend build`
Expected: `frontend/dist/index.html` 存在。

- [ ] **Step 3: 跑 PyInstaller（onedir）**

Run: `uv run --extra desktop pyinstaller packaging/asset_hub.spec --noconfirm`
Expected: 产出 `dist/asset-hub/asset-hub.exe`，无致命错误。

- [ ] **Step 4: 干净机冒烟（手验，关键）**

把 `dist/asset-hub/` 整个拷到一台**无 Python/Node** 的 Windows 机器（或干净用户环境），双击 `asset-hub.exe`：
- 开窗 → 浏览到资产列表
- 新建一个 asset（验 pydantic + sqlalchemy + sqlite 链路）
- 导出 xlsx（验 openpyxl 数据文件被收）
- 关窗重开 → 数据仍在（验 exe 同级 `./data` 持久）
- 撤销上一次流转按钮可用（验 PR2 + API 静态收集）
- 把含旧版本 DB 的 `data/` 放进去重开 → 自动 `upgrade head`（验编程式迁移 + batch_alter）

任一失败按 Step 1 注释补 `--collect-*` / `hiddenimports` 后重建。

- [ ] **Step 5: 提交 spec（不提交 build 产物）**

```bash
echo "/dist/" >> .gitignore; echo "/build/" >> .gitignore
git add packaging/asset_hub.spec .gitignore
git commit -m "build(desktop): PyInstaller onedir spec（排除 cli，收 dist+alembic）"
```

---

### Task 6: CI — Windows 构建 job

**Files:**
- Create: `.github/workflows/release-desktop.yml`

- [ ] **Step 1: 写 workflow**

`.github/workflows/release-desktop.yml`：

```yaml
name: release-desktop

on:
  workflow_dispatch:
  push:
    tags: ["v*"]

jobs:
  build-windows:
    runs-on: windows-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@v4

      - name: Setup uv
        uses: astral-sh/setup-uv@v5

      - name: Setup Node + pnpm
        uses: pnpm/action-setup@v4
        with:
          version: 9
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: pnpm
          cache-dependency-path: frontend/pnpm-lock.yaml

      - name: Build frontend
        run: |
          pnpm --dir frontend install --frozen-lockfile
          pnpm --dir frontend build

      - name: Install python deps (with desktop extra)
        run: uv sync --extra desktop

      - name: PyInstaller build
        run: uv run pyinstaller packaging/asset_hub.spec --noconfirm

      - name: Zip onedir
        run: Compress-Archive -Path dist/asset-hub/* -DestinationPath asset-hub-desktop-win64.zip

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: asset-hub-desktop-win64
          path: asset-hub-desktop-win64.zip
```

- [ ] **Step 2: 校验 YAML + 触发一次**

Run（本地校验缩进）: `uv run --with pyyaml python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/release-desktop.yml')); print('ok')"`
Expected: `ok`。
推分支后在 GitHub Actions 手动 `workflow_dispatch` 跑一次，确认产出 `asset-hub-desktop-win64.zip` artifact。

- [ ] **Step 3: 提交**

```bash
git add .github/workflows/release-desktop.yml
git commit -m "ci(desktop): Windows runner 构建 onedir + zip artifact"
```

---

### Task 7: 文档同步 + 版本号

**Files:**
- Modify: `references/deploy.md` / `SKILL.md` / `CLAUDE.md` / `README.md` / `pyproject.toml`

- [ ] **Step 1: `references/deploy.md` 加桌面版段**

新增"桌面便携版（人类 GUI）"小节，覆盖：构建（`pnpm build` → `pyinstaller packaging/asset_hub.spec`）、数据落点（exe 同级 `./data`；只读位置弹框提示移动；`.env` 设 `ASSET_HUB_DATA_DIR` 逃生口）、升级（替换整个文件夹但保留 `data/`，首启自动 `upgrade head`）、WebView2 前置。

- [ ] **Step 2: `SKILL.md` / `CLAUDE.md` 注记**

- `SKILL.md` 部署小节加一句：人类用户可用桌面便携版（双击 exe），Agent 仍用源码 + `uv run asset-hub` / `serve`，互不影响。
- `CLAUDE.md` "开发命令"加桌面版构建：`uv sync --extra desktop` + `pnpm --dir frontend build` + `uv run pyinstaller packaging/asset_hub.spec`；"目录"提及 `desktop/` 为第三接口层、`packaging/` 放 spec。

- [ ] **Step 3: `README.md` 加下载/使用说明**

面向人类用户：从 Release 下载 `asset-hub-desktop-win64.zip` → 解压到可写目录 → 双击 `asset-hub.exe`。

- [ ] **Step 4: 版本号**

按 [[feedback_versioning]] 保守策略（作者拍板）：新增发布形态属 feature，建议 `pyproject.toml` version `2.3.1 → 2.4.0`。由作者确认后改。

- [ ] **Step 5: 提交**

```bash
git add references/deploy.md SKILL.md CLAUDE.md README.md pyproject.toml
git commit -m "docs(desktop): 部署/SKILL/CLAUDE/README 同步桌面便携版 + 版本号"
```

---

## Self-Review（PR3）

- **Spec 覆盖**：§5 流程 → Task 1+3；§7.7 预检 → Task 2（dialogs/window）+ Task 3（launcher 预检）；§7.2 `.env` exe 同级 → Task 3 `_load_settings`；§7.6 extra → Task 4；§8 打包/excludes/hiddenimports/datas → Task 5；§9 数据生命周期 → Task 5 Step 4 冒烟；CI → Task 6；文档 → Task 7。
- **关键约束落实**：webview 惰性 import（Task 2 window.py + 测试 `test_window_module_imports_without_pywebview`），保证 Linux 后端 CI 不崩；Task 3/Task 4 全量 pytest 复核。
- **类型/命名一致**：`BackgroundServer`（server.py）→ launcher import 同名；`runtime.is_writable_dir` / `runtime.is_frozen` / `migrate.run_migrations`（PR1 定义）在 launcher 一致引用；`window.open_window` / `window.WEBVIEW2_HELP` / `dialogs.error_box` 命名贯穿测试与实现。
- **无占位符**：spec/CI/launcher 均为可直接落地的完整内容；可能的 `--collect-all` 补丁以"冒烟失败时"的明确条件给出，非泛化占位。
- **打包选择机制**：入口 `desktop_entry.py` → 静态图不含 cli + `excludes=['asset_hub.cli']` 双保险；uvicorn 动态层用 hiddenimports；alembic versions 用 `collect_submodules` + datas 目录双收（脚本既被 import 校验也作运行时目录加载）。
