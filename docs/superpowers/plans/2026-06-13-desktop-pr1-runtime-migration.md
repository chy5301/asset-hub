# 桌面便携版 PR1 — 路径解耦 + 运行时迁移地基 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为桌面便携版打地基——引入 frozen 感知的路径解析（`runtime.py`）与编程式数据库迁移（`migrate.py`），让 `config`/`api.app` 不再依赖 cwd 相对路径；本 PR 全部在源码态完成，不引入打包，行为对 Agent/`serve` 零回归。

**Architecture:** 新增包根模块 `asset_hub/runtime.py`（`is_frozen` / `resource_root` / `resource_path` / `data_root` / `is_writable_dir`）与 `asset_hub/migrate.py`（`run_migrations()`）。`config.Settings.data_dir` 默认改走 `runtime.data_root`；`api/app.py` 的前端 dist 路径改走 `runtime.resource_path`。所有改动在源码态等价于现状（`resource_root()`=仓库根、`data_root()`=`Path("data")`），故无回归。

**Tech Stack:** Python 3.12 / pydantic-settings / SQLAlchemy 2.x + Alembic / pytest（真实 SQLite tmp_path）。所有命令走 `uv`。

**设计依据:** `docs/superpowers/specs/2026-06-13-desktop-release-design.md` §7.1 / §7.2 / §7.3 / §7.4 / §10。

**分支:** `feat/desktop-release`。

---

### Task 1: `runtime.py` — frozen 检测 + 路径解析

**Files:**
- Create: `src/asset_hub/runtime.py`
- Test: `tests/unit/test_runtime.py`

- [ ] **Step 1: 写失败测试**

`tests/unit/test_runtime.py`：

```python
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
    # runtime.py 在 src/asset_hub/ 下，仓库根 = parents[2]
    expected = Path(rt.__file__).resolve().parents[2]
    assert rt.resource_root() == expected


def test_resource_root_frozen_is_meipass(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert rt.resource_root() == tmp_path


def test_resource_path_joins(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert rt.resource_path("frontend", "dist") == rt.resource_root() / "frontend" / "dist"


def test_data_root_source_is_cwd_data(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert rt.data_root() == Path("data")


def test_data_root_frozen_is_exe_adjacent(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "asset-hub.exe"), raising=False)
    assert rt.data_root() == tmp_path / "data"


def test_is_writable_dir_true_for_tmp(tmp_path):
    assert rt.is_writable_dir(tmp_path) is True


def test_is_writable_dir_false_for_nonexistent_uncreatable(tmp_path, monkeypatch):
    # 指向一个父目录不存在且无法创建的路径
    target = tmp_path / "a-file"
    target.write_text("x")  # 占成文件，子路径无法 mkdir
    assert rt.is_writable_dir(target / "sub") is False
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/test_runtime.py -v`
Expected: FAIL（`ModuleNotFoundError: asset_hub.runtime` 或 `AttributeError`）。

- [ ] **Step 3: 实现 `runtime.py`**

```python
"""Frozen（PyInstaller）感知的路径解析。

两类资源分开处理：
- 只读资源（frontend/dist 等包外资源）：resource_root() = _MEIPASS（frozen）/ 仓库根（源码）
- 可写数据（DB/附件/日志）：data_root() = exe 同级 ./data（frozen）/ cwd 下 ./data（源码）
包内资源（如 alembic）不走这里，按包目录 `Path(asset_hub.__file__).parent` 解析（见 migrate.py）。
"""

import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def resource_root() -> Path:
    """只读资源根。frozen → sys._MEIPASS（onedir/onefile 均设置）；源码 → 仓库根。"""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parents[2]


def resource_path(*parts: str) -> Path:
    return resource_root().joinpath(*parts)


def data_root() -> Path:
    """可写数据根。frozen → exe 同级 ./data；源码 → cwd 下 ./data（等价现状 Path("data")）。

    无自动回退——exe 同级不可写时由启动预检（PR3）弹框提示用户移动文件夹。
    """
    if is_frozen():
        return Path(sys.executable).resolve().parent / "data"
    return Path("data")


def is_writable_dir(path: Path) -> bool:
    """目标目录能否创建并写入：mkdir(parents=True) 后 touch 测试文件再删。best-effort。"""
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write-test"
        probe.touch()
        probe.unlink()
        return True
    except OSError:
        return False
```

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run pytest tests/unit/test_runtime.py -v`
Expected: PASS（9 passed）。

- [ ] **Step 5: 提交**

```bash
git add src/asset_hub/runtime.py tests/unit/test_runtime.py
git commit -m "feat(runtime): 新增 frozen 感知路径解析 runtime.py"
```

---

### Task 2: `config.Settings.data_dir` 走 `runtime.data_root`

**Files:**
- Modify: `src/asset_hub/config.py:15`
- Test: `tests/unit/test_config_data_dir.py`

- [ ] **Step 1: 写失败测试**

`tests/unit/test_config_data_dir.py`：

```python
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
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/unit/test_config_data_dir.py -v`
Expected: 第一个可能已 PASS（巧合相等），第二个 PASS（现有行为）；**但**改动目的是把字面量换成 factory——若当前 `data_dir = Path("data")` 已让两测试 PASS，本任务为防回归。先确认现状全 PASS 再做 Step 3，改完仍须 PASS。

- [ ] **Step 3: 改 `config.py`**

把 `src/asset_hub/config.py` 顶部加 import 并改字段默认：

```python
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from asset_hub import runtime


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ASSET_HUB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    data_dir: Path = Field(default_factory=runtime.data_root)
    backend_port: int = 8000
    frontend_port: int = 5173
    backend_host: str | None = None
```

（其余 `db_url` / `attachments_dir` / `pids_dir` / `logs_dir` / `resolve_backend_host` 不变。）

- [ ] **Step 4: 跑测试确认通过 + 全量回归**

Run: `uv run pytest tests/unit/test_config_data_dir.py -v && uv run pytest -q`
Expected: 新测试 PASS；**全量 pytest 全绿**（确认 Settings 改动不破坏 cli/api/migration 各层）。

- [ ] **Step 5: 提交**

```bash
git add src/asset_hub/config.py tests/unit/test_config_data_dir.py
git commit -m "refactor(config): data_dir 默认走 runtime.data_root（源码态行为不变）"
```

---

### Task 3: `api/app.py` 前端 dist 路径走 `runtime` + frozen 感知

**Files:**
- Modify: `src/asset_hub/api/app.py:1-30,89-94`
- Test: `tests/api/test_spa_mount.py`

- [ ] **Step 1: 写失败测试**

`tests/api/test_spa_mount.py`：

```python
import asset_hub.api.app as app_mod
import asset_hub.runtime as rt


def test_frontend_dist_is_absolute_from_resource_root():
    """_FRONTEND_DIST 应是基于 resource_root 的绝对路径，而非相对 cwd 的 Path('frontend/dist')。"""
    assert app_mod._FRONTEND_DIST == rt.resource_path("frontend", "dist")
    assert app_mod._FRONTEND_DIST.is_absolute()


def test_frozen_ignores_dev_mode(monkeypatch):
    """frozen 时即使 ASSET_HUB_MODE=dev，也不应被判为 dev（应挂 SPA）。"""
    monkeypatch.setattr(rt, "is_frozen", lambda: True)
    monkeypatch.setenv("ASSET_HUB_MODE", "dev")
    assert app_mod._compute_is_dev_mode() is False


def test_source_dev_mode_respected(monkeypatch):
    monkeypatch.setattr(rt, "is_frozen", lambda: False)
    monkeypatch.setenv("ASSET_HUB_MODE", "dev")
    assert app_mod._compute_is_dev_mode() is True
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/api/test_spa_mount.py -v`
Expected: FAIL（`_FRONTEND_DIST` 仍是相对路径；`_compute_is_dev_mode` 未定义）。

- [ ] **Step 3: 改 `api/app.py`**

顶部 import 加 `from asset_hub import runtime`；把 `_FRONTEND_DIST` 改为绝对路径；抽出 `_compute_is_dev_mode()` 并在 `create_app` 内调用：

```python
# 顶部
from asset_hub import runtime

# 原 _FRONTEND_DIST = Path("frontend/dist") 改为：
_FRONTEND_DIST = runtime.resource_path("frontend", "dist")


def _compute_is_dev_mode() -> bool:
    """frozen 永远 prod-like 自托管，无条件挂 SPA、忽略 ASSET_HUB_MODE=dev。"""
    if runtime.is_frozen():
        return False
    return os.environ.get("ASSET_HUB_MODE") == "dev"
```

在 `create_app()` 内，把原来的：

```python
_is_dev_mode = os.environ.get("ASSET_HUB_MODE") == "dev"
if (
    not _is_dev_mode
    and _FRONTEND_DIST.is_dir()
    and (_FRONTEND_DIST / "index.html").exists()
):
    ...
```

改为：

```python
import logging
_log = logging.getLogger(__name__)

_is_dev_mode = _compute_is_dev_mode()
if not _is_dev_mode:
    if _FRONTEND_DIST.is_dir() and (_FRONTEND_DIST / "index.html").exists():
        ...  # 原挂载逻辑保持不变
    else:
        _log.warning("frontend dist 不存在，跳过 SPA 挂载: %s", _FRONTEND_DIST)
```

（原 SPA 挂载主体逻辑 app.py:95-127 保持不变，只是被包进上面的 if 分支并补 else 的 warning。）

- [ ] **Step 4: 跑测试确认通过 + 回归**

Run: `uv run pytest tests/api/test_spa_mount.py tests/api -q`
Expected: 新测试 PASS；`tests/api` 全绿。

- [ ] **Step 5: 提交**

```bash
git add src/asset_hub/api/app.py tests/api/test_spa_mount.py
git commit -m "refactor(api): 前端 dist 走 runtime.resource_path + frozen 感知挂载"
```

---

### Task 4: `migrate.py` — 编程式 `alembic upgrade head`

**Files:**
- Create: `src/asset_hub/migrate.py`
- Test: `tests/migration/test_run_migrations.py`

- [ ] **Step 1: 写失败测试**

`tests/migration/test_run_migrations.py`（沿用 `test_v4_asset_brand_column.py` 的 mock Settings + `_clear_env_cache` 范式）：

```python
"""migrate.run_migrations() 编程式 upgrade head：把旧版本库升到 head。"""

import sys
from unittest.mock import MagicMock, patch

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def _clear_env_cache():
    for key in list(sys.modules.keys()):
        if "asset_hub.alembic" in key or key.endswith(".env"):
            del sys.modules[key]


@pytest.fixture
def v3_db(tmp_path):
    """临时库先 upgrade 到 v3 head（2d589d84e584），模拟"旧版本数据库"。"""
    db_path = tmp_path / "asset_hub.db"
    db_url = f"sqlite:///{db_path}"
    mock_settings = MagicMock()
    mock_settings.db_url = db_url

    cfg = Config("alembic.ini")
    cfg.set_main_option("script_location", "src/asset_hub/alembic")
    cfg.set_main_option("sqlalchemy.url", db_url)

    _clear_env_cache()
    with patch("asset_hub.config.Settings", return_value=mock_settings):
        command.upgrade(cfg, "2d589d84e584")
    return db_path, db_url, mock_settings


def test_run_migrations_upgrades_old_db_to_head(v3_db):
    from asset_hub import migrate

    db_path, db_url, mock_settings = v3_db
    engine = create_engine(db_url)
    cols_before = {c["name"] for c in inspect(engine).get_columns("assets")}
    assert "brand" not in cols_before  # v3 尚无 v4 的 brand 列

    _clear_env_cache()
    with patch("asset_hub.config.Settings", return_value=mock_settings):
        migrate.run_migrations()

    engine = create_engine(db_url)
    cols_after = {c["name"] for c in inspect(engine).get_columns("assets")}
    assert "brand" in cols_after  # run_migrations 已把库升到含 v4 的 head


def test_run_migrations_idempotent_on_head(v3_db):
    """已在 head 再跑一次不报错（no-op）。"""
    from asset_hub import migrate

    _, _, mock_settings = v3_db
    _clear_env_cache()
    with patch("asset_hub.config.Settings", return_value=mock_settings):
        migrate.run_migrations()
        migrate.run_migrations()  # 第二次 no-op，不抛
```

> 注：测试里 `run_migrations()` 内部用 `Path(asset_hub.__file__).parent / "alembic"` 解析脚本目录（源码态 = `src/asset_hub/alembic`），与 fixture 的 `script_location` 等价。

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/migration/test_run_migrations.py -v`
Expected: FAIL（`asset_hub.migrate` 不存在）。

- [ ] **Step 3: 实现 `migrate.py`**

```python
"""启动时编程式数据库迁移（替代 frozen 环境下不可用的 `uv run alembic`）。"""

from pathlib import Path

from alembic import command
from alembic.config import Config

import asset_hub
from asset_hub.config import Settings


def _alembic_dir() -> Path:
    """alembic 脚本目录。包内资源：源码态 src/asset_hub/alembic、frozen 态 _MEIPASS/asset_hub/alembic，
    两者都等于"包目录 / alembic"。"""
    return Path(asset_hub.__file__).resolve().parent / "alembic"


def run_migrations() -> None:
    """把当前 DB 升到 head。不读相对 alembic.ini；script_location 按包目录解析，
    sqlalchemy.url 取 Settings().db_url（env.py 内会再次 Settings() 覆盖，一致）。"""
    cfg = Config()
    cfg.set_main_option("script_location", str(_alembic_dir()))
    cfg.set_main_option("sqlalchemy.url", Settings().db_url)
    command.upgrade(cfg, "head")
```

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run pytest tests/migration/test_run_migrations.py -v`
Expected: PASS（2 passed）。

- [ ] **Step 5: 提交**

```bash
git add src/asset_hub/migrate.py tests/migration/test_run_migrations.py
git commit -m "feat(migrate): 新增编程式 run_migrations() 升级到 head"
```

---

### Task 5: PR1 收尾 — 全量 gate + lint

**Files:** 无新增（验证 + 修格式）

- [ ] **Step 1: 跑后端 CI gate**

Run: `uv run ruff check . && uv run ruff format --check . && uv run pytest -q`
Expected: 全绿。若 `ruff format --check` 报需格式化，跑 `uv run ruff format .` 后重跑。

- [ ] **Step 2: 确认 serve 源码态零回归（手验）**

Run: `uv run asset-hub serve doctor --json`（不需真启动，doctor 体检即可）
Expected: envelope `success=true`，无因路径改动产生的新错误。

- [ ] **Step 3: 提交（若有 format 改动）**

```bash
git add -A && git commit -m "style: PR1 ruff format" || echo "无需格式化"
```

---

## Self-Review（PR1）

- **Spec 覆盖**：§7.1 runtime（Task 1）、§7.2 config（Task 2）、§7.4 app.py（Task 3）、§7.3 migrate（Task 4）。`.env` exe 同级解析属 PR3 launcher 范畴（PR1 不引入 frozen 入口，故不在此）。
- **类型一致性**：`runtime.data_root` / `runtime.resource_path` / `runtime.is_frozen` / `runtime.is_writable_dir` / `migrate.run_migrations` 命名贯穿一致。
- **无占位符**：所有步骤含真实代码与命令。
- **回归保护**：Task 2/3/5 均含全量 pytest，确保对 Agent/`serve` 零回归。
