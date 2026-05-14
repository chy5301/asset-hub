# transitions reference

> ⚠️ 与 `src/asset_hub/services/transition.py` + `src/asset_hub/api/routers/transitions.py` + `frontend/src/features/assets/detail/*-dialog.tsx` 同源约定 — 改一处必查另一处。

12 种 transition 完整规则。补充 SKILL.md 主体的 transition 速查表。

## from-status 矩阵（合法性）

| kind | from 合法 | to | 备注 |
|---|---|---|---|
| `CHECKOUT_INTERNAL` | IDLE | IN_USE | 组内派发 |
| `CHECKOUT_EXTERNAL` | IDLE | IN_USE | 向外出借 |
| `RETURN` | IN_USE | IDLE | kind 跟随对应 OPEN checkout；service 自动查最近 OPEN CHECKOUT_* 行写 closes_transition_id |
| `SEND_TO_MAINTENANCE` | IDLE / BROKEN | MAINTENANCE | 送修；IN_USE 期间送修走两步（先 RETURN 或 REPORT_BROKEN 再 SEND）；v2.0 起 BROKEN 可直接送修 |
| `RECOVER_FROM_MAINTENANCE` | MAINTENANCE | IDLE | 修好回库 |
| `RETIRE` | IDLE / MAINTENANCE / BROKEN | RETIRED | 暂时退役（可复活）；v2.0 起 BROKEN 可直接退役 |
| `REINSTATE` | RETIRED | IDLE | 仅 RETIRED → IDLE |
| `DISPOSE` | RETIRED / MAINTENANCE / BROKEN | DISPOSED | **IDLE 不可直 DISPOSE**（必先 RETIRE）；DISPOSED 是终态——一旦设置不可回退；v2.0 起 BROKEN 可直接注销；confirm phrase 改"注销" |
| `REASSIGN` | IDLE / IN_USE / MAINTENANCE / BROKEN / RETIRED → 同 status | 同 status | 合并 v1 RELOCATE + TRANSFER_HOLDER；holder 或 location 至少改一项；DISPOSED 排除 |
| `REPORT_BROKEN` | IDLE / IN_USE | BROKEN | 出现故障（v2.0 新）；IN_USE → BROKEN 时不闭合 OPEN CHECKOUT（派出延续语义） |
| `DECLARE_UNREPAIRABLE` | MAINTENANCE | BROKEN | 维修过程判定不可修（v2.0 新） |
| `DISMISS` | BROKEN | IDLE | 故障解除/自愈（v2.0 新）；走通用化 closes 逻辑自动闭合 OPEN CHECKOUT |

## 必填字段（按 kind）

| kind | 必填（service 参数名） | CLI flag | 可选 |
|---|---|---|---|
| `CHECKOUT_INTERNAL` / `CHECKOUT_EXTERNAL` | `to_holder` | `--to-holder <holder>`（`asset checkout`） | `to_location` (`--to-location`), `due_at` (`--due-at`), `note` (`--note`) |
| `RETURN` | （无必填） | — | `to_holder` (`--to-holder`), `to_location` (`--to-location`), `note` (`--note`)（不传则字段保持 keep 语义） |
| `SEND_TO_MAINTENANCE` | （无必填） | — | `to_holder` (`--to-holder`), `to_location` (`--to-location`), `note` (`--note`) |
| `RECOVER_FROM_MAINTENANCE` | （无必填） | — | `to_holder` (`--to-holder`), `to_location` (`--to-location`), `note` (`--note`) |
| `RETIRE` | （无必填） | — | `to_holder` (`--to-holder`), `to_location` (`--to-location`), `note` (`--note`) |
| `REINSTATE` | （无必填） | — | `to_holder` (`--to-holder`), `to_location` (`--to-location`), `note` (`--note`) |
| `DISPOSE` | （无 service 必填；CLI 有 `--yes` 跳过确认 prompt） | `--yes`（跳过 CLI prompt）| `note` (`--note`) |
| `REASSIGN` | `to_holder` 或 `to_location`（至少一项） | `--to-holder <h>` 和/或 `--to-location <loc>` | `note` (`--note`) |
| `REPORT_BROKEN` | （无必填） | — | `to_holder` (`--to-holder`), `to_location` (`--to-location`), `note` (`--note`) |
| `DECLARE_UNREPAIRABLE` | （无 service 必填；CLI 有 `--yes` 跳过确认 prompt） | `--yes`（跳过 CLI prompt）| `note` (`--note`) |
| `DISMISS` | （无必填） | — | `to_holder` (`--to-holder`), `to_location` (`--to-location`), `note` (`--note`) |

> **注意**：`dispose` / `declare-unrepairable` CLI 没有 `--confirm 注销` 参数。输入"注销"解锁是前端 GUI 的 AlertDialog 行为，CLI 唯一的确认跳过方式是 `--yes`。

## CLI 命令字面量

```bash
# 平铺命令（无 'asset transition' 子组）
asset checkout <id> --to-holder <holder> [--kind internal|external] [--to-location --note --due-at --json]
asset return <id> [--to-holder --to-location --note --json]
asset send-to-maintenance <id> [--to-holder --to-location --note --json]
asset recover <id> [--to-holder --to-location --note --json]
asset retire <id> [--to-holder --to-location --note --yes --dry-run --json]
asset reinstate <id> [--to-holder --to-location --note --json]
asset dispose <id> [--note --yes --dry-run --json]
asset reassign <id> [--to-holder <h>] [--to-location <loc>] [--note --json]
asset report-broken <id> [--to-holder --to-location --note --json]
asset declare-unrepairable <id> [--note --yes --dry-run --json]
asset dismiss <id> [--to-holder --to-location --note --json]
```

## Dialog 行为（前端 7 dialog）

| dialog 文件 | 覆盖 kind |
|---|---|
| `checkout-dialog.tsx` | CHECKOUT_INTERNAL / CHECKOUT_EXTERNAL |
| `return-dialog.tsx` | RETURN |
| `simple-transition-dialog.tsx` | SEND_TO_MAINTENANCE / RECOVER_FROM_MAINTENANCE / REINSTATE / REPORT_BROKEN / DISMISS |
| `retire-alert-dialog.tsx` | RETIRE |
| `dispose-alert-dialog.tsx` | DISPOSE（confirm phrase 是"注销"） |
| `reassign-dialog.tsx` | REASSIGN（持有人 + 位置同时改的单一入口） |
| `declare-unrepairable-alert-dialog.tsx` | DECLARE_UNREPAIRABLE |

## Service 行为

- `record_transition(asset_id, kind, *, to_holder=_UNSET, to_location=_UNSET, note=None, due_at=None)` 是唯一入口
- service 内 `validate_transition(current_status, kind, to_holder, to_location)` 校验 from-status + 必填字段
- 违法 → `IllegalTransitionError(detail)` → router 409 Conflict / CLI exit 1 + `error.code = "illegal_transition"`
- 写入 `state_transition_records` 表 + 反规范化更新 `Asset.status` / `Asset.holder` / `Asset.location`
- **keep rule**：`to_holder/_UNSET` 时保留 asset 当前值；显式传 `None`/`""` 清空
- **派出集 closes 通用化（v2.0）**：任何从 `{IN_USE, BROKEN}` 走出的 transition 自动闭合最近 OPEN CHECKOUT；`RETURN` 强约束（找不到 OPEN CHECKOUT 则报错）；其他 kind finds_id = None 也合法
- REASSIGN 必改一项校验：holder 或 location 至少一个实际变化，否则报 `illegal_transition`

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

> **HTTP/JSON 约定**：JSON 体无 key → 视为未传（service 收 `_UNSET`）→ `keep` 行为；JSON 体 `{"to_holder": null}` → 视为显式 null → 清空。
