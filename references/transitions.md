# transitions reference

> ⚠️ 与 `src/asset_hub/services/transition.py` + `src/asset_hub/api/routers/transitions.py` + `frontend/src/features/assets/detail/*-dialog.tsx` 同源约定 — 改一处必查另一处。

10 种 transition 完整规则。补充 SKILL.md 主体的 transition 速查表。

## from-status 矩阵（合法性）

| kind | from 合法 | to | 备注 |
|---|---|---|---|
| `CHECKOUT_INTERNAL` | IDLE | IN_USE | 组内派发 |
| `CHECKOUT_EXTERNAL` | IDLE | IN_USE | 向外出借 |
| `RETURN` | IN_USE | IDLE | kind 跟随对应 OPEN checkout；service 自动查最近 OPEN CHECKOUT_* 行写 closes_transition_id |
| `SEND_TO_MAINTENANCE` | IDLE | MAINTENANCE | 送修；IN_USE 期间送修走两步（先 RETURN 再 SEND） |
| `RECOVER_FROM_MAINTENANCE` | MAINTENANCE | IDLE | 修好回库 |
| `RETIRE` | IDLE / MAINTENANCE | RETIRED | 暂时退役（可复活） |
| `REINSTATE` | RETIRED | IDLE | 仅 RETIRED → IDLE |
| `DISPOSE` | RETIRED / MAINTENANCE | DISPOSED | **IDLE 不可直 DISPOSE**（必先 RETIRE）；DISPOSED 是终态——一旦设置不可回退，因为它对应物理处置（卖/捐/销毁） |
| `RELOCATE` | IDLE / IN_USE / MAINTENANCE / RETIRED → 同 status | 同 status | 仅 location 变；DISPOSED 排除 |
| `TRANSFER_HOLDER` | IDLE / IN_USE / MAINTENANCE / RETIRED → 同 status | 同 status | holder（± location）变；DISPOSED 排除 |

## 必填字段（按 kind）

| kind | 必填（service 参数名） | CLI flag | 可选 |
|---|---|---|---|
| `CHECKOUT_INTERNAL` / `CHECKOUT_EXTERNAL` | `to_holder`, `to_location` | `--to <holder>`（`asset checkout`），`--location` | `due_at` (`--due-at`), `note` (`--note`) |
| `RETURN` | （无必填） | — | `to_holder` (`--receiver`), `to_location` (`--location`), `note` (`--note`)（不传则 holder → NULL，表示无人值守归还） |
| `SEND_TO_MAINTENANCE` | （无必填） | — | `to_holder` (`--holder`), `to_location` (`--location`), `note` (`--note`) |
| `RECOVER_FROM_MAINTENANCE` | （无必填） | — | `to_holder` (`--holder`), `to_location` (`--location`), `note` (`--note`) |
| `RETIRE` | （无必填） | — | `to_holder` (`--holder`), `to_location` (`--location`), `note` (`--note`) |
| `REINSTATE` | （无必填） | — | `to_holder` (`--holder`), `to_location` (`--location`), `note` (`--note`) |
| `DISPOSE` | （无 service 必填；CLI 有 `--yes` 跳过确认 prompt） | `--yes`（跳过 CLI prompt）| `note` (`--note`) |
| `RELOCATE` | `to_location` | `--to-location <loc>` | `note` (`--note`) |
| `TRANSFER_HOLDER` | `to_holder` | `--to-holder <h>` | `to_location` (`--location`), `note` (`--note`) |

> **注意**：`dispose` CLI 没有 `--confirm 处置` 参数。输入"处置"解锁是前端 GUI 的 AlertDialog 行为，CLI 唯一的确认跳过方式是 `--yes`。

## CLI 命令字面量

```bash
# 平铺命令（无 'asset transition' 子组）
asset checkout <id> --to <holder> [--kind internal|external] [--location --note --due-at --json]
asset return <id> [--receiver --location --note --json]
asset send-to-maintenance <id> [--holder --location --note --json]
asset recover <id> [--holder --location --note --json]
asset retire <id> [--holder --location --note --yes --dry-run --json]
asset reinstate <id> [--holder --location --note --json]
asset dispose <id> [--note --yes --dry-run --json]
asset relocate <id> --to-location <loc> [--note --json]
asset transfer-holder <id> --to-holder <h> [--location --note --json]
```

## Dialog 行为（前端 7 dialog）

| dialog 文件 | 覆盖 kind |
|---|---|
| `checkout-dialog.tsx` | CHECKOUT_INTERNAL / CHECKOUT_EXTERNAL（kind 单选 + 派发对象 / 位置 / 期望归还） |
| `return-dialog.tsx` | RETURN（归还接收人 / 归还位置 可选） |
| `simple-transition-dialog.tsx` | SEND_TO_MAINTENANCE / RECOVER_FROM_MAINTENANCE / REINSTATE（共用） |
| `retire-alert-dialog.tsx` | RETIRE（AlertDialog 二次确认） |
| `dispose-alert-dialog.tsx` | DISPOSE（AlertDialog + 输 "处置" 解锁，这是 GUI 行为；CLI 无此输入） |
| `relocate-dialog.tsx` | RELOCATE |
| `transfer-holder-dialog.tsx` | TRANSFER_HOLDER |

## Service 行为

- `record_transition(asset_id, kind, *, to_holder=None, to_location=None, note=None, due_at=None)` 是唯一入口
- service 内 `validate_transition(current_status, kind, to_holder, to_location)` 校验 from-status + 必填字段
- 违法 → `IllegalTransitionError(detail)` → router 409 Conflict / CLI exit 1 + `error.code = "illegal_transition"`
- 写入 `state_transition_records` 表 + 反规范化更新 `Asset.status` / `Asset.holder` / `Asset.location`
- RETURN 自动找最近 OPEN CHECKOUT_* 行，写 `closes_transition_id` 关闭闭环
- IN_USE → MAINTENANCE 直跳：service 不接受；需先 RETURN 再 SEND_TO_MAINTENANCE（前端 dialog 拆两步）

## REST 端点

`POST /api/assets/{asset_id}/transitions`：

```json
{
  "kind": "CHECKOUT_INTERNAL",
  "to_holder": "张三",
  "to_location": "北京办公室",
  "due_at": "2026-06-01T00:00:00Z",
  "note": "项目 X"
}
```

响应：刚创建的 `StateTransitionRecord` 行（含 `id` / `from_status` / `to_status` / `closes_transition_id` 等）。
