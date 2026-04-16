# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 当前状态

**设计阶段，尚未开始实现。** 仓库目前只含设计文档，无源码。

唯一权威设计文档：`docs/superpowers/specs/2026-04-15-asset-hub-design.md`。开始任何实现前必读；若对架构、数据模型、CLI 契约有疑问，以该文档为准。

README.md 是对外简介，**不要**把其中的"规划中"当作实现现状。

## 项目定位

班组/小组资产管理工具。v1 明确只服务两类使用者：

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

附件 I/O 一律走 `StorageAdapter` 接口（`src/asset_hub/storage/base.py`），v1 实现为 `local_fs.py`。数据库只存元数据（路径、sha256、size、mime）。不要在 service 里直接写文件路径。

### 4. CLI `--json` 标准信封

所有 CLI 命令的 `--json` 输出遵循固定信封：

```json
{"success": true, "data": {...}, "metadata": {"took_ms": 12, "count": 5}, "error": null}
```

退出码：0 成功、1 一般错误、2 用法错误、3 资源不存在、10 dry-run 预览（非错误）。破坏性命令（如 `asset delete`）必须支持 `--dry-run`。

## 开发命令（实现后使用）

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

并发启动：`./scripts/dev.sh`（M1 里程碑后提供）。

## 前端审美约束

遵循 `frontend-design` skill：**避免 AI 模板脸**。配色、间距、字体、动效都要经过设计决策，不使用框架默认值；空状态/错误态/加载态需要专门视觉处理。这不是可选项。

## 路线图定位

- **M1 骨架** → service/repo 抽象 + CLI `type define / asset register / list / show` + FastAPI 最小端点 + 前端脚手架
- **M2 核心流程** → checkout/return/history、附件上传、Web 列表+详情+动态表单
- **M3 特性完整** → 看板 4 图、CSV/XLSX 导出、SKILL.md、测试覆盖
- **M4 UI 打磨** → 设计审美达标

判断"某功能是否该现在做"时，先定位里程碑。

## 选型待观察项（来自设计文档 §13）

- SQLModel 维护节奏不稳时考虑迁 SQLAlchemy 2.x + 独立 Pydantic
- `openapi-fetch` vs `@hey-api/openapi-ts` 在 Plan 阶段择优
- Tremor 若推出 Radix/shadcn 原生版本可再评估

遇到相关技术选择时，不要再开脑洞，回到设计文档对应章节。
