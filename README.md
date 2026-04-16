# asset-hub

小组资产管理工具。双接口：Web GUI 面向人类，CLI 面向 AI Agent。

## 定位

聚合式资产管理中心，管理小组内的各类资产：设备、服务器、计算机、硬盘、显卡等。v1 明确只服务两类使用者：

- **单一人类用户**通过 Web GUI 维护资产
- **该用户的 AI Agent**（Claude Code）通过 CLI 完成登记、派发、归还、查询、导出

## 核心能力

- **双接口访问**
  - Web GUI（React + Vite + TanStack Router + Tailwind + shadcn/ui）
  - Agent CLI（Typer），`--json` 输出统一信封，Agent 直接可用
- **类型驱动的字段模型**：每类资产可定义各自的自定义字段，支持 string/int/float/bool/enum/date/text
- **可视化看板**（规划中）：资产状态、分布、使用情况的图形化展示
- **表格导出**（规划中）：CSV / XLSX，按当前筛选条件导出

## 技术栈

| 层 | 选型 |
|---|---|
| 后端 | Python 3.12 · FastAPI · SQLModel · SQLite · Typer |
| 前端 | React · Vite · TanStack Router · Tailwind · shadcn/ui |
| 测试 | pytest（service/CLI/API 三层） |
| 工具链 | uv · pnpm · ruff |

## 架构

```
Web GUI (React) ──HTTP──┐
                        ├──► FastAPI ──► Service 层（唯一事实）──► Repository/SQLModel/FS
CLI (Typer) ────import──┘
```

CLI 直接 `from asset_hub.services import ...` 调用 service 层，**不**通过 HTTP 调自己的 API。

## 开发

前置：`uv`、`pnpm`、Python 3.12+

```bash
# 安装依赖
uv sync
pnpm --dir frontend install

# 运行测试
uv run pytest

# 启动开发环境（并发后端 + 前端）
./scripts/dev.sh
```

## CLI 示例

```bash
# 定义类型
uv run asset-hub type define --from examples/types/laptop.json --json

# 登记资产
uv run asset-hub asset register --name "ThinkPad X1 Carbon" \
    --type-id <uuid> --sn "PF-xxx" \
    --custom '{"brand":"Lenovo","os":"Windows","ram_gb":16}' --json

# 列出
uv run asset-hub asset list --json
```

## 路线图

| 里程碑 | 目标 | 状态 |
|---|---|---|
| **M1 · 骨架** | service/repo 抽象、CLI CRUD、FastAPI 端点、前端脚手架 | ✅ 已完成 |
| **M2 · 核心流程** | checkout/return/history、附件、Web 列表+详情+动态表单 | ⏳ 规划中 |
| **M3 · 特性完整** | 看板 4 图、CSV/XLSX 导出、SKILL.md、测试覆盖 | ⏳ 规划中 |
| **M4 · UI 打磨** | 配色/间距/动效达到 frontend-design 审美标准 | ⏳ 规划中 |

## 设计文档

完整设计见 [docs/superpowers/specs/2026-04-15-asset-hub-design.md](docs/superpowers/specs/2026-04-15-asset-hub-design.md)。
