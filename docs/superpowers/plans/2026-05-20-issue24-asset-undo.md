# issue #24 asset undo 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 落地 `asset-hub asset undo <asset-id>` 元命令，物理删除该资产最后一条 transition 并把 asset 三字段（status/holder/location）回退到该 transition 的 `from_*`。

**Architecture:** 在既有三层（CLI → Service → Repository → SQLModel/SQLite）内增量。Repository 加两个最小方法（取最新 + 删行），Service 加一个元方法（**不**走 `validate_transition`，直接回退字段 + 物理删除 + `logger.info` 留运行日志安全网），CLI 加 `asset undo` 命令复用既有 envelope/parse_uuid/dry-run 工具。无 schema 变更、无迁移、无 REST endpoint、无前端。

**Tech Stack:** Python 3.12 + SQLModel + Typer + Pydantic v2，已存 `tests/{unit,cli,migration}/` 三层测试结构。所有 Python 命令一律 `uv run ...`。

**Spec：** `docs/superpowers/specs/2026-05-20-issue24-asset-undo-design.md`（commit `86e2dd3`）。

---

## File Map（动哪些文件）

| 文件 | 动作 | 责任 |
|---|---|---|
| `src/asset_hub/repositories/state_transition.py` | 修改 | 新增 `find_last(asset_id)` + `delete(record)` |
| `src/asset_hub/services/transition.py` | 修改 | 模块顶部加 `logger = logging.getLogger(__name__)`；类内加 `undo_last_transition(asset_id) -> TransitionRead` |
| `src/asset_hub/cli/asset_cmd.py` | 修改 | 新增 `asset_undo` 命令（含 `--dry-run` / `--json` / `--fields`） |
| `tests/unit/test_transition_undo.py` | 创建 | service 层 9 用例 |
| `tests/cli/test_asset_undo_cmd.py` | 创建 | CLI 层 6 用例 |
| `SKILL.md` | 修改 | 命令速查 + 任务流补一节 |
| `references/transitions.md` | 修改 | 底部新增 §undo（元操作）段 |

无 `tests/api/` 改动（无 REST endpoint）。无 `tests/migration/` 改动（无 schema 变化）。无前端改动。

---

## Task 1: Repository 层（`find_last` + `delete`）

**Files:**
- Modify: `src/asset_hub/repositories/state_transition.py`
- Test: `tests/unit/test_transition_undo.py`（本任务先建文件 + 写 repo 用例）

- [ ] **Step 1.1：新建 `tests/unit/test_transition_undo.py` 并写 repo 两条失败用例**

```python
# tests/unit/test_transition_undo.py
import uuid
from datetime import UTC, datetime

import pytest
from sqlmodel import Session

from asset_hub.errors import NotFoundError, StateError
from asset_hub.models.asset import Asset, AssetStatus
from asset_hub.models.asset_type import AssetType
from asset_hub.models.state_transition import StateTransitionRecord, TransitionKind
from asset_hub.repositories.state_transition import TransitionRepository
from asset_hub.services.transition import TransitionService


@pytest.fixture
def asset_type(session: Session) -> AssetType:
    t = AssetType(name="笔记本", code_prefix="NB", custom_fields=[])
    session.add(t)
    session.commit()
    session.refresh(t)
    return t


def _new_asset(
    session: Session,
    type_id: uuid.UUID,
    *,
    status=AssetStatus.IDLE,
    holder=None,
    location=None,
) -> Asset:
    a = Asset(
        asset_code="NB-001",
        name="测试机",
        type_id=type_id,
        status=status,
        holder=holder,
        location=location,
        custom_data={},
    )
    session.add(a)
    session.commit()
    session.refresh(a)
    return a


# ===== Repository 层 =====

def test_repo_find_last_returns_none_when_no_records(session, asset_type):
    a = _new_asset(session, asset_type.id)
    repo = TransitionRepository(session)
    assert repo.find_last(a.id) is None


def test_repo_find_last_returns_newest_by_created_at(session, asset_type):
    a = _new_asset(session, asset_type.id)
    repo = TransitionRepository(session)
    older = StateTransitionRecord(
        asset_id=a.id,
        kind=TransitionKind.REASSIGN,
        from_status=AssetStatus.IDLE,
        to_status=AssetStatus.IDLE,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    newer = StateTransitionRecord(
        asset_id=a.id,
        kind=TransitionKind.REASSIGN,
        from_status=AssetStatus.IDLE,
        to_status=AssetStatus.IDLE,
        created_at=datetime(2026, 5, 20, tzinfo=UTC),
    )
    session.add(older)
    session.add(newer)
    session.commit()

    last = repo.find_last(a.id)
    assert last is not None
    assert last.id == newer.id


def test_repo_delete_removes_row(session, asset_type):
    a = _new_asset(session, asset_type.id)
    repo = TransitionRepository(session)
    rec = StateTransitionRecord(
        asset_id=a.id,
        kind=TransitionKind.REASSIGN,
        from_status=AssetStatus.IDLE,
        to_status=AssetStatus.IDLE,
    )
    session.add(rec)
    session.commit()
    session.refresh(rec)

    repo.delete(rec)
    session.commit()
    assert repo.find_last(a.id) is None
```

- [ ] **Step 1.2：跑这三条测试确认 FAIL**

```bash
uv run pytest tests/unit/test_transition_undo.py -v
```

Expected：3 个 test 全部 fail，错误信息含 `AttributeError: 'TransitionRepository' object has no attribute 'find_last'`（或 `delete`）。

- [ ] **Step 1.3：实现 `find_last` + `delete`**

把 `src/asset_hub/repositories/state_transition.py` 的 class body 末尾追加（注意保留现有 `list_by_asset` / `find_open_checkout_id`）：

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

- [ ] **Step 1.4：跑这三条测试确认 PASS**

```bash
uv run pytest tests/unit/test_transition_undo.py -v
```

Expected：3 passed。

- [ ] **Step 1.5：ruff format + check（防 CI 退）**

```bash
uv run ruff format src/asset_hub/repositories/state_transition.py tests/unit/test_transition_undo.py
uv run ruff check src/asset_hub/repositories/state_transition.py tests/unit/test_transition_undo.py
```

Expected：format 改动若有则被写回；check 通过（"All checks passed"）。

- [ ] **Step 1.6：commit**

```bash
git add src/asset_hub/repositories/state_transition.py tests/unit/test_transition_undo.py
git commit -m "feat(#24): TransitionRepository 新增 find_last / delete"
```

---

## Task 2: Service 层 `undo_last_transition`（happy path + 边界）

**Files:**
- Modify: `src/asset_hub/services/transition.py`
- Modify (append): `tests/unit/test_transition_undo.py`

- [ ] **Step 2.1：在 `tests/unit/test_transition_undo.py` 追加 service 层失败用例（happy path 4 条）**

把以下追加到文件底部：

```python
# ===== Service 层 happy path =====

def test_undo_checkout_restores_idle(session, asset_type):
    a = _new_asset(session, asset_type.id)
    svc = TransitionService(session)
    svc.record_transition(
        asset_id=a.id,
        kind=TransitionKind.CHECKOUT_INTERNAL,
        to_holder="张三",
        to_location="1F-工位",
    )

    snapshot = svc.undo_last_transition(a.id)

    session.refresh(a)
    assert a.status == AssetStatus.IDLE
    assert a.holder is None
    assert a.location is None
    assert snapshot.kind == TransitionKind.CHECKOUT_INTERNAL
    assert snapshot.to_holder == "张三"
    assert TransitionRepository(session).find_last(a.id) is None


def test_undo_return_reopens_original_checkout(session, asset_type):
    a = _new_asset(session, asset_type.id)
    svc = TransitionService(session)
    co = svc.record_transition(
        asset_id=a.id,
        kind=TransitionKind.CHECKOUT_INTERNAL,
        to_holder="张三",
    )
    svc.record_transition(asset_id=a.id, kind=TransitionKind.RETURN)

    svc.undo_last_transition(a.id)

    session.refresh(a)
    assert a.status == AssetStatus.IN_USE
    assert a.holder == "张三"
    repo = TransitionRepository(session)
    last = repo.find_last(a.id)
    assert last is not None and last.id == co.id
    # 原 CHECKOUT 应重新被认作 OPEN
    assert repo.find_open_checkout_id(a.id) == co.id


def test_undo_dispose_restores_retired(session, asset_type):
    """验证 Q1=B：DISPOSE 是元命令可撤销，绕过状态机终态约束。"""
    a = _new_asset(session, asset_type.id, status=AssetStatus.RETIRED)
    svc = TransitionService(session)
    svc.record_transition(asset_id=a.id, kind=TransitionKind.DISPOSE)
    assert a.status == AssetStatus.DISPOSED  # sanity

    svc.undo_last_transition(a.id)

    session.refresh(a)
    assert a.status == AssetStatus.RETIRED


def test_undo_reassign_restores_holder_and_location(session, asset_type):
    a = _new_asset(session, asset_type.id, holder="原持有", location="原位置")
    svc = TransitionService(session)
    svc.record_transition(
        asset_id=a.id,
        kind=TransitionKind.REASSIGN,
        to_holder="新持有",
        to_location="新位置",
    )

    svc.undo_last_transition(a.id)

    session.refresh(a)
    assert a.holder == "原持有"
    assert a.location == "原位置"
    assert a.status == AssetStatus.IDLE
```

- [ ] **Step 2.2：跑这 4 条测试确认 FAIL（`undo_last_transition` 不存在）**

```bash
uv run pytest tests/unit/test_transition_undo.py::test_undo_checkout_restores_idle tests/unit/test_transition_undo.py::test_undo_return_reopens_original_checkout tests/unit/test_transition_undo.py::test_undo_dispose_restores_retired tests/unit/test_transition_undo.py::test_undo_reassign_restores_holder_and_location -v
```

Expected：4 个测试全部 fail（`AttributeError: 'TransitionService' object has no attribute 'undo_last_transition'`）。

- [ ] **Step 2.3：实现 `undo_last_transition` + 添加 logger import**

在 `src/asset_hub/services/transition.py` 顶部 import 区追加：

```python
import logging
```

且在现有 import 块后、`def _apply_holder_rule(` 之前加：

```python
logger = logging.getLogger(__name__)
```

同时把 `from asset_hub.errors import IllegalTransitionError` 改为：

```python
from asset_hub.errors import IllegalTransitionError, StateError
```

并在 `from asset_hub.api.schemas.transition import TransitionRead` 这一行（若不存在则新增）。检查后实际现状：当前文件 `transition.py` 没有 import `TransitionRead`，需要新增：

```python
from asset_hub.api.schemas.transition import TransitionRead
```

> ⚠️ service 层 import API DTO 是项目既有模式（参见 CLAUDE.md "实现模式"：CLI 输出格式复用 API DTO；service 返回 DTO 不算 ORM 模型泄漏，因为 DTO 是 Pydantic、不是 SQLModel(table=True)）。

然后在 `TransitionService` class 内、`list_transitions` 之前追加方法：

```python
    def undo_last_transition(self, asset_id: uuid.UUID) -> TransitionRead:
        """删除该 asset 最后一条 transition 并回退 asset 三字段。

        元操作：不走 12 种 transition kind 的状态机校验。
        - asset 不存在 → NotFoundError (404 / exit 3)
        - asset 无 transition → StateError (state_conflict / exit 1)
        - 否则：DELETE 该行 + 重置 asset.status/holder/location = 该行 from_*，
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

        # commit / delete 前快照为 DTO（保证后续可序列化）
        snapshot = TransitionRead.model_validate(last)

        asset.status = last.from_status
        asset.holder = last.from_holder
        asset.location = last.from_location
        asset.updated_at = datetime.now(UTC)
        self.repo.delete(last)

        logger.info(
            "undo transition asset_id=%s record_id=%s kind=%s created_at=%s",
            asset_id,
            snapshot.id,
            snapshot.kind,
            snapshot.created_at,
        )

        self.session.commit()
        return snapshot
```

- [ ] **Step 2.4：跑这 4 条测试确认 PASS**

```bash
uv run pytest tests/unit/test_transition_undo.py -v -k "test_undo_checkout_restores_idle or test_undo_return_reopens_original_checkout or test_undo_dispose_restores_retired or test_undo_reassign_restores_holder_and_location"
```

Expected：4 passed。

- [ ] **Step 2.5：跑全量 unit 测试确认无回归**

```bash
uv run pytest tests/unit/ -q
```

Expected：全部 pass（应包括既有 `test_transition_service.py` 等）。

- [ ] **Step 2.6：commit**

```bash
git add src/asset_hub/services/transition.py tests/unit/test_transition_undo.py
git commit -m "feat(#24): TransitionService.undo_last_transition 元操作 + 4 happy path 测试"
```

---

## Task 3: Service 层错误路径 + 余下场景

**Files:**
- Modify (append): `tests/unit/test_transition_undo.py`

- [ ] **Step 3.1：追加 5 条错误/边界用例**

把以下追加到 `tests/unit/test_transition_undo.py` 文件末尾：

```python
# ===== Service 层错误 / 余下场景 =====

def test_undo_without_any_transition_raises_state_conflict(session, asset_type):
    a = _new_asset(session, asset_type.id)
    svc = TransitionService(session)
    with pytest.raises(StateError) as exc_info:
        svc.undo_last_transition(a.id)
    assert "无可撤销的流转记录" in exc_info.value.message
    assert exc_info.value.hint is not None
    assert "asset delete" in exc_info.value.hint
    assert exc_info.value.affected_resource_id == str(a.id)


def test_undo_nonexistent_asset_raises_not_found(session):
    svc = TransitionService(session)
    bogus = uuid.uuid4()
    with pytest.raises(NotFoundError):
        svc.undo_last_transition(bogus)


def test_undo_twice_second_raises_state_conflict(session, asset_type):
    a = _new_asset(session, asset_type.id)
    svc = TransitionService(session)
    svc.record_transition(
        asset_id=a.id, kind=TransitionKind.CHECKOUT_INTERNAL, to_holder="张三"
    )
    svc.undo_last_transition(a.id)

    with pytest.raises(StateError):
        svc.undo_last_transition(a.id)


def test_undo_checkout_with_due_at_no_residue(session, asset_type):
    """due_at 仅在 transition 行上，asset 表无该字段，undo 后无残留。"""
    a = _new_asset(session, asset_type.id)
    svc = TransitionService(session)
    svc.record_transition(
        asset_id=a.id,
        kind=TransitionKind.CHECKOUT_INTERNAL,
        to_holder="张三",
        due_at=datetime(2026, 12, 1, tzinfo=UTC),
    )
    svc.undo_last_transition(a.id)
    session.refresh(a)
    assert a.status == AssetStatus.IDLE
    assert TransitionRepository(session).find_last(a.id) is None


def test_undo_recover_after_send_to_maintenance_keeps_holder_location(
    session, asset_type
):
    """register → send-to-maintenance → recover → undo
    asset 回 MAINTENANCE，holder/location 由 keep 规则保留 register 时的值。
    """
    a = _new_asset(session, asset_type.id, holder="李仓管", location="备件柜")
    svc = TransitionService(session)
    svc.record_transition(asset_id=a.id, kind=TransitionKind.SEND_TO_MAINTENANCE)
    svc.record_transition(asset_id=a.id, kind=TransitionKind.RECOVER_FROM_MAINTENANCE)

    svc.undo_last_transition(a.id)

    session.refresh(a)
    assert a.status == AssetStatus.MAINTENANCE
    assert a.holder == "李仓管"
    assert a.location == "备件柜"
```

- [ ] **Step 3.2：跑这 5 条测试确认 PASS（Service 实现已完成）**

```bash
uv run pytest tests/unit/test_transition_undo.py -v
```

Expected：全部 12 个 test pass（3 repo + 4 happy + 5 error/edge）。

- [ ] **Step 3.3：ruff format + check**

```bash
uv run ruff format src/asset_hub/services/transition.py tests/unit/test_transition_undo.py
uv run ruff check src/asset_hub/services/transition.py tests/unit/test_transition_undo.py
```

Expected：通过。

- [ ] **Step 3.4：commit**

```bash
git add tests/unit/test_transition_undo.py
git commit -m "test(#24): undo_last_transition 错误/边界场景 5 用例"
```

---

## Task 4: CLI `asset undo` 命令（含 dry-run）

**Files:**
- Modify: `src/asset_hub/cli/asset_cmd.py`
- Test: `tests/cli/test_asset_undo_cmd.py`（新建）

- [ ] **Step 4.1：新建 `tests/cli/test_asset_undo_cmd.py` 写 6 条失败用例**

```python
# tests/cli/test_asset_undo_cmd.py
import json

import pytest
from typer.testing import CliRunner

from asset_hub.cli.main import app

runner = CliRunner()


@pytest.fixture
def idle_asset_id(isolated_db):
    """创建一个 IDLE 资产，返回 UUID 字符串。"""
    res = runner.invoke(
        app,
        ["type", "define", "--name", "笔记本", "--prefix", "NB", "--json"],
    )
    assert res.exit_code == 0, res.stdout
    type_id = json.loads(res.stdout)["data"]["id"]

    res = runner.invoke(
        app,
        ["asset", "register", "--name", "测试机", "--type-id", type_id, "--json"],
    )
    assert res.exit_code == 0, res.stdout
    return json.loads(res.stdout)["data"]["id"]


@pytest.fixture
def asset_with_one_checkout(idle_asset_id):
    res = runner.invoke(
        app,
        ["asset", "checkout", idle_asset_id, "--to-holder", "张三", "--json"],
    )
    assert res.exit_code == 0, res.stdout
    return idle_asset_id


def test_undo_success_returns_transition_envelope(asset_with_one_checkout):
    res = runner.invoke(
        app, ["asset", "undo", asset_with_one_checkout, "--json"]
    )
    assert res.exit_code == 0, res.stdout
    body = json.loads(res.stdout)
    assert body["success"] is True
    assert body["data"]["kind"] == "CHECKOUT_INTERNAL"
    assert body["data"]["to_holder"] == "张三"

    # 验证副作用：asset 已回 IDLE
    show = runner.invoke(
        app, ["asset", "show", asset_with_one_checkout, "--json"]
    )
    assert json.loads(show.stdout)["data"]["status"] == "IDLE"


def test_undo_dry_run_returns_preview_envelope_exit_10(asset_with_one_checkout):
    res = runner.invoke(
        app,
        ["asset", "undo", asset_with_one_checkout, "--dry-run", "--json"],
    )
    assert res.exit_code == 10, res.stdout
    body = json.loads(res.stdout)
    assert body["success"] is True
    assert "would_undo" in body["data"]
    assert "would_restore" in body["data"]
    assert body["data"]["would_undo"]["kind"] == "CHECKOUT_INTERNAL"
    assert body["data"]["would_restore"]["status"] == "IDLE"

    # 验证 dry-run 不改 DB：还能再 undo
    res2 = runner.invoke(
        app, ["asset", "undo", asset_with_one_checkout, "--json"]
    )
    assert res2.exit_code == 0


def test_undo_invalid_uuid_exit_2(isolated_db):
    res = runner.invoke(app, ["asset", "undo", "not-a-uuid", "--json"])
    assert res.exit_code == 2, res.stdout
    body = json.loads(res.stdout)
    assert body["success"] is False
    assert body["error"]["code"] == "validation"


def test_undo_nonexistent_asset_exit_3(isolated_db):
    res = runner.invoke(
        app,
        [
            "asset",
            "undo",
            "00000000-0000-0000-0000-000000000000",
            "--json",
        ],
    )
    assert res.exit_code == 3, res.stdout
    body = json.loads(res.stdout)
    assert body["success"] is False
    assert body["error"]["code"] == "not_found"


def test_undo_no_transitions_state_conflict_exit_1(idle_asset_id):
    res = runner.invoke(app, ["asset", "undo", idle_asset_id, "--json"])
    assert res.exit_code == 1, res.stdout
    body = json.loads(res.stdout)
    assert body["success"] is False
    assert body["error"]["code"] == "state_conflict"
    assert body["error"]["hint"]  # 非空


def test_undo_fields_filter_applies(asset_with_one_checkout):
    res = runner.invoke(
        app,
        [
            "asset",
            "undo",
            asset_with_one_checkout,
            "--fields",
            "kind,to_holder",
            "--json",
        ],
    )
    assert res.exit_code == 0, res.stdout
    body = json.loads(res.stdout)
    assert set(body["data"].keys()) == {"kind", "to_holder"}
    assert body["data"]["kind"] == "CHECKOUT_INTERNAL"
```

- [ ] **Step 4.2：跑这 6 条测试确认 FAIL（无 undo 命令）**

```bash
uv run pytest tests/cli/test_asset_undo_cmd.py -v
```

Expected：所有 6 个 test fail（typer "No such command 'undo'"）。

- [ ] **Step 4.3：在 `src/asset_hub/cli/asset_cmd.py` 新增 `asset_undo` 命令**

在 `asset_delete` 命令前（即文件 668 行附近、`@asset_app.command("delete")` 上方）插入：

```python
@asset_app.command("undo")
def asset_undo(
    asset_id: Annotated[str, typer.Argument(help="资产 UUID")],
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="预览，不实际撤销")
    ] = False,
    fields: Annotated[
        str | None, typer.Option("--fields", help="逗号分隔字段名，按需返回")
    ] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """撤销该资产最后一条流转记录（物理删除，元操作不进状态机）。"""
    uid = parse_uuid(asset_id, json_output)
    parsed_fields = parse_cli_fields(fields)

    with cli_session() as session, handle_domain_errors(json_output):
        tx_svc = TransitionService(session)
        tx_svc.asset_svc.get_asset(uid)  # 404 兜底（与 service 路径对称）

        if dry_run:
            last = tx_svc.repo.find_last(uid)
            if last is None:
                from asset_hub.errors import StateError

                raise StateError(
                    f"资产无可撤销的流转记录: {uid}",
                    hint="该资产自登记以来无 transition；如需删除资产本身请用 asset delete。",
                    affected_resource_id=str(uid),
                )
            print_dry_run(
                {
                    "would_undo": to_json_dict(TransitionRead, last),
                    "would_restore": {
                        "status": last.from_status.value,
                        "holder": last.from_holder,
                        "location": last.from_location,
                    },
                },
                json_output,
                message=f"将撤销 {last.kind.value} (created_at={last.created_at.isoformat()})",
            )
            return

        rec = tx_svc.undo_last_transition(uid)  # 已是 TransitionRead DTO

    record = rec.model_dump(mode="json")
    record = filter_record_fields(
        record,
        parsed_fields,
        allowed=_TRANSITION_READ_FIELDS,
        json_output=json_output,
    )
    print_result(record, json_output)
```

> 备注：`tx_svc.repo` 和 `tx_svc.asset_svc` 都是 `TransitionService.__init__` 中已存在的属性，CLI 复用合法。`from asset_hub.errors import StateError` 在 dry-run 分支内 lazy import 避免顶部 import 区污染；若你偏好顶部 import，把它提到文件顶部 import 块也可。

- [ ] **Step 4.4：跑 CLI 6 条测试确认 PASS**

```bash
uv run pytest tests/cli/test_asset_undo_cmd.py -v
```

Expected：6 passed。

- [ ] **Step 4.5：跑全量 cli 测试确认无回归**

```bash
uv run pytest tests/cli/ -q
```

Expected：全部 pass。

- [ ] **Step 4.6：ruff format + check**

```bash
uv run ruff format src/asset_hub/cli/asset_cmd.py tests/cli/test_asset_undo_cmd.py
uv run ruff check src/asset_hub/cli/asset_cmd.py tests/cli/test_asset_undo_cmd.py
```

Expected：通过。

- [ ] **Step 4.7：commit**

```bash
git add src/asset_hub/cli/asset_cmd.py tests/cli/test_asset_undo_cmd.py
git commit -m "feat(#24): CLI asset undo 命令（含 --dry-run / --fields / --json）"
```

---

## Task 5: 文档同步（`SKILL.md` + `references/transitions.md`）

**Files:**
- Modify: `SKILL.md`
- Modify: `references/transitions.md`

- [ ] **Step 5.1：在 `SKILL.md` 命令速查 transition 段添加 `undo`**

定位 `SKILL.md` 的 "命令速查" 章节里 transition / asset 命令列表区域（用 grep 找 `asset checkout` 或 `asset return` 锚点），紧邻其下方加：

```
asset-hub asset undo <id> [--dry-run] [--fields ...] [--json]   # 撤销最后一条流转（物理删除元操作）
```

- [ ] **Step 5.2：在 `SKILL.md` 找到 "常见任务流" 或同性质章节，追加一节**

```markdown
### 撤销最后一条流转记录（手滑回退）

```bash
# 不确定要撤哪条 → 先预览
asset-hub asset undo <asset-id> --dry-run --json   # exit 10

# 确认无误，执行
asset-hub asset undo <asset-id> --json             # exit 0；data 是被删的 transition
```

约束：
- 只能撤"最后一条"（按 created_at desc），中间记录无法跳删
- 没有任何 transition 时报 `state_conflict`（exit 1）
- DISPOSE 也可撤销（v1 单一用户工具，无合规约束）
- 物理删除、零 DB 脚印；运行日志（`serve logs`）会留一行 `undo transition ...` 供事后追溯
```

> 若 SKILL.md 没有"常见任务流"小节，则插入到状态机/transition 章节下方一个新 `## 撤销流转` 小节即可。

- [ ] **Step 5.3：在 `references/transitions.md` 文件底部追加 §undo 段**

```markdown
## undo（元操作，不在 12 kind 内）

`asset-hub asset undo <id>` 物理删除该资产的最后一条 transition 并把 `Asset.status` / `Asset.holder` / `Asset.location` 重置为该 transition 的 `from_*`，`Asset.updated_at` 推到 now。

**契约要点：**

- **不**走 `validate_transition` / 状态机；与 12 种 kind 解耦
- 取"最后一条"的依据：`created_at DESC LIMIT 1`
- 物理删除（DB 零脚印），`logger.info` 在 service 层留一行运行日志做事后追溯
- 只能撤最后一条；中间记录不可跳删
- 资产无 transition → `StateError`（code=`state_conflict`，CLI exit 1）；asset 不存在 → `NotFoundError`（exit 3）
- **DISPOSE 可被 undo**（v1 工具无合规约束；元操作不受状态机终态约束）

**副作用：`closes_transition_id` 反向链**

- 删 `RETURN` / `DISMISS` 后，它原本闭合的 `CHECKOUT_*` 会被 `find_open_checkout_id` 重新认作 OPEN —— 这是 undo 想要的语义（恢复派出状态）
- 删 `CHECKOUT_*` 本身：它不闭合任何记录，无悬挂

**与反向 transition 的语义差异：**

| 维度 | `undo` | 反向 transition（如 `return` 反 `checkout`） |
|---|---|---|
| 历史记录 | 零脚印（物理删除）| 多一条记录 |
| 语义 | "我没派发，只是手滑" | "派出后归还" |
| 适用 | 误操作回退 | 真实业务往返 |
| 终态 DISPOSE | 可撤 | 无反向 transition，无法救回 |
```

- [ ] **Step 5.4：sanity check 文档锚点**

```bash
uv run pytest tests/ -q  # 防文档改动有意外触发的测试断言
```

Expected：依旧全 pass。

- [ ] **Step 5.5：commit**

```bash
git add SKILL.md references/transitions.md
git commit -m "docs(#24): SKILL.md + references/transitions.md 增补 asset undo"
```

---

## Task 6: 全量 gate + 手动烟测

**Files:** 无新文件，纯校验。

- [ ] **Step 6.1：跑全量后端测试 + ruff（CI 等价命令）**

```bash
uv run ruff check . && uv run ruff format --check . && uv run pytest
```

Expected：所有命令 exit 0。`pytest` 通过包括 12 + 6 = 18 条新测试在内的全量。

- [ ] **Step 6.2：手动烟测 — 主路径（CLI 真实交互）**

```bash
# 准备：新建 type + 资产，派出
uv run asset-hub type define --name 笔记本 --prefix NB --json
# 记下 type_id，假设为 $TYPE_ID
uv run asset-hub asset register --name 测试机 --type-id $TYPE_ID --json
# 记下 asset_id，假设为 $AID
uv run asset-hub asset checkout $AID --to-holder 张三 --json

# undo dry-run（不实际执行）
uv run asset-hub asset undo $AID --dry-run --json
# Expected: exit 10, data.would_undo.kind == "CHECKOUT_INTERNAL", data.would_restore.status == "IDLE"

# 真实 undo
uv run asset-hub asset undo $AID --json
# Expected: exit 0, data.kind == "CHECKOUT_INTERNAL"

# 验证回退
uv run asset-hub asset show $AID --json
# Expected: data.status == "IDLE"，holder == null
uv run asset-hub asset history $AID --json
# Expected: metadata.count == 0
```

- [ ] **Step 6.3：手动烟测 — 错误路径**

```bash
# 无 transition 时 undo
uv run asset-hub asset undo $AID --json
# Expected: exit 1, error.code == "state_conflict", error.hint 含 "asset delete"

# 不存在 asset
uv run asset-hub asset undo 00000000-0000-0000-0000-000000000000 --json
# Expected: exit 3, error.code == "not_found"

# 非法 UUID
uv run asset-hub asset undo not-a-uuid --json
# Expected: exit 2, error.code == "validation"
```

- [ ] **Step 6.4：手动烟测 — DISPOSE undo 路径（验证 Q1=B）**

```bash
uv run asset-hub asset retire $AID --yes --json
uv run asset-hub asset dispose $AID --yes --json
uv run asset-hub asset show $AID --json  # status == DISPOSED
uv run asset-hub asset undo $AID --json
uv run asset-hub asset show $AID --json  # status == RETIRED
```

Expected：每步 exit 0，最终 status 回 RETIRED。

- [ ] **Step 6.5：（可选）若启了 `serve start` 看一眼日志**

```bash
uv run asset-hub serve logs --tail 20
```

Expected：能看到形如 `undo transition asset_id=... record_id=... kind=...` 的一行（验证 Q3=B 日志安全网生效）。

- [ ] **Step 6.6：推送分支 + 开 PR**

```bash
# 若当前在 main 直接改：先创分支
git checkout -b feat/issue-24-asset-undo  # 若已有特性分支跳过
git push -u origin HEAD
gh pr create --title "feat(#24): asset undo 命令 — 撤销最后一条流转记录" --body "$(cat <<'EOF'
## Summary
- 新增 `asset-hub asset undo <id> [--dry-run --fields --json]` 元命令
- 物理删除最后一条 transition，回退 asset 三字段；DB 零脚印 + logger.info 留运行日志
- DISPOSE 也可 undo（v1 无合规约束，元操作不受状态机终态约束）
- 仅 CLI + service + repo（无 REST、无迁移、无前端）

Closes #24

## Test plan
- [x] 12 unit tests（repo 3 + service happy 4 + service edge 5）
- [x] 6 cli tests（成功 / dry-run / 三种错误 / fields 过滤）
- [x] 手动烟测主路径 + 错误路径 + DISPOSE undo 路径
- [x] `uv run ruff check . && uv run ruff format --check . && uv run pytest` 全绿
EOF
)"
```

> 若仓库当前不开 PR、直接 push main，则把上面这一步替换为 `git push origin main`。视项目流程而定。

---

## Self-Review（已自检完成）

- **Spec 覆盖：** §2 范围 6 项 / §3 三决策 / §4 repo+service+CLI / §5 测试 9+6 / §6 文档清单 — 全部映射到 Task 1–5；最终 gate 在 Task 6。
- **Placeholder 扫描：** 已检查无 TBD / TODO / "implement later"。
- **类型一致性：**
  - `find_last` 返回 `StateTransitionRecord | None` — Task 1/2 一致
  - `undo_last_transition` 返回 `TransitionRead`（DTO）— Task 2 实现 + Task 4 CLI 消费一致
  - `delete(record)` 签名 — Task 1 定义 + Task 2 service 调用一致
  - `from_status` 在 CLI dry-run 输出 `from_status.value`（StrEnum → string），与现有 envelope JSON 模式一致
- **错误处理：** `StateError` / `NotFoundError` 均在 `handle_domain_errors` 自动翻译为正确 exit code（1 / 3），不需要 CLI 手动 try/except。
- **既有约定遵从：** ORM 不出 service（返回 `TransitionRead` Pydantic）；`parse_uuid` 复用；`print_dry_run` + `print_result` 复用；ruff format 由工具负责行长。
