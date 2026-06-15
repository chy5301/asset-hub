# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 文档与进度

**设计决策**放在 `docs/superpowers/specs/`，**里程碑计划**放在 `docs/superpowers/plans/`，文件名带日期（`YYYY-MM-DD-<slug>.md`）。其他工具/插件如有自己的 docs，按 `docs/<plugin>/` 平铺。

**当前进度**：看 git log 和分支，不在这里记录。

遇到架构、数据模型、CLI 契约疑问，先在 `docs/` 下找**最新**的 spec；不确定时 `ls docs/ -R`。

Agent 操作手册：项目根 `SKILL.md`（asset-hub skill 主入口）+ `references/{envelope,transitions,workflows,deploy}.md`（信封契约、状态机、常见任务流、部署），改 CLI / 状态流转 / 命令产出格式时**先**对齐这两份再动代码。

## 项目定位

小组资产管理工具。v1 明确只服务两类使用者：

- **单一人类用户**（作者本人）通过 Web GUI（浏览器或桌面便携版）维护资产
- **该用户的 AI Agent**（Claude Code）通过 CLI 完成登记、派发、归还、查询、导出

这一定位决定了很多取舍：不做多用户认证、不做权限系统、不做扫码贴条；但 CLI 与 SKILL.md 的 Agent 友好度是一等公民。

创建 asset type 时可参考 `examples/types/`（如 `gpu.json`、`laptop.json`）的 `custom_fields` 结构。

## 架构关键约束

以下几条是跨文件才能看出来的"大局"，违反后果严重：

### 1. 三层分离，CLI 不走 HTTP

```
Web GUI (React/TS)    ──HTTP──┐
Desktop (pywebview)   ──HTTP──┼──► FastAPI ──► Service 层（唯一事实）──► Repository/SQLModel/FS
CLI (Python/Typer)   ─import──┘
```

CLI 直接 `from asset_hub.services import ...` 调用 service 层，**不**通过 HTTP 调自己的 API。新增能力时必须先在 service 层落地，再分别由 FastAPI router 和 Typer command 暴露。

### 2. ORM 与 API DTO 强制隔离

- `src/asset_hub/models/` 下的 `SQLModel(table=True)` **只**用于数据库映射
- `src/asset_hub/api/schemas/` 下的 Pydantic `BaseModel` 定义所有请求/响应 DTO，**不**继承 ORM 模型
- Service 层返回 domain 对象或 DTO，**不**把 ORM 模型泄漏到 FastAPI router 或 CLI
- 聚合/复杂查询走 SQLAlchemy 2.x `select()`，不依赖 SQLModel 高层查询糖

这是为了让未来迁 "SQLAlchemy 2.x + 纯 Pydantic" 只需删一层。新代码若把 `table=True` 模型直接返给路由，算违反约定。

### 3. 存储抽象

附件 I/O 一律走 `StorageAdapter` 接口（在 `src/asset_hub/storage/` 实现，v1 用本地文件系统）。数据库只存元数据（路径、sha256、size、mime）。不要在 service 里直接写文件路径。

### 4. CLI `--json` 标准信封

所有 CLI 命令的 `--json` 输出遵循固定信封：

```json
{"success": true, "data": {...}, "metadata": {"took_ms": 12, "count": 5}, "error": null}
```

退出码：0 成功、1 一般错误、2 用法错误、3 资源不存在、10 dry-run 预览（非错误）。破坏性命令（如 `asset delete`）必须支持 `--dry-run`。

### 5. 实现模式

- **API 异常映射集中在 `api/app.py`**：`NotFoundError`→404、`DuplicateError`→409、`ValidationError`→422。router 不写 try/except，直接让域异常冒泡
- **CLI UUID 解析走 `cli/deps.py::parse_uuid()`**：不要在每个命令里重复 `try/except ValueError`
- **CLI 输出格式复用 API DTO**：通过 `AssetRead.model_validate(a).model_dump(mode="json")`（Read DTO 带 `ConfigDict(from_attributes=True)`），避免 CLI/API 格式漂移
- **部分更新用 `_Unset` 哨兵**：`AssetService.update_asset` 用 `_Unset` 默认值，router 用 `body.model_dump(exclude_unset=True)` 传递——能正确区分"字段未传"和"显式传 null（清空）"

## 开发命令

后端（Python，所有命令走 `uv`，这是全局规范，不要直接调 `python` / `pip` / `pytest` / `ruff`）：

- 安装依赖：`uv sync`
- 启动开发 API：`uv run uvicorn asset_hub.api.app:app --reload`
- 运行 CLI：`uv run asset-hub <resource> <action>`
- CLI 命令组：`asset` / `type` / `attachment` / `stats` / `serve`（实现在 `src/asset_hub/cli/{asset_cmd,type_cmd,attachment_cmd,stats_cmd}.py`；`serve` 是子包 `cli/serve/`，入口 `cmd.py`）
- 单测：`uv run pytest` / 单个：`uv run pytest tests/unit/test_asset.py::test_register`
- lint：`uv run ruff check .` + `uv run ruff format .`（CI 用 `--check` 模式 gate；`ruff format` 负责行长，不要手动改 line-length）
- 数据库迁移：`uv run alembic revision --autogenerate -m "<slug>"` 生成 + `uv run alembic upgrade head` 执行。`src/asset_hub/alembic/env.py`（`alembic.ini` 里 `script_location` 指向）用 `Settings()` 覆盖 `sqlalchemy.url`（默认 `data/asset_hub.db`），并启用 `render_as_batch=True`（SQLite 改表必需）——新写迁移别绕过 batch。

前端（pnpm）：

- 安装：`pnpm --dir frontend install`
- 开发：`pnpm --dir frontend dev`（Vite `:5173`，代理 `/api` → `:8000`）
- 构建：`pnpm --dir frontend build` → `frontend/dist`，生产由 FastAPI 的 `StaticFiles` 托管
- lint：`pnpm --dir frontend lint`
- 测试：`pnpm --dir frontend test`（vitest 一次性）/ `test:watch` / `test:ui`
- e2e：`pnpm --dir frontend e2e`（Playwright + chromium，specs 在 `frontend/e2e/specs/`）/ `e2e:debug`
- 同步 API 类型：`pnpm --dir frontend gen:api` 拉 `:8000/openapi.json` 写到 `src/api/generated/schema.d.ts`。**后端任何 schema 改动都必须跑一次**——`openapi-fetch` 的 typed client 直接消费这份产物，漏跑会让前端类型与运行时漂移。

并发启动：`uv run asset-hub serve start --mode dev`（后端 `:8000` + 前端 `:5173`，Vite 代理 `/api`；后台 detach）。配套 `serve status`（查 PID/端口）、`serve logs --follow`（跟日志）、`serve restart`（不丢配置重启）、`serve stop`（干净停掉整个进程树）、`serve doctor`（端口/PID/依赖体检）。生产模式 `--mode prod` 自动 build 前端 + 单端口 `:8000` 对外。

桌面便携版构建：`uv sync --extra desktop --group packaging` + `pnpm --dir frontend build` + `uv run pyinstaller packaging/asset_hub.spec`。产物在 `dist/asset-hub/`，CI 归档为 zip。详见 `packaging/asset_hub.spec` 和 `references/deploy.md`。

### 测试分层

- `tests/unit/` — service 层，用真实 SQLite（`tmp_path`）+ `session` fixture
- `tests/cli/` — `typer.testing.CliRunner` + autouse `isolated_db` fixture（monkeypatch `ASSET_HUB_DATA_DIR`）
- `tests/api/` — `fastapi.testclient.TestClient` + `dependency_overrides[get_session]`
- `tests/migration/` — Alembic 迁移正确性（v2 状态机、v3 资产模型列改动）；改 schema/迁移时**必须**新加一条

新加功能严格走 TDD：先在对应层写失败测试，再实现。

前端（vitest + jsdom，配置见 `frontend/vitest.config.ts`，setup 见 `frontend/tests/setup.ts`）：

- `frontend/tests/unit/` — 纯函数（zod schema 生成、checkout 当前态推导、custom-field 格式化、upload progress 等）。新增逻辑优先在这一层 TDD。
- `frontend/tests/hooks/` — React Query hook、RHF + Zod 表单组件，配 `frontend/tests/msw-handlers.ts` mock HTTP。
- e2e：`frontend/e2e/` 用 Playwright 跑关键流程，`.github/workflows/e2e.yml` 在 PR 和 push main 时 gate（chromium，dist 模式）。日常迭代仍**优先**用 `playwright` MCP 烟测（`browser_navigate` / `browser_snapshot` / `browser_click` / `browser_fill_form` / `browser_take_screenshot`），把"必须长期守住"的场景再固化到 e2e specs。
  - **本地跑前提**：`global-setup.ts` 要求 `ASSET_HUB_DATA_DIR` 必填（一般指向 tmp 目录），未设直接抛错。
  - **gotcha**：`playwright.config.ts` 的 `webServer` 绑死 `:8000` 且 `reuseExistingServer: !CI`——本地若已有 `serve` 实例占用 :8000，e2e 会**复用它（连错数据库）**而非起隔离实例，spec 会莫名失败。本地跑 e2e 前先 `serve stop`，或只依赖 CI 的 e2e job。
  - jsdom 抹不出 Radix 受控组件的时序渲染 bug（如挂载后才 `reset` 的回显）；这类只在真实浏览器复现，回归守卫必须落在 e2e 而非 vitest。

### 目录补充

- `desktop/` — 桌面便携版第三接口层（pywebview WebView2 内嵌），入口 `packaging/desktop_entry.py`（调用 `src/asset_hub/desktop/launcher.py`）
- `packaging/` — PyInstaller spec 文件（`asset_hub.spec`），构建桌面便携版产物

## 前端审美约束

遵循 `frontend-design` skill：**避免 AI 模板脸**。配色、间距、字体、动效都要经过设计决策，不使用框架默认值；空状态/错误态/加载态需要专门视觉处理。这不是可选项。

项目级设计规则母文件：`design-system/asset-hub/MASTER.md`（全局色板、字体、组件规范）。改某个页面前先看 `design-system/asset-hub/pages/<page-name>.md`——若存在，其规则 **override** MASTER.md，不存在则严格走 MASTER。

## 前端工程约束

- `tsconfig.app.json` 必须保持 `"strict": true`：TanStack Router 的类型声明里有守卫，检测到 `strictNullChecks` 未开会把 `createRouter` 参数类型替换成字符串字面量 `"strictNullChecks must be enabled in tsconfig.json"`，直接 compile error。不要拆 `strict` 为子项。
- `eslint.config.js` 对 `src/routes/**` 关闭了 `react-refresh/only-export-components`：file-based 路由同文件既 `export Route` 又定义组件，该规则会误报——不要删这条 override，也不要把路由组件拆到别的文件。

## CI Gate

- `.github/workflows/ci.yml`：PR 与 push main 触发，并行跑 `backend`（`ruff check` + `ruff format --check` + `pytest`）和 `frontend`（`lint` + `tsc -b` + `vitest`），10 分钟超时
- `.github/workflows/e2e.yml`：PR 与 push main 触发，跑 Playwright chromium dist 模式

本地推 PR 前**至少**跑 `uv run ruff check . && uv run ruff format --check . && uv run pytest`（后端）和 `pnpm --dir frontend lint && pnpm --dir frontend exec tsc -b && pnpm --dir frontend test`（前端），减少 CI 来回。

## 里程碑划分

判断"某功能是否该现在做"时，先在 `docs/` 下找**最新**的路线图；不要自作主张把后面里程碑的事现在做。

## 选型待观察项（来自设计文档 §13）

- SQLModel 维护节奏不稳时考虑迁 SQLAlchemy 2.x + 独立 Pydantic
- Tremor 若推出 Radix/shadcn 原生版本可再评估

遇到相关技术选择时，不要再开脑洞，回到设计文档对应章节。

## 发版流程

版本权威源是 `pyproject.toml`；一次 release 提交需同步**三处**：`pyproject.toml`（手改）+ `uv.lock`（跑 `uv lock` 派生）+ `frontend/package.json`（手改）。OpenAPI `info.version` 运行时读包元数据，无需手改（改后跑 `uv sync` 让本地元数据刷新）。

手顺：① feature PR **squash** 合并入 main → ② **发版前先核对文档**：`README.md`（版本号引用、功能清单、路线图/里程碑状态）、`docs/deployment.md` 与 `references/deploy.md`（部署/升级手顺有无随本次改动失效）、相关 `docs/superpowers/specs`——有漂移先一并修；**若本次涉及 CLI / 状态机 / transition / envelope / 命令产出的增减，必须同步 `SKILL.md` + `references/{envelope,transitions,workflows}.md`**（纯前端/纯内部修复则无需动）→ ③ bump 三处版本 → ④ 写 `docs/superpowers/release-notes-vX.Y.Z.md`（沿用既有结构）→ ⑤ 提交 `chore(release): 发布 vX.Y.Z` 推 main → ⑥ 打 **annotated tag `vX.Y.Z` 推送**，触发 `.github/workflows/release-desktop.yml`（`tags: ["v*"]`）自动建 GitHub Release + 挂 Windows onedir zip。

SemVer 偏保守，版本号由作者拍板（契约小增强按 patch）。
