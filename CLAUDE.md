# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 文档与进度

**设计决策**与**里程碑计划**放在 `docs/` 下（可能按工具/插件分子目录，文件名带日期）。

**当前进度**：看 git log 和分支，不在这里记录。

遇到架构、数据模型、CLI 契约疑问，先在 `docs/` 下找**最新**的 spec；不确定时 `ls docs/ -R`。

## 项目定位

小组资产管理工具。v1 明确只服务两类使用者：

- **单一人类用户**（作者本人）通过 Web GUI 维护资产
- **该用户的 AI Agent**（Claude Code）通过 CLI 完成登记、派发、归还、查询、导出

这一定位决定了很多取舍：不做多用户认证、不做权限系统、不做扫码贴条；但 CLI 与 SKILL.md 的 Agent 友好度是一等公民。

## 架构关键约束

以下几条是跨文件才能看出来的"大局"，违反后果严重：

### 1. 三层分离，CLI 不走 HTTP

```
Web GUI (React/TS) ──HTTP──┐
                           ├──► FastAPI ──► Service 层（唯一事实）──► Repository/SQLModel/FS
CLI (Python/Typer) ─import─┘
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
- 单测：`uv run pytest` / 单个：`uv run pytest tests/unit/test_asset.py::test_register`
- lint：`uv run ruff check .`

前端（pnpm）：

- 安装：`pnpm --dir frontend install`
- 开发：`pnpm --dir frontend dev`（Vite `:5173`，代理 `/api` → `:8000`）
- 构建：`pnpm --dir frontend build` → `frontend/dist`，生产由 FastAPI 的 `StaticFiles` 托管

并发启动：`./scripts/dev.sh`（后端 `:8000` + 前端 `:5173`，Vite 代理 `/api`）。

### 测试分层

- `tests/unit/` — service 层，用真实 SQLite（`tmp_path`）+ `session` fixture
- `tests/cli/` — `typer.testing.CliRunner` + autouse `isolated_db` fixture（monkeypatch `ASSET_HUB_DATA_DIR`）
- `tests/api/` — `fastapi.testclient.TestClient` + `dependency_overrides[get_session]`

新加功能严格走 TDD：先在对应层写失败测试，再实现。

## 前端审美约束

遵循 `frontend-design` skill：**避免 AI 模板脸**。配色、间距、字体、动效都要经过设计决策，不使用框架默认值；空状态/错误态/加载态需要专门视觉处理。这不是可选项。

## 前端工程约束

- `tsconfig.app.json` 必须保持 `"strict": true`：TanStack Router 的类型声明里有守卫，检测到 `strictNullChecks` 未开会把 `createRouter` 参数类型替换成字符串字面量 `"strictNullChecks must be enabled in tsconfig.json"`，直接 compile error。不要拆 `strict` 为子项。
- `eslint.config.js` 对 `src/routes/**` 关闭了 `react-refresh/only-export-components`：file-based 路由同文件既 `export Route` 又定义组件，该规则会误报——不要删这条 override，也不要把路由组件拆到别的文件。

## 里程碑划分

判断"某功能是否该现在做"时，先在 `docs/` 下找**最新**的路线图；不要自作主张把后面里程碑的事现在做。

## 选型待观察项（来自设计文档 §13）

- SQLModel 维护节奏不稳时考虑迁 SQLAlchemy 2.x + 独立 Pydantic
- `openapi-fetch` vs `@hey-api/openapi-ts` 在 Plan 阶段择优
- Tremor 若推出 Radix/shadcn 原生版本可再评估

遇到相关技术选择时，不要再开脑洞，回到设计文档对应章节。
