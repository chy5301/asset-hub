# issue #24 — asset undo 命令设计

> 闭环 GitHub issue [#24](https://github.com/chy5301/asset-hub/issues/24)。新增 `asset-hub asset undo <asset-id>` 命令，物理删除该资产的最后一条 transition 并把 asset 三字段（status / holder / location）回退到该 transition 的 `from_*` 值。

## 1. 背景与动机

CLI 用户（人类或 Agent）执行了错误流转后，目前只能用反向 transition 补偿（如 `return` 反 `checkout`、`recover` 反 `send-to-maintenance`），结果：

- 历史里多一对脚印；
- 语义错位——"我没想派发，只是手滑了"，不是"派出后又归还"；
- 当反向 transition 不存在时（如 `dispose` 是终态）完全无法救回。

目标：提供单一元操作 `undo`，无痕回退最后一条 transition，零状态机污染。

## 2. 范围

**做：**

- `services.transition.TransitionService.undo_last_transition(asset_id)`
- `repositories.state_transition.TransitionRepository.find_last(asset_id)` + `delete(record)`
- CLI 命令 `asset-hub asset undo <asset-id> [--dry-run] [--json] [--fields ...]`
- TDD：unit（service）+ cli 两层测试
- 文档：`SKILL.md` 命令速查 + 任务流；`references/transitions.md` 新增 undo 段

**不做：**

- HTTP REST endpoint（issue 明确"面向 CLI"；前端无入口需求）
- 前端 GUI 入口
- 任何 schema / 迁移（DB 不动）
- 多步撤销 / 时间窗口限制 / 跨资产批量 undo
- 操作审计表（日志足够）

## 3. 关键设计决策（pre-brainstorm 锁定）

| 决策 | 选择 | 理由 |
|---|---|---|
| Q1：能否 undo `DISPOSE`？ | **可以** | v1 工具单一用户 + Agent，无外部合规约束；issue 核心场景就是"误手 dispose 也能救回"。DISPOSED "终态" 是状态机层面（没有 `DISPOSED → IDLE` 的 transition），undo 是元操作不走状态机，不冲突 |
| Q2：是否同步加 HTTP API？ | **不加** | YAGNI；前端无入口；service 层是唯一事实，CLI 直接 import，未来真要 GUI 化再补 |
| Q3：是否留操作痕迹？ | **DB 零脚印 + `logger.info` 一行** | issue 强调 "不会在历史中留下两条多余的脚印"；但运行日志成本极低，给出一条"出错时可追溯"的安全网 |

## 4. 实现细节

### 4.1 Repository

`src/asset_hub/repositories/state_transition.py` 新增：

```python
def find_last(self, asset_id: uuid.UUID) -> StateTransitionRecord | None:
    """按 created_at 倒序取第一条，无则 None。"""
    stmt = (
        select(StateTransitionRecord)
        .where(StateTransitionRecord.asset_id == asset_id)
        .order_by(StateTransitionRecord.created_at.desc())
        .limit(1)
    )
    return self.session.exec(stmt).first()

def delete(self, record: StateTransitionRecord) -> None:
    self.session.delete(record)
    self.session.flush()
```

### 4.2 Service

`src/asset_hub/services/transition.py::TransitionService` 新增（返回 **DTO** 而非 ORM record，避免 commit/delete 后 detached instance lazy-load 失败）：

```python
import logging
logger = logging.getLogger(__name__)

def undo_last_transition(self, asset_id: uuid.UUID) -> TransitionRead:
    """删除该 asset 最后一条 transition 并回退 asset 三字段。

    - asset 不存在 → NotFoundError (404 / exit 3)
    - asset 无 transition → StateError(code=state_conflict, exit 1)
    - 否则 DELETE 该行 + 重置 asset.status/holder/location = 该行 from_*，
      并把 asset.updated_at 推到 now。
    - 返回被删 transition 的 TransitionRead DTO（commit 前 validate，
      避免后续 ORM 字段访问触发 lazy-load 异常）。
    """
    asset = self.asset_svc.get_asset(asset_id)  # 404 兜底
    last = self.repo.find_last(asset_id)
    if last is None:
        raise StateError(
            f"资产无可撤销的流转记录: {asset_id}",
            hint="该资产自登记以来无 transition；如需删除资产本身请用 asset delete。",
            affected_resource_id=str(asset_id),
        )

    # 在 commit / delete 前快照为 DTO，保证后续可序列化
    snapshot = TransitionRead.model_validate(last)

    asset.status = last.from_status
    asset.holder = last.from_holder
    asset.location = last.from_location
    asset.updated_at = datetime.now(UTC)
    self.repo.delete(last)

    logger.info(
        "undo transition asset_id=%s record_id=%s kind=%s created_at=%s",
        asset_id, snapshot.id, snapshot.kind, snapshot.created_at,
    )

    self.session.commit()
    return snapshot
```

**关键约束：**

- **不走** `validate_transition` / 12 种 kind 状态机；undo 是元操作。
- `closes_transition_id` 反向链：最后一条 transition 不可能被任何更晚的记录引用（它最晚）；安全物理删。
- 删 `RETURN` / `DISMISS` 后，原 OPEN `CHECKOUT_*` 自动重新被 `find_open_checkout_id` 认作 OPEN——这是 undo 想要的副作用（恢复派出状态）。
- 删 `CHECKOUT_*` 本身：该行无 `closes_transition_id` 外向引用（CHECKOUT 自己不闭合任何东西），物理删无悬挂。
- `asset_code` / `serial_number` / `acquired_at` / `notes` / `custom_data` / `brand` / `model` / `name` / `type_id` —— transition 不影响这些字段，undo 不动。

### 4.3 CLI 命令

`src/asset_hub/cli/asset_cmd.py` 新增：

```python
@asset_app.command("undo")
def asset_undo(
    asset_id: Annotated[str, typer.Argument(help="资产 UUID")],
    dry_run: Annotated[bool, typer.Option("--dry-run", help="预览，不实际撤销")] = False,
    fields: Annotated[str | None, typer.Option("--fields", help="逗号分隔字段名")] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """撤销该资产最后一条流转记录（物理删除，元操作不进状态机）。"""
    uid = parse_uuid(asset_id, json_output)
    parsed_fields = parse_cli_fields(fields)

    with cli_session() as session, handle_domain_errors(json_output):
        tx_svc = TransitionService(session)

        if dry_run:
            last = tx_svc.repo.find_last(uid)  # 复用 service 内 repo；或加 svc.peek_last()
            asset = tx_svc.asset_svc.get_asset(uid)
            if last is None:
                # 抛 StateError 让 envelope 走错误路径，与非 dry-run 一致
                raise StateError(
                    f"资产无可撤销的流转记录: {uid}",
                    hint="该资产自登记以来无 transition；如需删除资产本身请用 asset delete。",
                    affected_resource_id=str(uid),
                )
            print_dry_run(
                {
                    "would_undo": to_json_dict(TransitionRead, last),
                    "would_restore": {
                        "status": last.from_status,
                        "holder": last.from_holder,
                        "location": last.from_location,
                    },
                },
                json_output,
                message=f"将撤销 {last.kind} (created_at={last.created_at.isoformat()})",
            )
            return

        rec = tx_svc.undo_last_transition(uid)  # 已是 TransitionRead DTO

    record = rec.model_dump(mode="json")
    record = filter_record_fields(
        record, parsed_fields, allowed=_TRANSITION_READ_FIELDS, json_output=json_output,
    )
    print_result(record, json_output)
```

**CLI 设计要点：**

- **无 `--yes` / 无 typer.confirm**：undo 是低摩擦"手滑就撤"操作，每次 confirm 反而拖累 Agent；想 preview 用 `--dry-run`。
- `--dry-run` 退出码 10（envelope 规约，同 `asset delete --dry-run`）。
- `--fields` 过滤 `would_undo` / 顶层 record 的字段集合，与 `asset history` 行为对齐。
- 成功输出 `data` = 被删 transition 的 `TransitionRead` shape（保留所有细节，让用户知道 undo 了什么）。

### 4.4 错误码 / 退出码

| 场景 | code | HTTP 等价 | exit | hint |
|---|---|---|---|---|
| asset_id UUID 非法 | `validation` | 422 | 2 | （现有 `parse_uuid` 行为，免改）|
| asset 不存在 | `not_found` | 404 | 3 | （现有 `NotFoundError`）|
| asset 存在但无 transition | `state_conflict` | 409 | 1 | "该资产自登记以来无 transition；如需删除资产本身请用 asset delete。" |
| `--dry-run` 成功 | — | — | 10 | — |
| 正常成功 | — | — | 0 | — |

不引入新 error code。

## 5. 测试计划（TDD 先写失败用例）

### 5.1 `tests/unit/test_transition_undo.py`（service 层 + 真实 SQLite）

| # | 用例 | 期望 |
|---|---|---|
| 1 | register → checkout → undo | asset 回 IDLE / holder=None / location=None；transition 表为空 |
| 2 | register → checkout → return → undo | asset 回 IN_USE / holder=原派出人；剩 1 条 transition；`find_open_checkout_id` 重新认到原 CHECKOUT 为 OPEN |
| 3 | register → retire → dispose → undo | asset 回 RETIRED（**验证 Q1=B**：DISPOSE 可 undo）|
| 4 | register → reassign → undo | asset 回 register 时的 holder / location（验证 self-loop transition 的 from_* 正确）|
| 5 | register（无 transition）→ undo | raise `StateError`，code=`state_conflict`，hint 含建议 |
| 6 | 不存在的 asset_id → undo | raise `NotFoundError` |
| 7 | register → checkout → undo → undo | 第二次 undo → `StateError`（自然递归到 5 用例）|
| 8 | register → checkout（with due_at）→ undo | asset 字段回退；transition 表空；无 due_at 残留（asset 表无该字段，符合预期）|
| 9 | register → send-to-maintenance → recover → undo | asset 回 MAINTENANCE（验证 keep holder/location）|

### 5.2 `tests/cli/test_asset_undo_cmd.py`（CliRunner + isolated_db）

| # | 用例 | 期望 |
|---|---|---|
| 1 | `--json` 成功 | envelope `success=true`，`data` 是 TransitionRead 形态，exit 0 |
| 2 | `--dry-run --json` | envelope `success=true`，`data.would_undo` + `data.would_restore`，exit 10 |
| 3 | 非 UUID 参数 | exit 2，`error.code=validation` |
| 4 | 不存在 asset | exit 3，`error.code=not_found` |
| 5 | 无 transition | exit 1，`error.code=state_conflict`，hint 不为空 |
| 6 | `--fields kind,created_at --json` | `data` 只剩这两字段（与 history `--fields` 行为对齐）|

### 5.3 不需要

- `tests/api/` —— 无 REST endpoint
- `tests/migration/` —— 无 schema 变化

## 6. 文档同步清单

| 文件 | 变更 |
|---|---|
| `SKILL.md` | "命令速查" 加一行 `asset undo <id> [--dry-run --json --fields]`；"常见任务流"或对应小节补"撤销最后一条流转记录"的快速回执 |
| `references/transitions.md` | 底部新增 §"undo（元操作）"段，说明：不在 12 kind 内 / 物理删除 / 对 `closes_transition_id` 的副作用 / 与 RETURN 反向操作的语义差异 / DISPOSE 可被 undo（Q1=B） |
| `references/envelope.md` | 无变更（无新 code） |
| 本 spec | 落盘 `docs/superpowers/specs/2026-05-20-issue24-asset-undo-design.md` |

## 7. 实施顺序（写实现计划时参考）

1. **Repository**：`find_last` + `delete` + unit 测试（5 用例 1/2 先 fail）
2. **Service**：`undo_last_transition` + unit 测试全 9 用例通过
3. **CLI**：`asset undo` 命令 + cli 测试 6 用例通过
4. **文档同步**：SKILL.md / references/transitions.md
5. **手验**：
   - `register → checkout → undo`：`asset show --json` 验证字段
   - `register → undo`：观察 envelope 错误形态
   - `register → checkout → undo --dry-run`：观察 `would_*` 形态
6. **CI gate**：`uv run ruff check . && uv run ruff format --check . && uv run pytest`

## 8. 风险与边界

- **检测最后一条用 `created_at desc`**：同毫秒内两条记录的相对顺序由 SQLite ROWID 兜底，但极不可能（CLI 串行 + service.commit 顺序写入）。即使踩中，undo 删的仍然是"逻辑上的最后一条"。
- **session.delete 后访问 ORM 字段**：service 在 delete/commit 之前先 `TransitionRead.model_validate(last)` 快照为 DTO 返回（见 §4.2），CLI 直接 `model_dump`，整链不再触碰被 detach 的 ORM 实例。
- **并发**：单用户工具，无并发场景；service 层 `commit()` 即事务边界。
- **可逆性**：undo 是物理删除，无法 "redo"；这是 issue 接受的代价（用户语义：手滑就当没发生）。`logger.info` 提供事后追溯入口。
