# asset-hub

> 小组资产管理工具。双接口：Web GUI 面向人类，CLI 面向 AI Agent。

## 核心能力

- **资产 CRUD** + 顶层 `model` 型号字段 + 类型驱动的自定义字段（string / int / float / bool / enum / multi_enum / date / text / url）
- **状态机**：6 态（闲置 / 在用 / 送修 / 故障 / 退役 / 注销）
- **12 种 transition**：派发（组内/外借）/ 归还 / 送修 / 维修完成 / 退役 / 重新启用 / 注销 / 重新分配（合并位置+保管人）/ 出现故障 / 故障报废 / 故障解除
- **看板**：4 段聚合（类型分布 / 状态分布 / 保管人 Top 10 / 闲置时长 Top 10）
- **导出**：CSV / XLSX，按当前筛选透传，走 Web GUI 或 HTTP API
- **附件管理**：照片 / 发票，CLI + Web 都可上传
- **服务生命周期管理**：`serve start / stop / status / restart / logs / doctor`

## 技术栈

| 层 | 选型 |
|---|---|
| 后端 | Python 3.12+ · FastAPI · SQLModel · SQLite · Typer · Alembic · openpyxl |
| 前端 | React 19 · Vite · TanStack Router · TanStack Table · TanStack Query · RHF + Zod · Tailwind v4 · shadcn/ui · Recharts |
| 测试 | pytest（unit / api / cli 三层）· vitest（unit / hooks / components）· playwright（e2e CI） |
| 工具链 | uv · pnpm · ruff · openapi-typescript / openapi-fetch |

## 架构

```
Web GUI (React) ──HTTP──┐
                        ├──► FastAPI ──► Service 层（唯一事实）──► Repository / SQLModel / FS
CLI (Typer) ────import──┘
```

CLI 直接 `from asset_hub.services import ...` 调用 service 层，**不**通过 HTTP 调自己的 API。

## 快速开始

```bash
# 前置：uv / pnpm / Python 3.12+ / Node 20+
uv sync
pnpm --dir frontend install
cp .env.example .env
uv run alembic upgrade head

# dev 模式（前后端并发，Vite 代理 /api → :8000）
uv run asset-hub serve start --mode dev
# 访问 http://127.0.0.1:5173

# prod 模式（自动 build 前端 + 单端口 :8000）
uv run asset-hub serve start --mode prod
# 访问 http://127.0.0.1:8000
```

## CLI 示例（v1.0 GA 命令）

```bash
# 定义类型
uv run asset-hub type define --from examples/types/laptop.json --json

# 登记资产（不含照片）
uv run asset-hub asset register \
    --name "李四开发本" \
    --type-id <uuid> --sn "PF-1234" \
    --model "ThinkPad X1 Carbon Gen 9" \
    --custom '{"brand":"Lenovo","ram_gb":16}' --json

# 单独上传照片附件（登记后）
uv run asset-hub attachment add <asset_id> --file ./photo.jpg --kind photo --json

# 状态流转 — 派发
uv run asset-hub asset checkout <asset_id> --to-holder "张三" --kind internal --to-location "北京办公室" --json

# 状态流转 — 归还
uv run asset-hub asset return <asset_id> --to-holder "李四" --to-location "上海仓库" --json

# 列表 + 筛选
uv run asset-hub asset list --status IDLE --json

# 看板统计
uv run asset-hub stats --json

# 导出（走 HTTP API，CLI 无 export 命令）
curl -OJ "http://localhost:8000/api/export?format=xlsx&status=IDLE"

# 诊断环境
uv run asset-hub serve doctor --json
```

## 路线图

| 里程碑 | 目标 | 状态 |
|---|---|---|
| **M1 · 骨架** | service/repo 抽象、CLI CRUD、FastAPI 端点、前端脚手架 | ✅ 已完成 |
| **M2 · 核心流程 + 视觉收尾** | checkout/return/history、附件、Web 列表 + 详情 + 动态表单、视觉打磨 | ✅ 已完成 |
| **M3a · 状态机基建** | 5 态 + 10 transition + StateTransitionRecord + 7 dialog | ✅ 已完成 |
| **M3b · 看板 + /api/stats** | 4 张图表 + ChartTokenProvider | ✅ 已完成 |
| **M3c · CSV/XLSX 导出** | /api/export + ExportButton + 5 态色条件格式 | ✅ 已完成 |
| **M3d · timeline 视觉重构** | Group rail + 月份分段 + 派出类型染色 + 超长派发预警 | ✅ 已完成 |
| **M3e · v1.0 GA 收口** | SKILL.md + envelope 统一 + serve doctor + Windows 部署 + e2e CI | ✅ 已完成 |
| **v2.0 · 状态机扩展 + Agent-native + model 字段** | 6 态（加 BROKEN）+ 12 transition + `keep` rule + flag 标准化 + envelope 深化 + `--help-json` + `--fields` + Asset.model 顶层字段 + sn sortable 顺修 | ✅ 已完成 2026-05-13 |
| **M4 · UI 打磨** | 配色 / 间距 / 动效达 frontend-design 审美标准；A3 dialog 合并；§S/§U/§W | ⏳ 规划中 |
| **M5 · People 实体化** | holder/location 实体化 + 重名/改名管理 | ⏳ 规划中 |

## 文档

- AI Agent 入口：[SKILL.md](./SKILL.md)（含 6 态 + 12 transition + envelope + 命令速查 + 任务流）
- 部署指南：[docs/deployment.md](./docs/deployment.md)
- v1.0 升级指南：[docs/superpowers/release-notes-v1.0.md](./docs/superpowers/release-notes-v1.0.md)
- v2.0 升级指南：[docs/superpowers/release-notes-v2.0.md](./docs/superpowers/release-notes-v2.0.md)
- 设计文档：[docs/superpowers/specs/](./docs/superpowers/specs/)
