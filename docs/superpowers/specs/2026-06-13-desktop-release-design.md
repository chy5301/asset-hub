# 桌面便携版（人类 GUI 发布形态）设计

> 在现有项目上**纯新增**一种面向人类用户的发布形态：Windows 便携桌面 app —— pywebview 原生窗口 + 进程内 FastAPI，双击即用、数据随文件夹搬迁。Agent 侧（源码 + `uv run asset-hub` + SKILL.md）**完全不动**。
>
> 前置评估见本次会话的 dynamic workflow（exe 打包可行性，6 维度 + skeptic 复核，结论"有条件可行"）；undo 缺口的历史决策见 [`2026-05-20-issue24-asset-undo-design.md`](2026-05-20-issue24-asset-undo-design.md)。

## 1. 背景与动机

项目定位是"单一人类用户（作者本人）+ 其 Claude Code Agent"。当前两类使用者的入口：

- **Agent** 在工作树里通过 CLI（`uv run asset-hub ...`）直接 `import` service 层干活，SKILL.md 是其操作手册；
- **人类** 通过 `serve start --mode prod` 起本地 Web 服务后浏览器访问。

人类侧的问题：必须有 Python/Node/uv/pnpm 工具链 + 源码树才能跑，谈不上"便携"。本设计给人类用户一个**双击即用、可整文件夹搬迁**的桌面 app，作为与"Agent 源码形态"并列的第二种 release。

## 2. 范围

**做：**

- 新增 `desktop/` 接口层（pywebview 窗口 + 进程内 uvicorn 启动编排）
- 新增包根横切 helper：`runtime.py`（frozen 检测 + 路径解析）、`migrate.py`（编程式 alembic upgrade）
- 改 `config.Settings.data_dir` 默认值走 `runtime.data_root()`（不再相对 cwd）
- 改 `api/app.py` 的 `_FRONTEND_DIST` 走 frozen-aware 绝对路径 + frozen 时无条件挂载 SPA
- **补 undo 的 GUI 化**：transitions router 新增"撤销上一次流转"端点 + 前端时间线撤销入口（兑现 issue24 Q2 预留）
- `pyproject` 新增可选依赖组 `desktop = ["pywebview"]`
- 仓库根 `packaging/asset_hub.spec`（PyInstaller）+ CI Windows 构建 job
- 各层测试（unit 路径解析、migration 编程式 upgrade、api undo、前端 undo、回归）

**不做（YAGNI）：**

- 多用户 / 认证 / 权限
- macOS / Linux 桌面版（v1 只 Windows）
- 自动更新 / 代码签名 / 安装器（Inno Setup）
- 服务模式打包（headless server exe）—— 服务端继续走源码/`serve`
- 改动 `cli/` / `serve` / SKILL.md 的任何现有行为
- 托盘图标（pystray 等）

## 3. 关键设计决策

| # | 决策 | 选择 | 理由 |
|---|---|---|---|
| Q1 | 两种 release 的关系 | **纯新增桌面版**，Agent 侧不变 | 项目定位单人 + Agent；Agent 本就在仓库里跑，打 wheel 收益小、徒增版本漂移 |
| Q2 | "迁移模式"指什么 | **数据便携** | 整个 `data/`（库+附件）随 exe 文件夹拷走、换机即用 |
| Q3 | 人类 UI 外壳 | **pywebview 原生窗口** | 用 Windows 内置 WebView2 开真窗口，不打包 Chromium、单 Python 工具链、PyInstaller 友好。Electron 要双工具链 + Python sidecar + ~200MB Chromium，杀鸡用牛刀 |
| Q4 | CLI 表面 | **纯 GUI，不暴露 CLI** | GUI 已覆盖全部领域操作（见 §4.1）；`cli` 包在打包时 `excludes` 排除 |
| Q5 | 升级时旧库迁移 | **启动时编程式 `alembic upgrade head`** | 数据便携 → 跨版本保留 → 必须自动迁移；人类不会手动跑 alembic。失败弹窗而非裸崩 |
| Q6 | 数据落点 | **exe 同级 `./data`（铁律）**；只读位置 → 启动预检弹框提示用户移动文件夹后退出（不自动搬家）；`ASSET_HUB_DATA_DIR`（可经 exe 同级 `.env`）作唯一显式逃生口 | "数据永远贴着 exe"为不可破的便携前提；隐形回退到 AppData 会让用户误以为数据丢失 |
| Q7 | 打包目标数量 | **单一目标（桌面版）** | 服务端走源码，无需 headless server exe |
| Q8 | undo 是否补 GUI/API | **补** | issue24 Q2 明确"未来真要 GUI 化再补"，本设计正是该时刻；否则纯 GUI 版比 CLI 少一个能力 |

## 4. GUI 能力覆盖核对

逐条比对 CLI 命令 vs API/GUI，确认"纯 GUI"不丢能力：

| 能力 | API router | GUI | 备注 |
|---|---|---|---|
| 资产增删改、登记 | `assets` | ✅ | |
| 10 种状态流转 | `transitions` | ✅ | checkout/return/reassign/retire/dispose/report-broken/declare-unrepairable/recover/reinstate/dismiss |
| 类型管理 + 自定义字段 | `types` | ✅ | 含字段构建器 |
| 附件上传/查看 | `attachments` | ✅ | |
| CSV/XLSX 导出 | `export` | ✅ | `export-button.tsx` |
| 看板统计 | `stats` | ✅ | dashboard |
| **`asset undo`** | **无** | **❌→ 本设计补** | service `undo_last_transition` 已存在，仅缺 API + GUI |

`serve`（进程管理）与 `--json`（信封）是 CLI 独占，但对桌面 exe 无意义（exe 即服务器；`--json` 给 Agent），无需补。

## 5. 架构与启动流程

桌面入口是**第三个接口层**，与 `api/`（HTTP）、`cli/`（Typer）平级，建立在共享核心（`services`/`repositories`/`models`/`storage`）之上。它**不走** `serve` 的 subprocess 编排（保护开发期 `serve dev`）。

```
desktop/launcher.py::main()
 ├─ 1. runtime: 解析 resource_root(只读 _MEIPASS) + data_root(可写, exe同级 ./data)
 ├─ 2. 预检（见 §7.7）:
 │       · data_root 不可写 → 原生消息框"请把文件夹移到可写位置" → 退出
 │       · WebView2 缺失   → 原生消息框"请安装 Edge WebView2 Runtime" → 退出
 ├─ 3. migrate.run_migrations(): 编程式 alembic upgrade head（失败→弹原生错误框, 退出）
 ├─ 4. 后台线程: uvicorn.Server(create_app(), 127.0.0.1:<空闲端口>, reload=False, workers=1)
 ├─ 5. server.wait_until_ready(): 轮询 /api/healthz 直到就绪（复用 serve 的 probe 思路）
 └─ 6. 主线程: window.open_window(title, url) → pywebview.start() 阻塞
        关窗 → server.should_exit = True → 进程干净退出
```

要点：

- **端口**：选空闲端口（避免 8000 被占）；URL 传给窗口。
- **传 app 对象**：`uvicorn.Server(Config(app=create_app(), ...))`，**不传字符串** `"asset_hub.api.app:app"` —— 避免 uvicorn 字符串动态 import，让 router 走静态图（PyInstaller 可追踪，见 §9）。
- **单 worker + `multiprocessing.freeze_support()`**：避免 frozen 下 spawn 子进程。
- **uvicorn 日志必须关掉默认 dictConfig**：`console=False` 的 windowed exe 下 `sys.stdout/stderr=None`，uvicorn 默认 `ColourizedFormatter` 会调 `sys.stdout.isatty()` → `AttributeError` → server 线程启动期静默崩 → `wait_until_ready` 超时弹"启动超时"，窗口永远开不出（源码态/带 console 测不出）。故 `uvicorn.Config(..., log_config=None, access_log=False)`。
- **window 必须在主线程**：pywebview 要求；故 uvicorn 放后台线程。
- **就绪后再开窗**：先 `wait_until_ready` 再 `open_window`，否则窗口首帧可能"连接被拒绝"（skeptic 复核指出的时序问题）。

## 6. 目录结构

```
src/asset_hub/
├── api/              # HTTP 接口（仅改 app.py 路径解析）
├── cli/              # Typer 接口（不动；打包时 excludes 排除）
├── desktop/          # ★新增：pywebview 接口
│   ├── __init__.py
│   ├── launcher.py   # main()：迁移→起 server 线程→开窗（编排，薄）
│   ├── server.py     # uvicorn-in-thread + wait_until_ready（纯函数，可测，不碰 webview）
│   └── window.py     # pywebview 建窗 + WebView2 缺失兜底（唯一不可测薄片）
│
├── runtime.py        # ★新增：is_frozen() / resource_path() / data_root()
├── migrate.py        # ★新增：run_migrations()
├── config.py         # Settings.data_dir 默认改走 runtime.data_root()
├── db.py             # create_all 与迁移先后理顺
├── services/ repositories/ models/ storage/ alembic/   # 核心，不动
└── api/routers/transitions.py   # ★加 undo 端点

<repo root>/
├── packaging/
│   ├── asset_hub.spec           # ★PyInstaller spec
│   └── (icon.ico / version_info — 可选)
├── pyproject.toml               # ★加 optional-dependencies.desktop = ["pywebview"]
└── .github/workflows/release-desktop.yml   # ★Windows 构建 job

frontend/src/
├── api/hooks/transitions.ts             # ★加 useUndoLastTransition
└── features/assets/detail/...           # ★时间线/详情加撤销入口
```

横切 helper（`runtime.py` / `migrate.py`）放包根：它们同时被 `api`（`resource_path` 定位 dist）和 `desktop`（`data_root` + 迁移）消费，不属于任何单一接口。

## 7. 详细改动

### 7.1 `runtime.py`（新增）

```python
import sys
from pathlib import Path

def is_frozen() -> bool:
    return getattr(sys, "frozen", False)

def resource_root() -> Path:
    """只读资源根：frozen → _MEIPASS；源码 → 仓库根。"""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS"))  # PyInstaller onedir/onefile 均设置
    # 源码态：runtime.py 在 src/asset_hub/ 下，仓库根 = parents[2]
    return Path(__file__).resolve().parents[2]

def resource_path(*parts: str) -> Path:
    return resource_root().joinpath(*parts)

def data_root() -> Path:
    """可写数据根。frozen → exe 同级 ./data；源码 → cwd 下 ./data。
    无自动回退——exe 同级不可写时由启动预检弹框提示用户移动文件夹（见 §7.7）。"""
    # frozen: Path(sys.executable).parent / "data"；源码: Path("data")
```

- **只读资源**统一走 `sys._MEIPASS`：PyInstaller 在 onedir 与 onefile 下**都**会设置它（onedir 指向 bundle 目录），故 `resource_root()` 无需区分两种模式。
- **可写数据**才用 exe 同级：`data_root()` frozen 时 = `Path(sys.executable).parent / "data"`。**不自动回退**到 AppData——不可写由启动预检处理（§7.7），守住"数据永远贴着 exe"的铁律。
- 源码态 `data_root()` 必须等价于现状 `Path("data")`，否则破坏 Agent CLI 与测试（`isolated_db` 走 `ASSET_HUB_DATA_DIR`，仍优先生效）。
- **v1 用 onedir**（启动快、无解压临时目录、杀软误报低）；onefile 仅作可选格式。

### 7.2 `config.py`

```python
from asset_hub import runtime

class Settings(BaseSettings):
    data_dir: Path = Field(default_factory=runtime.data_root)
    ...
```

`data_dir` 默认从字面量 `Path("data")` 改为 `default_factory=runtime.data_root`。`ASSET_HUB_DATA_DIR` 环境变量/`.env` 覆盖语义不变（pydantic-settings 字段名映射；显式值优先于 `default_factory`）。

**`.env` 逃生口（exe 同级解析 + 写回 os.environ）**：`Settings` 已配 `env_file=".env"` + `env_prefix="ASSET_HUB_"`，故在 `.env` 写一行 `ASSET_HUB_DATA_DIR=<路径>` 即可覆盖数据落点。但 pydantic-settings 默认在 **cwd** 找 `.env`，而双击 exe 的 cwd 不可控——所以 frozen 下 launcher 必须显式按 **exe 同级**解析。

**关键（避免 split-brain）**：解析结果不能只用于预检。`migrate.run_migrations()` / `db.get_engine()` / `storage` / alembic `env.py` 内部都是**裸 `Settings()`**（按 cwd 找 .env），若 launcher 只把 `_env_file` 喂给自己那一个 Settings，预检放行的目录与真实 DB/迁移落点会分裂。**解法**：launcher 启动最早期解析出 `data_dir` 后**写回 `os.environ["ASSET_HUB_DATA_DIR"]`**，使后续所有裸 `Settings()` 自然命中同一落点（env 优先于 .env/default）：

```python
def _bootstrap_settings() -> Settings:
    if runtime.is_frozen():
        env_file = Path(sys.executable).resolve().parent / ".env"
        s = Settings(_env_file=str(env_file) if env_file.exists() else None)
        os.environ["ASSET_HUB_DATA_DIR"] = str(s.data_dir)  # 让全链路裸 Settings() 跟随
        return s
    return Settings()
```

源码态行为不变（cwd=仓库根，`.env` 照旧）。必须补一条测试：frozen + exe 同级 `.env` 改 `ASSET_HUB_DATA_DIR` → 后续 `Settings().db_url` 跟随。

### 7.3 `migrate.py`（新增）

```python
from alembic import command
from alembic.config import Config
from asset_hub import runtime
from asset_hub.config import Settings

def run_migrations() -> None:
    import asset_hub
    alembic_dir = Path(asset_hub.__file__).parent / "alembic"  # 包内资源，两态统一
    cfg = Config()  # 不读相对 alembic.ini
    cfg.set_main_option("script_location", str(alembic_dir))
    cfg.set_main_option("sqlalchemy.url", Settings().db_url)
    command.upgrade(cfg, "head")
```

- `script_location` 按**包目录解析**：源码态 = `src/asset_hub/alembic`，frozen 态 = `_MEIPASS/asset_hub/alembic`（两者都等于"包目录 `/alembic`"），统一用 `Path(asset_hub.__file__).parent / "alembic"`。**注意**：alembic 在包内，用包目录解析；`frontend/dist` 在包外，才用 `runtime.resource_root()`（§7.1）。不再依赖相对仓库根的路径。
- `env.py` 现有逻辑（`Settings()` 覆盖 url、`render_as_batch=True`、`import asset_hub.models.*`）原样复用——但注意 `env.py` 被 alembic 动态 exec，其 `import asset_hub.models` 需确保被收进 bundle（§9 hiddenimports 校验）。
- 与 `db.py` `create_all` 的先后（明确规则）：桌面入口在**起 engine 前先调 `run_migrations()`**，让 alembic 成为唯一 schema 事实源（全新库也由迁移链建表 + stamp）。迁移完成后即使 `get_engine` 再走 `create_all` 也无害（表已存在，只补缺失）；**禁止**在迁移前触发 `create_all`，否则会建出与迁移链 head 不一致的表导致 SQLite `batch_alter` 失败。

### 7.4 `api/app.py`

```python
from asset_hub import runtime
_FRONTEND_DIST = runtime.resource_path("frontend", "dist")  # 原 Path("frontend/dist")
...
# frozen 时无条件挂载，忽略 ASSET_HUB_MODE=dev；dist 缺失 log.warning 而非静默跳过
_is_dev_mode = (not runtime.is_frozen()) and os.environ.get("ASSET_HUB_MODE") == "dev"
```

- frozen 下永远是 prod-like 自托管，必须挂 SPA；`ASSET_HUB_MODE=dev` 残留不应让 exe 白屏。
- dist 不存在时 `log.warning`，避免"白屏无报错"。

### 7.5 undo 的 GUI 化

**API**（`api/routers/transitions.py`）新增端点，复用既有 service：

```python
@router.post("/{asset_id}/transitions/undo", response_model=TransitionRead)
def undo_last(asset_id: uuid.UUID, session: Session = Depends(get_session)) -> TransitionRead:
    return TransitionService(session).undo_last_transition(asset_id)
```

- 路径挂在 `assets` 前缀下（与现有 transitions router 一致，prefix `/api/assets`）。最终路径 `POST /api/assets/{asset_id}/transitions/undo`。
- 域异常（`NotFoundError`/`StateError`）由 `api/app.py` 集中映射（404/409），router 不写 try/except。
- 跑 `pnpm --dir frontend gen:api` 同步 openapi 类型。

**前端**：`api/hooks/transitions.ts` 加 `useUndoLastTransition`；详情页/时间线加"撤销上一次流转"入口（带确认弹窗，因为是物理删除不可 redo）。

**契约文档**：按 CLAUDE.md，改状态流转产出格式前先对齐 `references/transitions.md`（undo 段已存在，补"现也经 API/GUI 暴露"）。

### 7.6 `pyproject.toml`

```toml
[project.optional-dependencies]
desktop = ["pywebview>=5"]

[dependency-groups]
packaging = ["pyinstaller>=6"]   # 仅构建期需要；不进运行时 bundle
```

核心 `dependencies` 不变 → Agent 侧 `uv sync` 默认不装 pywebview/pyinstaller，零影响。

**构建依赖必须显式声明**：`pyinstaller` 不在 core/dev/desktop 任一处则 `uv run pyinstaller` 会报找不到（`uv run` 不像 `uvx` 凭空拉工具）。故单列 `packaging` group。构建命令：`uv sync --extra desktop --group packaging` 后 `uv run --group packaging pyinstaller packaging/asset_hub.spec`。

### 7.7 启动预检（`desktop/launcher.py` + `window.py`）

开窗 / 起服务前的两道预检，失败都走"原生消息框 + 退出"而非裸崩。检查逻辑抽成可测纯函数，只有"弹框"本身不可测。

**可写性预检**：复用 `serve` 已有的 `_ensure_dirs_writable` 思路——往 `data_root()` `touch` 一个临时文件再删，试得动才继续。不可写时弹框：

> asset-hub 需要写入数据，但当前位置（`<exe目录>`）不可写。请把整个 asset-hub 文件夹移动到文档/桌面等你有权限的位置后重新运行。（高级用户可在 exe 同级 `.env` 设 `ASSET_HUB_DATA_DIR` 指定别处。）

→ 退出（非零码）。**不自动回退**到 AppData（Q6 铁律）。

**WebView2 预检**：`window.py` 捕获 pywebview 启动失败（Win 后端找不到 WebView2 Runtime），弹框提示安装并给微软下载链接，退出。

## 8. 打包：模块选择机制

PyInstaller **不自动判断形态**，由 spec 的**入口脚本**驱动，四条叠加：

1. **入口决定主体**：spec 入口 = `desktop/launcher.py`。顺其静态 import 图收集：`launcher → api.app → routers → services → repositories → models → storage`（routers 在 `app.py` 顶层静态 import，§5 已确认无动态加载）。`launcher` 不 import `cli`，故 `cli`/`serve` 不在图上。
2. **`excludes=['asset_hub.cli']`**：兜底钉死 + 瘦身，落实"不含 CLI"。
3. **`hiddenimports`**（补静态分析盲区，仅真正的动态导入）：
   - uvicorn auto 选择层：`uvicorn.loops.asyncio`、`uvicorn.protocols.http.h11_impl`、`uvicorn.protocols.http.httptools_impl`、`uvicorn.protocols.websockets.websockets_impl`、`uvicorn.lifespan.on`、`uvicorn.lifespan.off`（**不**列 `wsproto_impl`：本项目无 WS 路由且未必装 wsproto，列了只多一条构建告警）
   - `alembic.ddl.sqlite`、`sqlalchemy.dialects.sqlite`
   - `typer.testing`（仅当未被 excludes 波及；cli 排除后通常无需，校验后定）
   - Windows **不打** uvloop / watchfiles（reload 关闭，不需要）
   - 必要时 `collect_submodules('uvicorn')`、`--collect-all pydantic`、`--collect-data openpyxl`、`copy_metadata('asset-hub')`（`app.py` 用 `version("asset-hub")`）
4. **`datas`**（非 Python 资源）：
   - `('frontend/dist', 'frontend/dist')`
   - `('src/asset_hub/alembic', 'asset_hub/alembic')` —— 含 versions/*.py（alembic **运行时目录扫描**加载，非 import，故 excludes 不影响、必须当数据打）、env.py、script.py.mako；排除 `__pycache__`
   - `alembic.ini` 非必需（`migrate.py` 不读它），但带上无害

**运行时形态判定**不是"选模块"，而是 `runtime.is_frozen()` 切**行为**（路径解析 + SPA 挂载）。同一份代码：源码态 Agent 走 `cli/main`，frozen 态人类走 `desktop/launcher`。

构建：onedir（启动快、无解压临时目录、杀软误报低、`_MEIPASS` 跨启动稳定，便于可写数据放 exe 旁）；zip 分发。onefile 仅作可选格式。

## 9. 数据生命周期

- **首启**：`data_root` 不存在则建；`run_migrations()` upgrade head（全新库由迁移链建表并 stamp）。
- **后续启动**：`upgrade head` 把旧库升到当前版本（已是 head 则秒过）。
- **便携**：整个 exe 文件夹（含 `data/`）拷到另一台机器，数据原样可用。
- **只读安装位置**：exe 同级不可写时，启动预检弹框提示用户把文件夹移到可写位置后退出（不自动搬家，§7.7）。高级用户可在 exe 同级 `.env` 写 `ASSET_HUB_DATA_DIR=...` 显式指定别处。
- **WebView2 缺失**（极老机器）：`window.py` 捕获 pywebview 启动失败，弹原生消息框提示"请安装 Edge WebView2 Runtime"并给下载链接，而非裸崩。

## 10. 测试计划

- **`tests/unit/test_runtime.py`**：`resource_path` / `data_root` 在 frozen / 源码两态解析（monkeypatch `sys.frozen` / `sys._MEIPASS` / `sys.executable` / `ASSET_HUB_DATA_DIR`）；`.env` 按 exe 同级解析；启动预检的可测纯函数——不可写时返回"提示移动"判定（弹框前那一步）、WebView2 缺失兜底（mock pywebview 抛错）。
- **`tests/migration/`**（CLAUDE.md 强制）：新增一条覆盖"编程式 `run_migrations()` 把旧版本 schema 库 upgrade 到 head"，并验证 `create_all` 与迁移先后不冲突。
- **`tests/api/test_transition_undo_api.py`**：新 undo 端点 —— 成功（200 + TransitionRead）、asset 不存在（404）、无 transition（409）。
- **前端**：`useUndoLastTransition` hook 测试（msw mock）；撤销入口组件 unit；一条 e2e 烟测（checkout → undo → 状态回退）。
- **回归**：`serve dev`（pnpm dev + uvicorn --reload）路径零改动，跑通确认无回归；现有全套 `pytest` + 前端测试绿。
- **干净机冒烟（手动）**：无 Python/Node 机器跑 exe → 开窗 → 建 asset（验 pydantic+sqlalchemy+sqlite）→ 导出 xlsx（验 openpyxl 数据文件）→ 关窗重开验数据持久 → 用旧库验自动 upgrade（含 batch_alter 的 v2/v3/v4 迁移）→ dist 托管。

## 11. 文档同步清单

| 文件 | 变更 |
|---|---|
| `references/deploy.md` | 新增"桌面便携版"段：构建命令、数据落点（exe 同级 `./data`；只读位置提示移动；`.env` 设 `ASSET_HUB_DATA_DIR` 逃生口）、升级（替换 exe 保留 data）、WebView2 前置 |
| `references/transitions.md` | undo 段补"现也经 `POST /api/assets/{id}/transitions/undo` 与 GUI 暴露" |
| `SKILL.md` | 部署小节加桌面版一句话指引（Agent 仍用源码/`serve`，不受影响） |
| `CLAUDE.md` | "开发命令"加桌面版构建命令（`uv sync --extra desktop` + `pyinstaller packaging/asset_hub.spec`）；目录结构提及 `desktop/` 第三接口层 |
| `README.md` | 面向人类用户的下载/使用说明 |
| `frontend` gen:api | 后端 undo schema 改动后必跑 `pnpm --dir frontend gen:api` |

## 12. 实施顺序（写实现计划时参考）

按"先解耦、可测，再打包"分阶段，每阶段源码态全测试绿：

1. **路径解耦**：`runtime.py` + `config.data_dir` 改 `default_factory`；`api/app.py` 路径与 SPA 挂载；unit 覆盖两态。**不打包**。
2. **运行时迁移**：`migrate.py` + 理顺 `db.py` 顺序；`tests/migration` 加一条。
3. **undo GUI 化**：API 端点 + `tests/api`；`gen:api`；前端 hook + 入口 + 测试。
4. **桌面入口**：`desktop/{launcher,server,window}.py`；`pyproject` 加 `desktop` extra；server/wait_until_ready 可测部分加 unit。
5. **打包脚本**：`packaging/asset_hub.spec`；本地构建 onedir 跑通干净机冒烟。
6. **CI**：`.github/workflows/release-desktop.yml`（Windows runner：`uv sync --extra desktop` → `pnpm build` → `pyinstaller` → 产 onedir + zip artifact）。
7. **文档同步** + 版本号（按 [[feedback_versioning]] 保守策略，作者拍板 minor/patch）。

## 13. 风险与边界

- **uvicorn auto 层 try-import**：冻结器静态图抓不到 except 分支真实实现，漏打启动崩或静默降级——`hiddenimports` 显式补 + 干净机实测（头号风险）。
- **alembic versions 是数据文件**：默认不进 bundle，漏收则 upgrade 找不到 revision；`datas` 收整个 alembic 目录 + `migrate.py` 重定向 `script_location`。
- **env.py 动态 exec 的 model import**：`env.py` 被 alembic 加载执行，其 `import asset_hub.models.*` 需在 bundle 内（`collect_submodules('asset_hub')` 或确认静态图已覆盖）；打包后必须实测 upgrade head。
- **create_all / alembic 双轨漂移**：必须保证迁移先于 create_all 或对已存在库跳过 create_all。
- **误伤 serve dev**：严格用独立 `desktop` 入口 + `is_frozen` 分流，绝不把 in-process 逻辑塞进 `serve` 状态机。
- **只读资源 vs 可写数据分离**：只读资源统一走 `sys._MEIPASS`（onedir/onefile 均设置）；可写数据走 `Path(sys.executable).parent`（onedir 下与 bundle 同级）。两者不可混用——把可写 DB 放进 `_MEIPASS`（onefile 下是临时解压目录）会导致数据丢失。
- **WebView2 运行时**：Win10/11 多数内置，老机器需兜底提示而非崩。

## 14. 非目标重申

多用户/认证、macOS/Linux、自动更新、代码签名、安装器、headless 服务版打包、托盘——均不在 v1。需要时回到本 spec 的对应章节再评估，不在实现期临时扩张。
