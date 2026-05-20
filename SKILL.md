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
| `BROKEN` | 故障 | 已发现故障，未送修 / 维修不可修 | ✗ | ✓ |
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
| `REASSIGN` | 重新分配（持有人 + 位置同时改的单一入口） | ALL_BUT_DISPOSED | (self) | keep | keep |
| `REPORT_BROKEN` | 出现故障 | IDLE / IN_USE | BROKEN | keep | keep |
| `DECLARE_UNREPAIRABLE` | 故障报废 | MAINTENANCE | BROKEN | keep | keep |
| `DISMISS` | 故障解除 | BROKEN | IDLE | keep | keep |

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

## Asset 顶层公共字段

所有 AssetType 共享的字段，由 `Asset` 模型直接承载——**不要**在 `AssetType.custom_fields` 里重复定义同名 key，否则顶层 vs custom 两边各存一份导致数据漂移。

| 字段 | 类型 | register flag | 说明 |
|---|---|---|---|
| `name` | str（必填）| `--name` | 资产实例名（自定义代号，与厂家型号无关） |
| `type_id` | UUID（必填）| `--type-id` | 关联 AssetType |
| `serial_number` | str / null | `--sn` | 厂家 SN，**unique index** |
| `brand` | str / null | `--brand` | 品牌（CL-1 v2.1 拆为顶层列） |
| `model` | str / null | `--model` | 厂家型号（v2.0 PR-3 拆为顶层列） |
| `holder` | str / null | `--holder` | 保管人。register 时可直传（"IDLE + 在库由 X 保管"语义）；由 checkout transition 写入则表达"X 正在使用"。两种语义都合法，按现实情况选 |
| `location` | str / null | `--location` | 物理位置 |
| `notes` | str / null | `--notes` | 备注自由文本 |
| `acquired_at` | date / null | `--acquired-at` | 入库日期 ISO `YYYY-MM-DD` |
| `custom_data` | dict | `--custom` | 类型特有规格，结构由 AssetType.custom_fields 定义 |
| `asset_code` | str | （服务生成 `{prefix}-{seq:03d}`，不可传） | 资产编号 |
| `status` | enum | （服务默认 IDLE，**只能**经 transition 改） | 状态 |

**设计 type 时的边界**：`custom_fields` 只放**类型特有规格**——笔记本的 `cpu` / `ram_gb` / `os_family`、显示器的 `resolution` / `panel_type`、GPU 的 `vram_gb`。涉及上表任意字段时走顶层 flag，不要进 `custom_fields`。

## 命令速查

**资产 CRUD：**

```
asset-hub asset register --name <txt> --type-id <uuid> [--sn <txt>] [--model <txt>] [--holder <txt>] [--location <txt>] [--notes <txt>] [--custom <json>] [--acquired-at YYYY-MM-DD] [--json]
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
asset-hub asset undo <asset_id> [--dry-run] [--json]    # 撤销最后一条流转（物理删除元操作）
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

`serve doctor` 含 `port_owner` 检测项（v2.2.1+）：PID 文件记 uv 父进程，端口实际由 python 子进程绑定；doctor 通过祖先链比对自动识别 uv 父子场景，不再误报 `external_port_owner`。详见 [references/deploy.md](./references/deploy.md)。

## Gotcha

1. **破坏性命令需 --yes 跳过 prompt**：`asset retire/dispose/declare-unrepairable/delete` 默认互交确认；脚本场景必须传 `--yes`，否则挂起。
2. **keep rule 陷阱**：多数 transition 的 holder/location 是 `keep` 规则——未传字段**保留 asset 当前值**（非清空）。如要显式清空，传空字符串：`--to-holder ""`（CLI）或 `null`（API JSON）。
3. **REASSIGN 必改一项**：`asset reassign` 必须实际改变 holder 或 location；都不改（不传或传当前值）报 409 `illegal_transition`。
4. **CLI flag 命名**：所有 transition 命令的目标字段统一为 `--to-holder` / `--to-location`。旧脚本若仍用 `--to` / `--receiver` / `--holder` / `--location`（v1 残留命名）必报 typer usage error。
5. **declare-unrepairable vs retire**：DECLARE_UNREPAIRABLE 是"维修过程判定不可修"（MAINTENANCE → BROKEN）；RETIRE 是"主动下架"（多个起点）。两者均需 confirm，含 `--yes/--dry-run`。
6. **派出集 closes 通用化**：任何从 `{IN_USE, BROKEN}` 走出到 `{IN_USE, BROKEN}` 之外的 transition 都自动闭合最近 OPEN CHECKOUT。即不只 RETURN，BROKEN → IDLE (DISMISS) / IN_USE → MAINTENANCE 等都会闭合最初的 CHECKOUT。
7. **DISPOSE 中文术语是"注销"**：CLI confirm phrase、UI label、export 文案统一为"注销"。前端 AlertDialog 解锁短语是 `"注销"`，旧脚本若硬编码 `"处置"` 会失败（CLI 唯一跳过确认的方式是 `--yes`）。
8. **顶层字段 vs custom_fields 边界**：`custom_fields` **只放类型特有规格**（`cpu` / `ram_gb` / `os_family` 等），**不要**重复定义 Asset 顶层字段（`name` / `brand` / `model` / `serial_number` / `holder` / `location` / `notes` / `acquired_at`）。重复定义会造成数据漂移：顶层一份 + custom 一份谁是真值不明。设计 AssetType 前先对照上方"Asset 顶层公共字段"段。

   **v2.1+** 起 AssetType `custom_fields[].key` 已强制校验 reserved 全集 16 项：顶层字段 9 个（`asset_code` / `serial_number` / `name` / `model` / `brand` / `holder` / `location` / `notes` / `acquired_at`）+ CLI 别名 `sn` + 系统/关系字段 6 个（`type` / `type_name` / `type_id` / `status` / `id` / `custom_data`）。违规 `create_type` / `update_type` 会直接 `ValidationError`。**对现有 AssetType 含 reserved key 重名 custom_field 零破坏**（仅 future create/update 拒绝），但建议手动从 type 中删除避免双输入框 UI 怪状。
9. **holder / location 必须由用户明确指定，避免静默缺省 / 推断 / 复用**：登记或流转设备涉及 `holder` 或 `location` 字段时（包括 `register --holder` / `--location`，与所有 transition 的 `--to-holder` / `--to-location`），必须**先向用户确认**。**避免**三种推断模式：(a) 静默不传 → 字段为 null；(b) 从国资资产卡的"负责人"、铭牌、照片背景里抓字段；(c) 复用上一台同型号 / 同批次设备的 holder。其他规格字段（型号 / SN / CPU / RAM 等）正常从命令/照片自动组装；唯独 `holder` 和 `location` 例外——它们是"谁现在拿着这台设备"的现实世界状态，不能静默替用户决策。
10. **设计 AssetType 前先 `type list --json` 查实际类型**：新建或扩展 `AssetType` 时，**第一步**是 `uv run asset-hub type list --json`，读完现有类型的 `custom_fields` 再动笔——让新类型的字段命名（`brand` 不要写成 `manufacturer`）、required 策略、`help` / `placeholder` 风格、enum vs string 选择、`unit` / `min` / `max` 标注与现有类型对齐。`examples/types/*.json` 是写文档时的快照，会跟数据库实际类型漂移，**只在**实际库里没有同类资产时作补充参考。AssetType 是长期消费的契约，字段风格不一致会让后续聚合 / 导出被字段差异坑。
11. **录入设备时必须问清初始 status**：register 默认 status=IDLE 且只能经 transition 改；用户若未明确"这台是闲置 / 在用 / 送修 / 故障 / 退役"，**先问再录**，再决定操作链——单独 `register`（IDLE 在库）或 `register` 后跟一个 transition（checkout / send-to-maintenance / report-broken / retire）。**避免**两种推断：(a) 用户没说就默认 IDLE 静默走过；(b) 看 `--holder` 有值就推断 IN_USE。本次踩坑就是后者——"归 X 保管"被自动翻译成 register+checkout，把闲置库存变成"占用中"，破坏 IDLE/IN_USE 看板统计与"派出集 closes 通用化"（Gotcha #6）的事件链。

## 常见任务流

### 撤销最后一条流转记录（手滑回退）

```bash
# 不确定要撤哪条 → 先预览
asset undo <asset_id> --dry-run --json   # exit 10

# 确认无误，执行
asset undo <asset_id> --json             # exit 0；data 是被删的 transition
```

约束：
- 只能撤"最后一条"（按 created_at desc），中间记录无法跳删
- 没有任何 transition 时报 `state_conflict`（exit 1）
- DISPOSE 也可撤销（v1 单一用户工具，无合规约束）
- 物理删除、零 DB 脚印；运行日志（`serve logs`）会留一行 `undo transition ...` 供事后追溯

## 详细参考

- 12 transition 完整规则（**何时读**：用户问 REASSIGN 与各 kind 边界、dialog 行为、from-status 矩阵）：[references/transitions.md](./references/transitions.md)
- envelope error code 完整 inventory（**何时读**：解析 CLI error 遇到未知 code、调试 exit_code、需引用错误处理对照表）：[references/envelope.md](./references/envelope.md)
- 端到端任务流（**何时读**：用户给出"帮我登记 + 派发 + 归还"完整流程，或需要 `--json` 输出对照样本）：[references/workflows.md](./references/workflows.md)
- 部署 / serve doctor / 故障排查（**何时读**：`serve start` 失败、`serve doctor` 输出有 issue、用户问"在 Windows 怎么部署 / 怎么备份"）：[references/deploy.md](./references/deploy.md)
