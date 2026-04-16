# asset-hub 设计文档

- **日期**：2026-04-15
- **状态**：初稿，待实施
- **作者**：conghaoyangbobby@gmail.com（与 Claude 协同 brainstorm）

## 1. 定位与目标

**asset-hub** 是小组内部使用的资产管理工具，聚合管理设备、服务器、计算机、硬盘、显卡等各类资产。

当前阶段（v1）明确服务的用户：
- **单一人类用户**（作者本人）通过 Web GUI 维护资产信息
- **该用户的 AI Agent**（Claude Code）通过 CLI 完成登记、领用、归还、查询、导出

**核心价值命题**：取代"用 Excel/文档维护资产"的原始方式，让 AI Agent 可以通过一句话 + 一张照片完成资产录入与流转操作，同时保留对人类友好的可视化界面。

## 2. 核心需求（v1）

### 2.1 必须支持的能力

1. **类型驱动的字段模型**：不同资产类型（笔记本、显卡、硬盘、服务器…）拥有不同的自定义字段；系统提供通用字段 + 用户为每种类型声明自定义字段
2. **资产 CRUD**：登记、查询、编辑、删除
3. **状态与流转**：派发（checkout）、归还（return），自动记录保管人、位置、时间
4. **历史记录**：每个资产的完整流转时间线（谁、何时、从哪到哪、备注）
5. **附件管理**：主要是资产照片（也支持发票、文档等），CLI 与 Web 都可上传
6. **可视化表格**：带彩色状态标签、多维筛选、排序、列显隐的资产列表
7. **最小看板**：4 张固定聚合图表（类型分布、状态分布、按保管人 Top N、闲置时长 Top N）
8. **导出**：CSV 与 XLSX 两种格式，支持"按当前筛选条件导出"
9. **Agent CLI**：覆盖以上全部能力，支持 `--json` 输出 + 标准信封，可被 Claude Code 直接调用

### 2.2 明确推迟到 v2+

- 多用户认证、基于角色的权限
- 字段级审计日志
- Postgres 迁移 / 对象存储（S3/MinIO）
- 通知与提醒（逾期未归还、维保到期）
- 时间序列趋势图、可配置看板
- 扫码/二维码贴条（永不做）
- 手机 App / 深度响应式

## 3. 技术选型

| 层 | 选型 | 理由 |
|---|---|---|
| 后端语言 | **Python 3.12+**（uv 管理） | 用户熟悉 Python；CLI 生态（Typer）优；与用户全局 `uv` 规范对齐 |
| 后端框架 | **FastAPI** | 自动生成 OpenAPI，前端可生成类型安全客户端 |
| ORM / 持久化模型 | **SQLModel**（`table=True` 仅作持久化模型） | 与 SQLAlchemy 2.x 兼容；**聚合/复杂查询直接走 SQLAlchemy 2.x `select()`** 而非 SQLModel 高层糖 |
| API DTO | **独立 Pydantic `BaseModel`**（不与 ORM 模型共用） | 持久化模型与请求/响应 schema 解耦，便于未来改栈或改接口形状 |
| 数据库 | **SQLite**（v1），预留迁 Postgres | 单机足够；Repository 层抽象使替换代价低 |
| 附件存储 | **本地文件系统**（通过 `StorageAdapter` 抽象） | 数据库只存元数据；未来可无缝切 S3/MinIO |
| CLI | **Typer** + 自定义 JSON 信封中间件 | 底层即 Click；类型签名驱动，`--help` 对 Agent 直接可用 |
| 前端 | **TypeScript + React + Vite** | 现代 SPA 审美必需；shadcn/ui 生态绑定 TS |
| 路由 | **TanStack Router** | 纯 SPA + typed search params，表格/过滤器 URL 化天然契合；RR7 的 framework mode 特性用不上 |
| 样式 | **Tailwind CSS + shadcn/ui** | 可定制的设计系统基座 |
| 表格 | **TanStack Table** | 排序/筛选/分页/虚拟滚动 |
| 图表 | **shadcn/ui charts（基于 Recharts）** | 与 shadcn/ui 同体系，避免再引一套命名空间和 Tailwind preset |
| 表单 | **React Hook Form + Zod** | 类型安全、体验佳 |
| API 契约 | **openapi-typescript + openapi-fetch** | 类型生成 + 薄运行时客户端；避免手拼 URL/query 导致的类型不同步 |
| 前端包管理 | **pnpm** | 仓库默认 |
| XLSX 生成 | **openpyxl** | 成熟稳定 |

**协议层面**：遵循 Agent-Native 设计指南（CLI + Skill 为默认，不引入 MCP）。CLI 是唯一 Agent 入口，`SKILL.md` 提供可发现性。

### 3.1 ORM / DTO 隔离约定

为避免持久化模型与 API schema 耦合，本项目强制执行：

- `src/asset_hub/models/` 下的 `table=True` SQLModel 类**只用于数据库映射**
- `src/asset_hub/api/schemas/` 下的 Pydantic `BaseModel` 定义所有请求/响应 DTO，**不继承** ORM 模型
- Service 层返回 domain 对象或 DTO，不直接把 ORM 模型泄漏到 FastAPI 路由或 CLI
- 聚合/批量查询优先使用 SQLAlchemy 2.x `select()` 风格，不依赖 SQLModel 的高层查询糖

这样未来若 SQLModel 演进停滞，迁 "SQLAlchemy 2.x + 纯 Pydantic" 只是删掉一层，无需重构业务逻辑。

## 4. 架构（三层分离）

```
┌──────────────────────┐   ┌──────────────────────┐
│  Web GUI (React/TS)  │   │  CLI (Python/Typer)  │
│    人类展示层         │   │    Agent 控制层       │
└───────────┬──────────┘   └──────────┬───────────┘
            │ HTTP (JSON)              │ in-process import
            └──────────┬───────────────┘
                       ▼
         ┌─────────────────────────────┐
         │  FastAPI 应用层 (HTTP 入口)  │
         └──────────────┬──────────────┘
                        ▼
         ┌─────────────────────────────┐
         │  Service 层 (纯业务逻辑)     │   ← 唯一事实
         │  asset / type / checkout /   │
         │  attachment / stats / export │
         └──────────────┬──────────────┘
                        ▼
         ┌─────────────────────────────┐
         │  Repository / SQLModel       │
         │  SQLite                      │
         │  + FS StorageAdapter (附件)  │
         └─────────────────────────────┘
```

**关键原则**：

- **CLI 不走 HTTP**：直接 `from asset_hub.services import asset_service`。优点：零序列化损失、无认证问题、失败时异常直达调用方
- **Service 层与存储解耦**：所有 service 依赖 Repository 接口，不依赖 SQLModel 具体类；所有附件 I/O 走 `StorageAdapter` 接口
- **API schema 自动同步**：Pydantic 模型既是 FastAPI 校验器，也通过 OpenAPI 导出给前端生成 TS 类型

## 5. 数据模型

### 5.1 通用字段（所有资产共享，Asset 表顶层）

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | UUID | 系统内部主键 |
| `asset_code` | string, unique | **内部编号**，默认自动生成（`<类型前缀>-<年>-<序号>`，如 `NB-2026-001`），可手改 |
| `serial_number` | string?, unique | **铭牌编码 / SN**（厂家刻印），用户填入，允许空，非空时组织内唯一 |
| `name` | string | 展示名，通常等于型号（如 `ThinkPad X1 Carbon Gen 11`） |
| `type_id` | FK → AssetType | 所属类型 |
| `status` | enum | `IN_USE` / `IDLE` / `MAINTENANCE` / `RETIRED` |
| `holder` | string? | 当前保管人，空 = 仓库/无 |
| `location` | string? | 当前位置 |
| `notes` | text? | 备注 |
| `custom_data` | JSON | 按类型的 `custom_fields` 填入的键值对 |
| `current_checkout_id` | FK? | 当前未归还的派发记录，`NULL` 表示无派发中 |
| `created_at` / `updated_at` | timestamp | 时间戳 |

### 5.2 其他实体

```
AssetType
├── id, name (e.g. "笔记本电脑"), description
└── custom_fields: JSON
    # [{key, label, type, required?, unique?, options?}]
    # type 支持: string | int | float | bool | enum | date | text

CheckoutRecord
├── id, asset_id
├── holder, location
├── checked_out_at, returned_at?  # returned_at 为空表示当前持有
├── checkout_note?, return_note?

Attachment
├── id, asset_id
├── kind: enum (photo | invoice | doc | other)
├── storage_path  # 相对路径，如 attachments/2026/04/<sha256>.jpg
├── sha256, size, mime_type, original_name
└── uploaded_at
```

### 5.3 设计权衡

- **自定义字段用 JSON 列**（`custom_data`）而非 EAV：SQLite/Postgres 均原生支持 JSON path 查询，此规模下 EAV 得不偿失
- **CheckoutRecord 独立表**：`Asset` 表只保存"当前"快照；历史可完整重放
- **`serial_number` 提升到顶层**：跨类型查询（"帮我找 SN 为 XYZ 的设备"）是刚需；对无铭牌的资产留空即可
- **附件元数据与文件分离**：DB 仅存路径和校验和；切换存储后端无需迁移数据库

### 5.4 类型字段示例：笔记本电脑

```json
[
  {"key": "brand",    "label": "品牌",       "type": "string", "required": true},
  {"key": "os",       "label": "操作系统",   "type": "enum",   "options": ["Windows", "macOS", "Linux"]},
  {"key": "cpu_arch", "label": "处理器架构", "type": "enum",   "options": ["x86_64", "arm64"]},
  {"key": "cpu",      "label": "处理器",     "type": "string"},
  {"key": "ram_gb",   "label": "内存(GB)",   "type": "int"}
]
```

## 6. CLI 设计

### 6.1 命令结构

遵循 `<工具> <资源> <操作>` 模式：

```bash
# 类型
asset-hub type define --from schema.json
asset-hub type list
asset-hub type show <id>

# 资产
asset-hub asset register --type laptop --name "ThinkPad X1" --sn "PF-xxx" \
          --holder "张三" --custom '{"brand":"Lenovo","os":"Windows"}'
asset-hub asset show <id-or-code>
asset-hub asset list [--type laptop] [--status IDLE] [--holder 张三] [--q 关键词]
asset-hub asset update <id> --set '{"location":"机房A"}'
asset-hub asset checkout <id> --to 张三 [--location 工位5] [--note "借用一周"]
asset-hub asset return <id> [--note "完好归还"]
asset-hub asset history <id>
asset-hub asset delete <id> [--dry-run]

# 附件
asset-hub attachment add <asset> --file photo.jpg --kind photo
asset-hub attachment list <asset>

# 导出
asset-hub export --format xlsx --out inventory.xlsx \
                 [--type laptop] [--status IN_USE] [--holder 张三]
```

### 6.2 全局约定

- `--json` 输出标准信封：

  ```json
  {
    "success": true,
    "data": { ... },
    "metadata": { "took_ms": 12, "count": 5 },
    "error": null
  }
  ```

- `--fields name,holder,status` 投影字段（节省 Agent 上下文）
- `--yes` 跳过所有交互确认（Agent 必备）
- `--no-interactive` 禁用 pager / 交互提示
- 破坏性操作（`delete`）强制支持 `--dry-run`

### 6.3 退出码

| 码 | 含义 |
|---|---|
| 0 | 成功 |
| 1 | 一般错误 |
| 2 | 用法/参数错误 |
| 3 | 资源不存在 |
| 10 | dry-run 预览（非错误，但表示未执行） |

### 6.4 SKILL.md

仓库根放置 `SKILL.md`，内容包含：

- asset-hub 能做什么的简述
- 典型工作流示例（照片登记、派发、归还、按条件导出）
- 命令速查
- **Gotchas 区块**（随实践持续增长）

## 7. Web GUI 设计

### 7.1 页面清单（v1）

| 页面 | 路径 | 关键能力 |
|---|---|---|
| 资产列表（首页） | `/` | TanStack Table；多维筛选（类型/状态/保管人/位置/关键词）；列显隐；排序；分页；导出按钮使用当前筛选 |
| 资产详情 | `/assets/:id` | 字段分组（通用/类型字段）；附件缩略图 + lightbox；流转时间线；派发/归还/编辑入口 |
| 登记表单 | `/assets/new` | 选择 type 后动态渲染 `custom_fields`；SN 查重；图片上传 |
| 编辑表单 | `/assets/:id/edit` | 复用登记表单组件 |
| 派发 / 归还对话框 | 浮层 | Shadcn Dialog，表单简洁 |
| 看板 | `/dashboard` | 4 张 Tremor 图表 |
| 类型一览 | `/types` | 只读展示类型与字段（v1 定义用 CLI） |

### 7.2 设计原则

严格遵循 `frontend-design` skill 的原则，**避免 AI 模板脸**：
- 配色、间距、字体、动效都要经过设计决策，不使用框架默认
- 状态色、空状态、错误态、加载态都有专门视觉处理
- 键盘可达性（快捷键、focus 管理）

### 7.3 前后端交互

- 前端由 `openapi-typescript` 从 FastAPI 的 `/openapi.json` 生成类型
- 所有 API 请求经过一个 `apiClient` 封装，统一处理 envelope
- 开发期 Vite 代理 `/api` → `:8000`；生产期 FastAPI `StaticFiles` 托管 `frontend/dist`

## 8. 可视化看板（v1）

**固定 4 张图**，不做可配置化，使用 **shadcn/ui charts（基于 Recharts）**：

| 图表 | 类型 | 数据 |
|---|---|---|
| 类型分布 | 甜甜圈 | `count by type` |
| 状态分布 | 堆叠条形图 | `count by status`（全局） |
| 按保管人 Top N | 横向条形图 | `count by holder`，N = 10 |
| 闲置时长 Top N | 列表式条形图 | 取 `status = IDLE` 的资产，按 `updated_at` 倒序取 10 |

后端提供单一端点 `GET /api/stats`，返回四段聚合数据。

## 9. 导出

- 后端 `GET /api/export?type=&status=&holder=&q=&format=csv|xlsx` 接收筛选参数
- CSV：Python stdlib `csv`
- XLSX：`openpyxl`，带列宽自适应、冻结首行、状态色条件格式
- CLI `asset-hub export` 复用同一 service 函数
- Web：列表页"导出"按钮把当前筛选状态序列化进 query string

## 10. 项目结构（monorepo）

```
asset-hub/
├── pyproject.toml              # uv 管理
├── uv.lock
├── README.md
├── SKILL.md
├── .env.example
│
├── src/asset_hub/
│   ├── cli/                    # Typer
│   │   ├── main.py
│   │   ├── asset.py / type.py / export.py / attachment.py
│   │   └── envelope.py
│   ├── api/                    # FastAPI
│   │   ├── app.py
│   │   ├── routers/
│   │   └── schemas/
│   ├── services/               # ★ 纯业务逻辑
│   │   ├── asset.py / type.py / checkout.py / attachment.py
│   │   ├── stats.py / export.py
│   ├── repositories/           # 接口 + SQLModel 实现
│   ├── storage/                # 附件存储
│   │   ├── base.py
│   │   └── local_fs.py
│   ├── models/                 # SQLModel 实体
│   ├── db.py                   # Engine/Session/迁移
│   └── config.py               # pydantic-settings
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── cli/
│
├── frontend/
│   ├── package.json            # pnpm
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── index.html
│   └── src/
│       ├── main.tsx / App.tsx
│       ├── routes/             # assets/ dashboard/ types/
│       ├── components/ui/      # shadcn
│       ├── api/                # openapi-typescript 类型 + openapi-fetch 客户端
│       ├── lib/
│       └── styles/
│
├── data/                       # 运行期，gitignored
│   ├── asset_hub.db
│   └── attachments/<yyyy>/<mm>/<sha256>.<ext>
│
├── docs/superpowers/specs/
└── scripts/
    ├── dev.sh                  # 并发启动 backend + frontend dev
    └── build.sh                # 前端构建 → 后端挂载
```

### 10.1 开发与运行

- 所有 Python 命令走 `uv run ...`
- 前端用 `pnpm`
- 开发：`./scripts/dev.sh` → FastAPI `:8000` + Vite `:5173`（代理 `/api` → `:8000`）
- 生产：`pnpm --dir frontend build` → `frontend/dist`，FastAPI 挂载为静态文件，单端口对外
- 部署形态：v1 为本地 `uv run uvicorn`；docker-compose 的 Dockerfile 在 M4 之后再补

## 11. 路线图

| 里程碑 | 版本 | 目标 | 主要产出 |
|---|---|---|---|
| **M1 · 骨架** | v0.1 | 可跑通的最小闭环 | 项目初始化；SQLModel 模型 + 首次迁移；service/repo 抽象；CLI `type define / asset register / list / show` 带 `--json`；FastAPI 最小端点；前端脚手架 |
| **M2 · 核心流程** | v0.5 | 资产管理真正可用 | checkout / return + history；附件上传（CLI + API + FS 存储）；Web 资产列表 / 详情 / 动态表单 / 派发归还对话框 |
| **M3 · 特性完整** | v1.0 | MVP 全量 | 看板 4 图 + `/api/stats`；CSV/XLSX 导出（前后端）；SKILL.md 完善；基础测试覆盖；README + 部署文档 |
| **M4 · UI 打磨** | v1.x | 达到 `frontend-design` 审美标准 | 配色/间距/字体/微动效；空状态、错误态、加载态的设计；键盘快捷键；响应式基础 |

## 12. 未决事项（供 Plan 阶段解决）

- `AssetType.custom_fields` 的 schema JSON 的严格校验规则（哪些 type 支持哪些属性）
- 自动编号的具体规则：类型前缀如何选取（从 type.name 推断 vs 类型自带 `code_prefix` 字段）
- 附件目录按日期分片（`yyyy/mm`）还是按资产 id 前缀分片
- 首次运行初始化策略（是否自动创建 `data/` 目录、是否内置几个常见类型模板）
- API 客户端在 Plan 阶段最终敲定：**openapi-fetch**（更轻）vs **@hey-api/openapi-ts**（客户端更完整、原生集成 TanStack Query）
- 测试策略细节（service 层单测 + CLI 输出断言 + 极简 API 集成测试）

## 13. 选型待观察项

以下项在 v1 按现有选型推进，但需在后续版本重新评估：

- **SQLModel 维护节奏**：若 2026 下半年仍无 minor feature release，考虑迁 SQLAlchemy 2.x + 独立 Pydantic schema。由于第 3.1 节的隔离约定，迁移代价可控
- **Tremor**：若推出 Radix/shadcn 原生版本，可再评估是否回迁（目前 shadcn charts 已足够）
- **openapi-fetch vs hey-api**：实操时择优，两者均与 openapi-typescript 生成的 schema 兼容
