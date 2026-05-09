---
name: asset-hub
description: |-
  小组资产管理工具（命令 asset-hub）的 Agent 入口。
  使用此 skill 当用户在 asset-hub 项目里提到资产登记 / 状态流转（派发、归还、送修、退役、处置）/ 列表筛选 / CSV/XLSX 导出 / 看板统计 / AssetType 自定义字段 / serve 子命令（start/stop/status/restart/logs/doctor）/ 在 Windows 部署 asset-hub / asset-hub 升级，或在项目目录里直接调用 asset-hub 命令。
  包含 5 态状态机（闲置中/使用中/维修中/已退役/已处置）、10 种 transition、JSON envelope 契约、CLI 命令速查、常见任务流。
---

# asset-hub

小组资产管理工具。Web GUI 面向作者本人，CLI 面向 AI Agent（即此文件的主消费者）。

## 何时用我

- 资产 CRUD（登记 / 查询 / 编辑 / 删除）
- 状态流转（10 种 transition）
- 类型管理（AssetType 自定义字段定义）
- 看板查询（4 段聚合统计：类型 / 状态 / 保管人 Top 10 / 闲置时长 Top 10）
- 数据导出（CSV / XLSX，通过 Web GUI / API 按筛选导出，CLI 不直接做 export）
- 服务生命周期（serve start/stop/status/restart/logs/doctor）

## 资产状态机（5 态）

| status | 中文文案 | 含义 | 可派发 | 列表默认显示 |
|---|---|---|---|---|
| `IDLE` | 闲置中 | 在库可派发 | ✓ | ✓ |
| `IN_USE` | 使用中 | 已派出（kind 区分组内/对外） | ✗ | ✓ |
| `MAINTENANCE` | 维修中 | 维修中，不可派发 | ✗ | ✓ |
| `RETIRED` | 已退役 | 暂时退役（备件/转借/暂停服役，可复活） | ✗ | ✗（toggle 显示） |
| `DISPOSED` | 已处置 | 彻底处置（卖/捐/销毁，终态） | ✗ | ✗（toggle 显示） |

## 10 种 transition

| kind | from → to | 必填字段 |
|---|---|---|
| `CHECKOUT_INTERNAL` | IDLE → IN_USE | `--to` |
| `CHECKOUT_EXTERNAL` | IDLE → IN_USE | `--to` |
| `RETURN` | IN_USE → IDLE | —（可选 `--receiver`, `--location`） |
| `SEND_TO_MAINTENANCE` | IDLE → MAINTENANCE | —（可选 `--holder`, `--location`） |
| `RECOVER_FROM_MAINTENANCE` | MAINTENANCE → IDLE | —（可选 `--holder`, `--location`） |
| `RETIRE` | IDLE / MAINTENANCE → RETIRED | —（可选 `--holder`, `--location`） |
| `REINSTATE` | RETIRED → IDLE | —（可选 `--holder`, `--location`） |
| `DISPOSE` | RETIRED / MAINTENANCE → DISPOSED | `--yes` 确认（终态） |
| `RELOCATE` | IDLE / IN_USE / MAINTENANCE / RETIRED → 同 status | `--to-location` |
| `TRANSFER_HOLDER` | IDLE / IN_USE / MAINTENANCE / RETIRED → 同 status | `--to-holder` |

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

**状态流转（平铺在 asset 下，9 种命令）：**

```
asset-hub asset checkout <asset_id> --to <holder> [--kind internal|external] [--location <loc>] [--note <txt>] [--due-at <iso>] [--json]
asset-hub asset return <asset_id> [--receiver <name>] [--location <loc>] [--note <txt>] [--json]
asset-hub asset send-to-maintenance <asset_id> [--holder <maint-contact>] [--location <loc>] [--note <txt>] [--json]
asset-hub asset recover <asset_id> [--holder <name>] [--location <loc>] [--note <txt>] [--json]
asset-hub asset retire <asset_id> [--holder <name>] [--location <loc>] [--note <txt>] [--yes] [--dry-run] [--json]
asset-hub asset reinstate <asset_id> [--holder <name>] [--location <loc>] [--note <txt>] [--json]
asset-hub asset dispose <asset_id> [--note <txt>] [--yes] [--dry-run] [--json]
asset-hub asset relocate <asset_id> --to-location <loc> [--note <txt>] [--json]
asset-hub asset transfer-holder <asset_id> --to-holder <holder> [--location <loc>] [--note <txt>] [--json]
```

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

## Gotchas

- **DISPOSED 是终态**：一旦设置不可回退。这是因为 DISPOSED 对应物理处置（卖 / 捐 / 销毁），与 RETIRED（暂时退役、可复活）严格区分。用户说"先放着以后可能用"→ 用 `asset retire`，不是 `asset dispose`。
- **DISPOSE 必须 from RETIRED / MAINTENANCE**：IDLE 不能直接 dispose，必须先 retire。这是为了让"误点处置"成本最小化——多一道门槛做二次确认。
- **归还后 holder/location 跟随 to_holder/to_location，不强制清空**：M3a 行为修订。`--receiver` 不传则资产归还后无 holder（无人值守仓库语义）；传了则归还接收人成为新 holder。
- **IN_USE → MAINTENANCE 直跳走两步**：CLI 会提示"将先记 RETURN 再 SEND_TO_MAINTENANCE"，service 写两条 record。这样 timeline 能真实反映"派发期间送修"的两步语义，不丢历史。
- **5 态文案 vs 枚举值严格区分**：UI 显示"闲置中/使用中/维修中/已退役/已处置"，API 与 CLI `--json` 输出 "IDLE/IN_USE/MAINTENANCE/RETIRED/DISPOSED"。`--json` 里看到 `"IN_USE"` 不是 bug。

## 详细参考

- 10 transition 完整规则（**何时读**：用户问 RELOCATE 与 TRANSFER_HOLDER 区别 / dialog 行为 / from-status 边界）：[references/transitions.md](./references/transitions.md)
- envelope error code 完整 inventory（**何时读**：解析 CLI error 遇到未知 code、调试 exit_code、需引用错误处理对照表）：[references/envelope.md](./references/envelope.md)
- 端到端任务流（**何时读**：用户给出"帮我登记 + 派发 + 归还"完整流程，或需要 `--json` 输出对照样本）：[references/workflows.md](./references/workflows.md)
- 部署 / serve doctor / 故障排查（**何时读**：`serve start` 失败、`serve doctor` 输出有 issue、用户问"在 Windows 怎么部署 / 怎么备份"）：[references/deploy.md](./references/deploy.md)
