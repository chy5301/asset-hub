---
name: asset-hub
description: |-
  小组实物资产管理工具（命令 asset-hub）的 Agent 入口，管理笔记本/显示器/GPU/工作站等硬件设备的登记、派发、归还、维修、退役全生命周期。
  在 asset-hub 项目里使用此 skill 当用户提到：登记/录入设备、把某台设备派给某人、归还设备、设备坏了/出现故障/送修/修不好/报废/退役/注销、把设备从某工位换到另一处（重新分配）、查询闲置/在用/故障设备、按保管人/类型/状态筛选列表、导出 CSV/XLSX、看板统计、AssetType 自定义字段（CPU/RAM/序列号等）、serve 子命令（start/stop/status/restart/logs/doctor）排障、在 Windows 上部署或升级 asset-hub，或在项目目录里直接调用 asset-hub 命令。即便用户用口语词（"借出"、"还回来"、"坏了"、"换工位"），只要语境是公司/小组内部实物设备管理就触发。
  不适用于：网页 image asset / 静态资源加载问题、金融资产、CSS asset bundling 等同名不同义场景。
  包含 6 态状态机（闲置/在用/送修/故障/退役/注销）、12 种 transition、JSON envelope 契约、CLI 命令速查、常见任务流。
---

# asset-hub

小组资产管理工具。Web GUI 面向作者本人，CLI 面向 AI Agent（即此文件的主消费者）。

## 何时用我

- 资产 CRUD（登记 / 查询 / 编辑 / 删除）
- 状态流转（12 种 transition）
- 类型管理（AssetType 自定义字段定义）
- 看板查询（4 段聚合统计：类型 / 状态 / 保管人 Top 10 / 闲置时长 Top 10）
- 数据导出（CSV / XLSX，通过 Web GUI / API 按筛选导出，CLI 不直接做 export）
- 服务生命周期（serve start/stop/status/restart/logs/doctor）

## 资产状态机（6 态）

| status | 中文文案 | 含义 | 可派发 | 列表默认显示 |
|---|---|---|---|---|
| `IDLE` | 闲置 | 在库可派发 | ✓ | ✓ |
| `IN_USE` | 在用 | 已派出（kind 区分组内/对外） | ✗ | ✓ |
| `MAINTENANCE` | 送修 | 维修中 | ✗ | ✓ |
| `BROKEN` | 故障 | 已发现故障，未送修 / 维修不可修（v2.0 新） | ✗ | ✓ |
| `RETIRED` | 退役 | 暂时退役（备件/转借/暂停服役，可复活） | ✗ | ✗（toggle） |
| `DISPOSED` | 注销 | 彻底处置（卖/捐/销毁，终态） | ✗ | ✗（toggle） |

## Transition（12 种）

| kind | 中文 | valid_from | to_status | holder_rule | location_rule |
|---|---|---|---|---|---|
| `CHECKOUT_INTERNAL` | 派发（组内） | IDLE | IN_USE | required | keep |
| `CHECKOUT_EXTERNAL` | 出借（对外） | IDLE | IN_USE | required | keep |
| `RETURN` | 归还 | IN_USE | IDLE | optional | keep |
| `SEND_TO_MAINTENANCE` | 送修 | IDLE / BROKEN | MAINTENANCE | keep | keep |
| `RECOVER_FROM_MAINTENANCE` | 维修完成 | MAINTENANCE | IDLE | keep | keep |
| `RETIRE` | 退役 | IDLE / MAINTENANCE / BROKEN | RETIRED | keep | keep |
| `REINSTATE` | 重新启用 | RETIRED | IDLE | keep | keep |
| `DISPOSE` | 注销 | RETIRED / MAINTENANCE / BROKEN | DISPOSED | forced_null | forced_null |
| `REASSIGN` | 重新分配（v2.0 合并 RELOCATE+TRANSFER_HOLDER） | ALL_BUT_DISPOSED | (self) | keep | keep |
| `REPORT_BROKEN` | 出现故障（v2.0 新） | IDLE / IN_USE | BROKEN | keep | keep |
| `DECLARE_UNREPAIRABLE` | 判定不可修复（v2.0 新） | MAINTENANCE | BROKEN | keep | keep |
| `DISMISS` | 故障解除（v2.0 新） | BROKEN | IDLE | keep | keep |

**规则约定**：
- `keep`：未传字段保留 asset 当前值；显式传 `""`（CLI）/`null`（API）清空
- `required`：必传非空
- `optional`：可传可不传；未传则字段最终为 null
- `forced_null`：service 强制清空（无视用户输入）
- `(self)`：to_status 等于 from_status（self-loop）

## CLI envelope 速查

成功响应：

```json
{ "success": true, "data": <任意>, "metadata": { "took_ms": 12, "count": 5 }, "error": null }
```

错误响应：

```json
{ "success": false, "data": null, "metadata": {}, "error": { "code": "<error_code>", "message": "<中文 detail>" } }
```

退出码：`0` 成功 / `1` 一般错误 / `2` 用法/参数错误 / `3` 资源不存在 / `10` dry-run 预览（非错误）。

## 命令速查

**资产 CRUD：**

```
asset-hub asset register --name <txt> --type-id <uuid> [--sn <txt>] [--holder <txt>] [--location <txt>] [--notes <txt>] [--custom <json>] [--acquired-at YYYY-MM-DD] [--json]
asset-hub asset list [--type-id <uuid>] [--status <s>] [--holder <txt>] [--q <txt>] [--include-retired/--no-include-retired] [--include-disposed/--no-include-disposed] [--sort <field>] [--order asc|desc] [--limit N] [--offset N] [--json]
asset-hub asset show <asset_id> [--json]
asset-hub asset update <asset_id> --set <json> [--json]
asset-hub asset delete <asset_id> [--yes] [--dry-run] [--json]
asset-hub asset history <asset_id> [--json]
```

**状态流转（平铺在 asset 下，11 种命令）：**

```
asset-hub asset checkout <asset_id> --to-holder <holder> [--kind internal|external] [--to-location <loc>] [--note <txt>] [--due-at <iso>] [--json]
asset-hub asset return <asset_id> [--to-holder <name>] [--to-location <loc>] [--note <txt>] [--json]
asset-hub asset send-to-maintenance <asset_id> [--to-holder <h>] [--to-location <loc>] [--note <txt>] [--json]
asset-hub asset recover <asset_id> [--to-holder <h>] [--to-location <loc>] [--note <txt>] [--json]
asset-hub asset retire <asset_id> [--to-holder <h>] [--to-location <loc>] [--note <txt>] [--yes] [--dry-run] [--json]
asset-hub asset reinstate <asset_id> [--to-holder <h>] [--to-location <loc>] [--note <txt>] [--json]
asset-hub asset dispose <asset_id> [--note <txt>] [--yes] [--dry-run] [--json]
asset-hub asset report-broken <asset_id> [--to-holder <h>] [--to-location <loc>] [--note <txt>] [--json]
asset-hub asset declare-unrepairable <asset_id> [--note <txt>] [--yes] [--dry-run] [--json]
asset-hub asset dismiss <asset_id> [--to-holder <h>] [--to-location <loc>] [--note <txt>] [--json]
asset-hub asset reassign <asset_id> [--to-holder <h>] [--to-location <loc>] [--note <txt>] [--json]
```

### asset reassign 用法

仅改持有人：     asset reassign <id> --to-holder 李四
仅改位置：       asset reassign <id> --to-location 仓库
同时改：         asset reassign <id> --to-holder 李四 --to-location 仓库

service 校验：必须传至少一项（否则 409 illegal_transition）

**类型管理：**

```
asset-hub type define [--name <txt>] [--prefix <2-4 大写字母>] [--description <txt>] [--fields <json>] [--from <json-file>] [--json]
asset-hub type list [--json]
asset-hub type show <type_id> [--json]
asset-hub type update <type_id> [--name <txt>] [--description <txt>] [--from <json-file>] [--dry-run] [--json]
asset-hub type delete <type_id> [--yes] [--dry-run] [--json]
```

**附件（仅 add / list，无 delete）：**

```
asset-hub attachment add <asset_id> --file <path> [--kind photo|invoice|doc|other] [--json]
asset-hub attachment list <asset_id> [--json]
```

**看板统计：**

```
asset-hub stats [--include-retired/--no-include-retired] [--include-disposed/--no-include-disposed] [--fields <type_distribution,status_distribution,holder_ranking,idle_top>] [--json]
```

**服务生命周期：**

```
asset-hub serve start [--mode dev|prod] [--skip-build] [--port N] [--frontend-port N] [--json]
asset-hub serve stop [--json]
asset-hub serve status [--no-probe] [--json]
asset-hub serve restart [--mode dev|prod] [--json]
asset-hub serve logs [--service backend|frontend|all] [--lines N] [--follow] [--json]
asset-hub serve doctor [--mode dev|prod] [--json]
```

## Gotcha

1. **破坏性命令需 --yes 跳过 prompt**：`asset retire/dispose/declare-unrepairable/delete` 默认互交确认；脚本场景必须传 `--yes`，否则挂起。
2. **keep rule 陷阱**：v2.0 多数 transition holder/location 是 `keep` 规则——未传字段**保留 asset 当前值**（非清空）。如要显式清空，传空字符串：`--to-holder ""`（CLI）或 `null`（API JSON）。
3. **REASSIGN 必改一项**：`asset reassign` 必须实际改变 holder 或 location；都不改（不传或传当前值）报 409 `illegal_transition`。
4. **CLI flag 全面 v2 标准化（vs v1.0 BC）**：v1 的 `--to`/`--receiver`/`--holder`/`--location` 全统一为 `--to-holder`/`--to-location`。脚本如有旧 flag 必报 typer usage error。
5. **declare-unrepairable vs retire**：DECLARE_UNREPAIRABLE 是"维修过程判定不可修"（MAINTENANCE → BROKEN）；RETIRE 是"主动下架"（多个起点）。两者均需 confirm，含 `--yes/--dry-run`。
6. **派出集 closes 通用化（v2.0）**：v1 中只有 `RETURN` 闭合 OPEN CHECKOUT；v2 中任何"从 IN_USE/BROKEN 走出去 IDLE/MAINTENANCE/etc"的 transition 都自动闭合。如 BROKEN → IDLE (DISMISS) 也会闭合最初的 CHECKOUT。
7. **DISPOSE 改名 → 注销**：v1 的"处置"在 v2 改为"注销"（CLI confirm phrase、UI label、export 文案全统一）。dispose phrase 现是 `"注销"`，旧脚本输入 `"处置"` 会失败。

## 详细参考

- 12 transition 完整规则（**何时读**：用户问 REASSIGN 与各新 kind 区别 / dialog 行为 / from-status 边界）：[references/transitions.md](./references/transitions.md)
- envelope error code 完整 inventory（**何时读**：解析 CLI error 遇到未知 code、调试 exit_code、需引用错误处理对照表）：[references/envelope.md](./references/envelope.md)
- 端到端任务流（**何时读**：用户给出"帮我登记 + 派发 + 归还"完整流程，或需要 `--json` 输出对照样本）：[references/workflows.md](./references/workflows.md)
- 部署 / serve doctor / 故障排查（**何时读**：`serve start` 失败、`serve doctor` 输出有 issue、用户问"在 Windows 怎么部署 / 怎么备份"）：[references/deploy.md](./references/deploy.md)
