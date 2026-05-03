# M3a PR-1 实施计划：后端契约 + schema migration

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** M3a PR-1 落地——后端 5 态状态机（含 DISPOSED）+ 10 transition kind 单表 + TransitionService SoT + API 不向后兼容切换（删 checkout 端点 + 新 transitions 端点）+ CLI 9 命令 + alembic schema migration（不迁移测试数据）+ 删除整条旧 Checkout 链路 + 重新生成前端 OpenAPI 类型。

**Architecture:** 数据层 `StateTransitionRecord` 宽表替代 `CheckoutRecord`；service 层 `TransitionService.record_transition()` 单事务（state machine 校验 → INSERT transition → UPDATE asset）；状态机校验层 `TRANSITION_RULES + validate_transition` 是合法性 SoT（simplify C1 闭环）；API `POST/GET /api/assets/{id}/transitions` nested resource 单一 body shape；CLI 保留 `checkout/return/history` 命令名 + 新增 7 命令。

**Tech Stack:** Python 3.x（uv）、FastAPI、SQLModel、SQLAlchemy 2.x、Alembic、Pydantic v2、Typer。

**Spec:** [`docs/superpowers/specs/2026-05-03-m3a-state-machine-design.md`](../specs/2026-05-03-m3a-state-machine-design.md)

**配套 PR-2 plan**：[`2026-05-03-m3a-pr2-frontend.md`](./2026-05-03-m3a-pr2-frontend.md)（前端切换 + UX 完整；PR-1 合并后再启动）

**前置约束**：

- 用户在 Task 9 之前**手动**清空测试数据库（`rm data/asset_hub.db` + 清空 `data/attachments/*`）。M3a 决议不做数据迁移，旧测试数据全清重建
- PR-1 合并后 main 上前端会临时 broken（旧 `CheckoutRead` import 失效），由 PR-2 修复

**任务总览**（11 任务）：

1. AssetStatus 加 DISPOSED + StateTransitionRecord/TransitionKind 模型
2. 状态机 SoT 重写 + 单测（约 50+ case）
3. IllegalTransitionError handler + TransitionRepository
4. TransitionService.record_transition + 单测（约 15-20 case）
5. AssetService 改造（删 change_status / 限制 update_asset / 加 list filter）
6. Transition DTOs + API router + 端点测试
7. 删除旧 Checkout 链路文件
8. CLI 重构 + 测试
9. Alembic schema migration（用户先清空 db）
10. 前端 OpenAPI schema 重新生成
11. PR-1 验收清单

---

## 任务详情

### Task 1: AssetStatus 加 DISPOSED + 新建 TransitionKind / StateTransitionRecord 模型

**Files:**
- Modify: `src/asset_hub/models/asset.py`（删 `current_checkout_id` 字段；status enum 加 DISPOSED）
- Create: `src/asset_hub/models/state_transition.py`
- Modify: `src/asset_hub/models/__init__.py`（如有，导出新 model）

- [ ] **Step 1.1: 修改 AssetStatus enum**

修改 `src/asset_hub/models/asset.py:14-18`：

```python
class AssetStatus(StrEnum):
    IN_USE = "IN_USE"
    IDLE = "IDLE"
    MAINTENANCE = "MAINTENANCE"
    RETIRED = "RETIRED"
    DISPOSED = "DISPOSED"  # 新增，终态
```

- [ ] **Step 1.2: 删除 Asset.current_checkout_id 字段**

修改 `src/asset_hub/models/asset.py`，删除：

```python
current_checkout_id: uuid.UUID | None = Field(
    default=None, foreign_key="checkout_records.id", index=True
)
```

- [ ] **Step 1.3: 创建 StateTransitionRecord 模型**

新建 `src/asset_hub/models/state_transition.py`：

```python
import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import Index
from sqlmodel import Field, SQLModel

from asset_hub.models.asset import AssetStatus


class TransitionKind(StrEnum):
    CHECKOUT_INTERNAL = "CHECKOUT_INTERNAL"
    CHECKOUT_EXTERNAL = "CHECKOUT_EXTERNAL"
    RETURN = "RETURN"
    SEND_TO_MAINTENANCE = "SEND_TO_MAINTENANCE"
    RECOVER_FROM_MAINTENANCE = "RECOVER_FROM_MAINTENANCE"
    RETIRE = "RETIRE"
    REINSTATE = "REINSTATE"
    DISPOSE = "DISPOSE"
    RELOCATE = "RELOCATE"
    TRANSFER_HOLDER = "TRANSFER_HOLDER"


class StateTransitionRecord(SQLModel, table=True):
    __tablename__ = "state_transition_records"
    __table_args__ = (
        Index("ix_transition_asset_created", "asset_id", "created_at"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    asset_id: uuid.UUID = Field(foreign_key="assets.id", index=True)
    kind: TransitionKind
    from_status: AssetStatus
    to_status: AssetStatus
    from_holder: str | None = None
    to_holder: str | None = None
    from_location: str | None = None
    to_location: str | None = None
    note: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)
    due_at: datetime | None = None
    closes_transition_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="state_transition_records.id",
        index=True,
    )
```

- [ ] **Step 1.4: 验证 import 通过**

Run: `uv run python -c "from asset_hub.models.state_transition import StateTransitionRecord, TransitionKind; from asset_hub.models.asset import AssetStatus; print(AssetStatus.DISPOSED, TransitionKind.RELOCATE)"`
Expected: `AssetStatus.DISPOSED TransitionKind.RELOCATE`

- [ ] **Step 1.5: Commit**

```bash
git add src/asset_hub/models/asset.py src/asset_hub/models/state_transition.py
git commit -m "feat(model): AssetStatus 加 DISPOSED + 新建 StateTransitionRecord/TransitionKind 模型"
```

---

### Task 2: 状态机 SoT 重写 + 单测

**Files:**
- Modify: `src/asset_hub/errors.py`（加 IllegalTransitionError）
- Modify: `src/asset_hub/services/state_machine.py`（重写为 TRANSITION_RULES + validate_transition）
- Create: `tests/unit/test_state_machine.py`（重写）
- Delete: 原 `tests/unit/test_state_machine.py` 内容（如有）

- [ ] **Step 2.1: 加 IllegalTransitionError**

修改 `src/asset_hub/errors.py`，append：

```python
class IllegalTransitionError(Exception):
    """状态机拒绝当前 transition。映射 HTTP 409 Conflict。"""
```

- [ ] **Step 2.2: 重写 state_machine.py**

完全替换 `src/asset_hub/services/state_machine.py`：

```python
"""状态机校验层 SoT（M3a 子 spec §2.6）。

TRANSITION_RULES 是合法 from/to + holder/location 必填规则的唯一来源。
service 层不写 if-block 双层防御（C1 闭环）。
"""
from typing import Literal, NamedTuple

from asset_hub.errors import IllegalTransitionError
from asset_hub.models.asset import AssetStatus
from asset_hub.models.state_transition import TransitionKind

HolderRule = Literal["required", "optional", "forced_null", "ignored"]
LocationRule = Literal["required", "optional", "forced_null"]


class TransitionRule(NamedTuple):
    valid_from: frozenset[AssetStatus]
    to_status: AssetStatus | None  # None = 同 from（RELOCATE/TRANSFER_HOLDER）
    holder_rule: HolderRule
    location_rule: LocationRule


_ALL_BUT_DISPOSED = frozenset({
    AssetStatus.IDLE,
    AssetStatus.IN_USE,
    AssetStatus.MAINTENANCE,
    AssetStatus.RETIRED,
})


TRANSITION_RULES: dict[TransitionKind, TransitionRule] = {
    TransitionKind.CHECKOUT_INTERNAL: TransitionRule(
        valid_from=frozenset({AssetStatus.IDLE}),
        to_status=AssetStatus.IN_USE,
        holder_rule="required",
        location_rule="optional",
    ),
    TransitionKind.CHECKOUT_EXTERNAL: TransitionRule(
        valid_from=frozenset({AssetStatus.IDLE}),
        to_status=AssetStatus.IN_USE,
        holder_rule="required",
        location_rule="optional",
    ),
    TransitionKind.RETURN: TransitionRule(
        valid_from=frozenset({AssetStatus.IN_USE}),
        to_status=AssetStatus.IDLE,
        holder_rule="optional",
        location_rule="optional",
    ),
    TransitionKind.SEND_TO_MAINTENANCE: TransitionRule(
        valid_from=frozenset({AssetStatus.IDLE}),
        to_status=AssetStatus.MAINTENANCE,
        holder_rule="optional",
        location_rule="optional",
    ),
    TransitionKind.RECOVER_FROM_MAINTENANCE: TransitionRule(
        valid_from=frozenset({AssetStatus.MAINTENANCE}),
        to_status=AssetStatus.IDLE,
        holder_rule="optional",
        location_rule="optional",
    ),
    TransitionKind.RETIRE: TransitionRule(
        valid_from=frozenset({AssetStatus.IDLE, AssetStatus.MAINTENANCE}),
        to_status=AssetStatus.RETIRED,
        holder_rule="optional",
        location_rule="optional",
    ),
    TransitionKind.REINSTATE: TransitionRule(
        valid_from=frozenset({AssetStatus.RETIRED}),
        to_status=AssetStatus.IDLE,
        holder_rule="optional",
        location_rule="optional",
    ),
    TransitionKind.DISPOSE: TransitionRule(
        valid_from=frozenset({AssetStatus.RETIRED, AssetStatus.MAINTENANCE}),
        to_status=AssetStatus.DISPOSED,
        holder_rule="forced_null",
        location_rule="forced_null",
    ),
    TransitionKind.RELOCATE: TransitionRule(
        valid_from=_ALL_BUT_DISPOSED,
        to_status=None,
        holder_rule="ignored",
        location_rule="required",
    ),
    TransitionKind.TRANSFER_HOLDER: TransitionRule(
        valid_from=_ALL_BUT_DISPOSED,
        to_status=None,
        holder_rule="required",
        location_rule="optional",
    ),
}


def validate_transition(
    current_status: AssetStatus,
    kind: TransitionKind,
    to_holder: str | None,
    to_location: str | None,
) -> AssetStatus:
    """返回 to_status；非法抛 IllegalTransitionError。"""
    rule = TRANSITION_RULES[kind]
    if current_status not in rule.valid_from:
        raise IllegalTransitionError(
            f"{kind.value} 不能从 {current_status.value} 出发"
        )
    if rule.holder_rule == "required" and not to_holder:
        raise IllegalTransitionError(f"{kind.value} 必须提供 to_holder")
    if rule.location_rule == "required" and not to_location:
        raise IllegalTransitionError(f"{kind.value} 必须提供 to_location")
    return rule.to_status if rule.to_status is not None else current_status
```

- [ ] **Step 2.3: 写状态机单测（合法 from 矩阵）**

新建 `tests/unit/test_state_machine.py`：

```python
import pytest

from asset_hub.errors import IllegalTransitionError
from asset_hub.models.asset import AssetStatus
from asset_hub.models.state_transition import TransitionKind
from asset_hub.services.state_machine import TRANSITION_RULES, validate_transition


@pytest.mark.parametrize(
    "kind,from_status,expected_to",
    [
        (TransitionKind.CHECKOUT_INTERNAL, AssetStatus.IDLE, AssetStatus.IN_USE),
        (TransitionKind.CHECKOUT_EXTERNAL, AssetStatus.IDLE, AssetStatus.IN_USE),
        (TransitionKind.RETURN, AssetStatus.IN_USE, AssetStatus.IDLE),
        (TransitionKind.SEND_TO_MAINTENANCE, AssetStatus.IDLE, AssetStatus.MAINTENANCE),
        (TransitionKind.RECOVER_FROM_MAINTENANCE, AssetStatus.MAINTENANCE, AssetStatus.IDLE),
        (TransitionKind.RETIRE, AssetStatus.IDLE, AssetStatus.RETIRED),
        (TransitionKind.RETIRE, AssetStatus.MAINTENANCE, AssetStatus.RETIRED),
        (TransitionKind.REINSTATE, AssetStatus.RETIRED, AssetStatus.IDLE),
        (TransitionKind.DISPOSE, AssetStatus.RETIRED, AssetStatus.DISPOSED),
        (TransitionKind.DISPOSE, AssetStatus.MAINTENANCE, AssetStatus.DISPOSED),
    ],
)
def test_legal_transitions(kind, from_status, expected_to):
    to = validate_transition(from_status, kind, to_holder="X", to_location="Y")
    assert to == expected_to


@pytest.mark.parametrize("from_status", list(AssetStatus))
def test_relocate_returns_same_status_except_disposed(from_status):
    if from_status == AssetStatus.DISPOSED:
        with pytest.raises(IllegalTransitionError):
            validate_transition(from_status, TransitionKind.RELOCATE, None, "loc")
    else:
        to = validate_transition(from_status, TransitionKind.RELOCATE, None, "loc")
        assert to == from_status


@pytest.mark.parametrize("from_status", list(AssetStatus))
def test_transfer_holder_returns_same_status_except_disposed(from_status):
    if from_status == AssetStatus.DISPOSED:
        with pytest.raises(IllegalTransitionError):
            validate_transition(from_status, TransitionKind.TRANSFER_HOLDER, "h", None)
    else:
        to = validate_transition(from_status, TransitionKind.TRANSFER_HOLDER, "h", None)
        assert to == from_status


@pytest.mark.parametrize(
    "kind,bad_from",
    [
        (TransitionKind.CHECKOUT_INTERNAL, AssetStatus.IN_USE),
        (TransitionKind.CHECKOUT_INTERNAL, AssetStatus.MAINTENANCE),
        (TransitionKind.CHECKOUT_INTERNAL, AssetStatus.RETIRED),
        (TransitionKind.CHECKOUT_INTERNAL, AssetStatus.DISPOSED),
        (TransitionKind.RETURN, AssetStatus.IDLE),
        (TransitionKind.RETURN, AssetStatus.MAINTENANCE),
        (TransitionKind.SEND_TO_MAINTENANCE, AssetStatus.IN_USE),
        (TransitionKind.RECOVER_FROM_MAINTENANCE, AssetStatus.IDLE),
        (TransitionKind.RETIRE, AssetStatus.IN_USE),
        (TransitionKind.RETIRE, AssetStatus.RETIRED),
        (TransitionKind.REINSTATE, AssetStatus.IDLE),
        (TransitionKind.DISPOSE, AssetStatus.IDLE),
        (TransitionKind.DISPOSE, AssetStatus.IN_USE),
        (TransitionKind.DISPOSE, AssetStatus.DISPOSED),
    ],
)
def test_illegal_from_raises(kind, bad_from):
    with pytest.raises(IllegalTransitionError):
        validate_transition(bad_from, kind, to_holder="X", to_location="Y")


def test_required_holder_missing_raises():
    with pytest.raises(IllegalTransitionError, match="to_holder"):
        validate_transition(AssetStatus.IDLE, TransitionKind.CHECKOUT_INTERNAL, None, None)


def test_required_location_missing_raises():
    with pytest.raises(IllegalTransitionError, match="to_location"):
        validate_transition(AssetStatus.IDLE, TransitionKind.RELOCATE, None, None)


def test_dispose_forced_null_rules():
    rule = TRANSITION_RULES[TransitionKind.DISPOSE]
    assert rule.holder_rule == "forced_null"
    assert rule.location_rule == "forced_null"


def test_relocate_holder_ignored_rule():
    rule = TRANSITION_RULES[TransitionKind.RELOCATE]
    assert rule.holder_rule == "ignored"
```

- [ ] **Step 2.4: 跑 state machine 测试**

Run: `uv run pytest tests/unit/test_state_machine.py -v`
Expected: 所有用例 PASS（约 50+ case）

- [ ] **Step 2.5: Commit**

```bash
git add src/asset_hub/errors.py src/asset_hub/services/state_machine.py tests/unit/test_state_machine.py
git commit -m "feat(state-machine): TRANSITION_RULES + validate_transition SoT 重写（C1 闭环）+ IllegalTransitionError"
```

---

### Task 3: 异常 handler 注册 + Repository

**Files:**
- Modify: `src/asset_hub/api/app.py`（加 IllegalTransitionError handler）
- Create: `src/asset_hub/repositories/state_transition.py`
- Modify: `tests/api/conftest.py`（如需）

- [ ] **Step 3.1: 加 IllegalTransitionError 异常 handler**

定位 `src/asset_hub/api/app.py` 异常 handler 段（其他 handler 已注册位置），追加：

```python
from asset_hub.errors import IllegalTransitionError  # 顶部 import 段加


@app.exception_handler(IllegalTransitionError)
async def illegal_transition_handler(request, exc: IllegalTransitionError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})
```

- [ ] **Step 3.2: 创建 TransitionRepository**

新建 `src/asset_hub/repositories/state_transition.py`：

```python
import uuid

from sqlalchemy import select
from sqlmodel import Session

from asset_hub.models.state_transition import StateTransitionRecord, TransitionKind


class TransitionRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, record: StateTransitionRecord) -> None:
        self.session.add(record)

    def list_by_asset(self, asset_id: uuid.UUID) -> list[StateTransitionRecord]:
        stmt = (
            select(StateTransitionRecord)
            .where(StateTransitionRecord.asset_id == asset_id)
            .order_by(StateTransitionRecord.created_at.desc())
        )
        return list(self.session.scalars(stmt))

    def find_open_checkout_id(self, asset_id: uuid.UUID) -> uuid.UUID | None:
        """找到该 asset 的最近一条未关闭 CHECKOUT_*（closes_transition_id 不指向它的 CHECKOUT）。

        简化：找最新的 kind=CHECKOUT_*，再确认无对应 RETURN 闭合。
        """
        # 最近的 CHECKOUT_*
        checkout_stmt = (
            select(StateTransitionRecord)
            .where(
                StateTransitionRecord.asset_id == asset_id,
                StateTransitionRecord.kind.in_(
                    [TransitionKind.CHECKOUT_INTERNAL, TransitionKind.CHECKOUT_EXTERNAL]
                ),
            )
            .order_by(StateTransitionRecord.created_at.desc())
            .limit(1)
        )
        latest_checkout = self.session.scalars(checkout_stmt).first()
        if latest_checkout is None:
            return None

        # 是否已被某条 RETURN 关闭
        return_stmt = select(StateTransitionRecord).where(
            StateTransitionRecord.closes_transition_id == latest_checkout.id
        )
        already_returned = self.session.scalars(return_stmt).first()
        if already_returned is not None:
            return None  # 已闭合，无 OPEN

        return latest_checkout.id
```

- [ ] **Step 3.3: 验证 import 通过**

Run: `uv run python -c "from asset_hub.api.app import app; from asset_hub.repositories.state_transition import TransitionRepository; print('ok')"`
Expected: `ok`

- [ ] **Step 3.4: Commit**

```bash
git add src/asset_hub/api/app.py src/asset_hub/repositories/state_transition.py
git commit -m "feat(api,repo): IllegalTransitionError → 409 handler + TransitionRepository"
```

---

### Task 4: TransitionService.record_transition + 单测

**Files:**
- Create: `src/asset_hub/services/transition.py`
- Create: `tests/unit/test_transition_service.py`

- [ ] **Step 4.1: 写 TransitionService 失败测试**

新建 `tests/unit/test_transition_service.py`：

```python
import uuid
from datetime import UTC, datetime

import pytest
from sqlmodel import Session

from asset_hub.errors import IllegalTransitionError
from asset_hub.models.asset import Asset, AssetStatus
from asset_hub.models.asset_type import AssetType
from asset_hub.models.state_transition import TransitionKind
from asset_hub.services.transition import TransitionService


@pytest.fixture
def asset_type(session: Session) -> AssetType:
    t = AssetType(name="笔记本", code_prefix="NB", custom_fields=[])
    session.add(t)
    session.commit()
    session.refresh(t)
    return t


def _new_asset(session: Session, type_id: uuid.UUID, status=AssetStatus.IDLE, holder=None, location=None) -> Asset:
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


def test_checkout_internal_transitions_idle_to_in_use(session, asset_type):
    a = _new_asset(session, asset_type.id)
    svc = TransitionService(session)

    rec = svc.record_transition(
        asset_id=a.id,
        kind=TransitionKind.CHECKOUT_INTERNAL,
        to_holder="张三",
        to_location="1F-工位",
    )

    assert rec.kind == TransitionKind.CHECKOUT_INTERNAL
    assert rec.from_status == AssetStatus.IDLE
    assert rec.to_status == AssetStatus.IN_USE
    assert rec.to_holder == "张三"
    assert rec.to_location == "1F-工位"
    session.refresh(a)
    assert a.status == AssetStatus.IN_USE
    assert a.holder == "张三"
    assert a.location == "1F-工位"


def test_return_closes_open_checkout(session, asset_type):
    a = _new_asset(session, asset_type.id)
    svc = TransitionService(session)

    co = svc.record_transition(
        asset_id=a.id,
        kind=TransitionKind.CHECKOUT_INTERNAL,
        to_holder="张三",
    )
    ret = svc.record_transition(
        asset_id=a.id,
        kind=TransitionKind.RETURN,
        to_holder="仓管李四",
        to_location="仓库",
    )

    assert ret.closes_transition_id == co.id
    assert ret.from_status == AssetStatus.IN_USE
    assert ret.to_status == AssetStatus.IDLE
    session.refresh(a)
    assert a.status == AssetStatus.IDLE
    assert a.holder == "仓管李四"  # M3a: 跟随 to_holder，不再清空
    assert a.location == "仓库"


def test_return_with_null_to_holder_sets_asset_holder_null(session, asset_type):
    a = _new_asset(session, asset_type.id)
    svc = TransitionService(session)
    svc.record_transition(asset_id=a.id, kind=TransitionKind.CHECKOUT_INTERNAL, to_holder="X")
    svc.record_transition(asset_id=a.id, kind=TransitionKind.RETURN, to_holder=None)
    session.refresh(a)
    assert a.holder is None  # 无人值守仓库


def test_return_without_open_checkout_raises(session, asset_type):
    a = _new_asset(session, asset_type.id, status=AssetStatus.IN_USE, holder="X")
    svc = TransitionService(session)
    # IN_USE 但无对应 CHECKOUT_* transition 行
    with pytest.raises(IllegalTransitionError, match="未归还"):
        svc.record_transition(asset_id=a.id, kind=TransitionKind.RETURN, to_holder="Y")


def test_dispose_forces_null_holder_location(session, asset_type):
    a = _new_asset(session, asset_type.id, status=AssetStatus.RETIRED, holder="X", location="L")
    svc = TransitionService(session)
    rec = svc.record_transition(
        asset_id=a.id,
        kind=TransitionKind.DISPOSE,
        to_holder="尝试传值",  # 应被 forced_null 覆盖
        to_location="尝试传值",
    )
    assert rec.to_holder is None
    assert rec.to_location is None
    session.refresh(a)
    assert a.status == AssetStatus.DISPOSED
    assert a.holder is None
    assert a.location is None


def test_relocate_ignores_to_holder_keeps_current(session, asset_type):
    a = _new_asset(session, asset_type.id, status=AssetStatus.IN_USE, holder="原 holder")
    svc = TransitionService(session)
    rec = svc.record_transition(
        asset_id=a.id,
        kind=TransitionKind.RELOCATE,
        to_holder="尝试改",  # ignored
        to_location="新位置",
    )
    assert rec.to_holder == "原 holder"  # 保持现 holder
    assert rec.to_location == "新位置"
    session.refresh(a)
    assert a.holder == "原 holder"
    assert a.location == "新位置"
    assert a.status == AssetStatus.IN_USE  # status 不变


def test_relocate_missing_to_location_raises(session, asset_type):
    a = _new_asset(session, asset_type.id)
    svc = TransitionService(session)
    with pytest.raises(IllegalTransitionError, match="to_location"):
        svc.record_transition(asset_id=a.id, kind=TransitionKind.RELOCATE, to_location=None)


def test_transfer_holder_required_to_holder(session, asset_type):
    a = _new_asset(session, asset_type.id, holder="原")
    svc = TransitionService(session)
    with pytest.raises(IllegalTransitionError, match="to_holder"):
        svc.record_transition(asset_id=a.id, kind=TransitionKind.TRANSFER_HOLDER, to_holder=None)


def test_send_to_maintenance_optional_fields(session, asset_type):
    a = _new_asset(session, asset_type.id)
    svc = TransitionService(session)
    rec = svc.record_transition(asset_id=a.id, kind=TransitionKind.SEND_TO_MAINTENANCE)
    assert rec.to_status == AssetStatus.MAINTENANCE
    session.refresh(a)
    assert a.status == AssetStatus.MAINTENANCE


def test_retire_from_idle(session, asset_type):
    a = _new_asset(session, asset_type.id)
    svc = TransitionService(session)
    rec = svc.record_transition(asset_id=a.id, kind=TransitionKind.RETIRE)
    assert rec.to_status == AssetStatus.RETIRED


def test_retire_from_maintenance(session, asset_type):
    a = _new_asset(session, asset_type.id, status=AssetStatus.MAINTENANCE)
    svc = TransitionService(session)
    rec = svc.record_transition(asset_id=a.id, kind=TransitionKind.RETIRE)
    assert rec.to_status == AssetStatus.RETIRED


def test_dispose_from_idle_illegal(session, asset_type):
    a = _new_asset(session, asset_type.id)
    svc = TransitionService(session)
    with pytest.raises(IllegalTransitionError):
        svc.record_transition(asset_id=a.id, kind=TransitionKind.DISPOSE)


def test_disposed_asset_cannot_transition(session, asset_type):
    a = _new_asset(session, asset_type.id, status=AssetStatus.DISPOSED)
    svc = TransitionService(session)
    with pytest.raises(IllegalTransitionError):
        svc.record_transition(asset_id=a.id, kind=TransitionKind.RELOCATE, to_location="X")


def test_due_at_only_for_checkout(session, asset_type):
    a = _new_asset(session, asset_type.id)
    svc = TransitionService(session)
    due = datetime(2026, 12, 31, tzinfo=UTC)
    co = svc.record_transition(
        asset_id=a.id,
        kind=TransitionKind.CHECKOUT_INTERNAL,
        to_holder="X",
        due_at=due,
    )
    assert co.due_at == due

    ret = svc.record_transition(
        asset_id=a.id,
        kind=TransitionKind.RETURN,
        due_at=due,  # 应被忽略
    )
    assert ret.due_at is None


def test_list_transitions_returns_desc_order(session, asset_type):
    a = _new_asset(session, asset_type.id)
    svc = TransitionService(session)
    svc.record_transition(asset_id=a.id, kind=TransitionKind.CHECKOUT_INTERNAL, to_holder="X")
    svc.record_transition(asset_id=a.id, kind=TransitionKind.RETURN)

    rows = svc.list_transitions(a.id)
    assert len(rows) == 2
    assert rows[0].kind == TransitionKind.RETURN  # 最新在前
    assert rows[1].kind == TransitionKind.CHECKOUT_INTERNAL
```

- [ ] **Step 4.2: 跑测试确认失败**

Run: `uv run pytest tests/unit/test_transition_service.py -v`
Expected: ImportError / ModuleNotFoundError（TransitionService 还没创建）

- [ ] **Step 4.3: 实现 TransitionService**

新建 `src/asset_hub/services/transition.py`：

```python
import uuid
from datetime import UTC, datetime

from sqlmodel import Session

from asset_hub.errors import IllegalTransitionError
from asset_hub.models.state_transition import StateTransitionRecord, TransitionKind
from asset_hub.repositories.state_transition import TransitionRepository
from asset_hub.services.asset import AssetService
from asset_hub.services.state_machine import TRANSITION_RULES, validate_transition


class TransitionService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = TransitionRepository(session)
        self.asset_svc = AssetService(session)

    def record_transition(
        self,
        asset_id: uuid.UUID,
        kind: TransitionKind,
        *,
        to_holder: str | None = None,
        to_location: str | None = None,
        note: str | None = None,
        due_at: datetime | None = None,
    ) -> StateTransitionRecord:
        asset = self.asset_svc.get_asset(asset_id)

        to_status = validate_transition(asset.status, kind, to_holder, to_location)
        rule = TRANSITION_RULES[kind]

        # holder/location 规则套用
        if rule.holder_rule == "forced_null":
            to_holder_final = None
        elif rule.holder_rule == "ignored":
            to_holder_final = asset.holder
        else:
            to_holder_final = to_holder

        if rule.location_rule == "forced_null":
            to_location_final = None
        else:
            to_location_final = to_location

        # 闭合最近 OPEN CHECKOUT_*（仅 RETURN 用）
        closes_id = None
        if kind == TransitionKind.RETURN:
            closes_id = self.repo.find_open_checkout_id(asset_id)
            if closes_id is None:
                raise IllegalTransitionError(f"资产无未归还的派发记录: {asset_id}")

        record = StateTransitionRecord(
            asset_id=asset_id,
            kind=kind,
            from_status=asset.status,
            to_status=to_status,
            from_holder=asset.holder,
            to_holder=to_holder_final,
            from_location=asset.location,
            to_location=to_location_final,
            note=note,
            due_at=due_at if kind in (TransitionKind.CHECKOUT_INTERNAL, TransitionKind.CHECKOUT_EXTERNAL) else None,
            closes_transition_id=closes_id,
        )
        self.repo.add(record)
        self.session.flush()

        # 更新 asset 字段
        asset.status = to_status
        asset.holder = to_holder_final
        if to_location_final is not None or rule.location_rule == "forced_null":
            asset.location = to_location_final
        asset.updated_at = datetime.now(UTC)

        self.session.commit()
        self.session.refresh(record)
        return record

    def list_transitions(self, asset_id: uuid.UUID) -> list[StateTransitionRecord]:
        self.asset_svc.get_asset(asset_id)  # 404 兜底
        return self.repo.list_by_asset(asset_id)
```

- [ ] **Step 4.4: 跑测试确认通过**

Run: `uv run pytest tests/unit/test_transition_service.py -v`
Expected: 所有 case PASS

- [ ] **Step 4.5: Commit**

```bash
git add src/asset_hub/services/transition.py tests/unit/test_transition_service.py
git commit -m "feat(service): TransitionService.record_transition 单事务（state machine 校验 → INSERT → UPDATE asset）"
```

---

### Task 5: AssetService 改造（删 change_status / 限制 update_asset / 加 list filter）

**Files:**
- Modify: `src/asset_hub/services/asset.py`
- Modify: `src/asset_hub/repositories/asset.py`（如需）
- Modify: `tests/unit/test_asset_service.py`（如已有）

- [ ] **Step 5.1: 删除 AssetService.change_status 方法**

修改 `src/asset_hub/services/asset.py`，删除：

```python
def change_status(self, asset_id: uuid.UUID, to_status: AssetStatus) -> Asset:
    ...
```

- [ ] **Step 5.2: 修订 AssetService.update_asset（移除 status/holder/location 参数）**

替换 `src/asset_hub/services/asset.py` 的 `update_asset` 方法：

```python
def update_asset(
    self,
    asset_id: uuid.UUID,
    name: str | None = None,
    serial_number: str | _Unset = _UNSET,
    notes: str | _Unset = _UNSET,
    custom_data: dict | _Unset = _UNSET,
    acquired_at: date | None | _Unset = _UNSET,
) -> Asset:
    """更新资产非状态字段。

    M3a 后 status/holder/location 不再走 PATCH——必须通过
    POST /api/assets/{id}/transitions 经 state machine 校验。
    """
    a = self.get_asset(asset_id)
    if name is not None:
        a.name = name
    if not isinstance(serial_number, _Unset):
        a.serial_number = serial_number
    if not isinstance(notes, _Unset):
        a.notes = notes
    if not isinstance(custom_data, _Unset):
        asset_type = self.type_repo.get(a.type_id)
        a.custom_data = validate_custom_data(asset_type.custom_fields, custom_data)
    if not isinstance(acquired_at, _Unset):
        a.acquired_at = acquired_at
    a.updated_at = datetime.now(UTC)
    try:
        self.session.commit()
    except IntegrityError:
        self.session.rollback()
        raise DuplicateError(f"序列号重复: {serial_number}") from None
    self.session.refresh(a)
    return a
```

同时删除文件顶部对 `AssetStatus` 和 `assert_transition_allowed` 的 import（如已不再使用）。

- [ ] **Step 5.3: 修订 AssetService.list_assets 加 include_retired/include_disposed**

替换 `list_assets` 方法：

```python
def list_assets(
    self,
    type_id: uuid.UUID | None = None,
    status: AssetStatus | None = None,
    holder: str | None = None,
    q: str | None = None,
    include_retired: bool = False,
    include_disposed: bool = False,
) -> list[Asset]:
    return self.repo.list_filtered(
        type_id=type_id,
        status=status,
        holder=holder,
        q=q,
        include_retired=include_retired,
        include_disposed=include_disposed,
    )
```

- [ ] **Step 5.4: 修订 AssetRepository.list_filtered 实现 status 过滤**

修改 `src/asset_hub/repositories/asset.py` 的 `list_filtered`，在 query 构建时加：

```python
def list_filtered(
    self,
    type_id=None,
    status=None,
    holder=None,
    q=None,
    include_retired=False,
    include_disposed=False,
) -> list[Asset]:
    stmt = select(Asset)
    if type_id:
        stmt = stmt.where(Asset.type_id == type_id)
    if status:
        stmt = stmt.where(Asset.status == status)
    else:
        # 默认隐藏 RETIRED / DISPOSED，按 toggle 决定是否包含
        excluded = []
        if not include_retired:
            excluded.append(AssetStatus.RETIRED)
        if not include_disposed:
            excluded.append(AssetStatus.DISPOSED)
        if excluded:
            stmt = stmt.where(Asset.status.notin_(excluded))
    if holder:
        stmt = stmt.where(Asset.holder == holder)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Asset.name.ilike(like), Asset.asset_code.ilike(like)))
    return list(self.session.scalars(stmt))
```

（依据现有 repo 实现细节调整：保留现有 search 字段约定，仅追加 include_* 参数与默认排除逻辑。）

- [ ] **Step 5.5: 修订 AssetService.delete_asset cascade**

修改 `src/asset_hub/services/asset.py` 的 `delete_asset`：

```python
def delete_asset(self, asset_id: uuid.UUID) -> None:
    """硬删除：cascade 清掉 StateTransitionRecord + Attachment。"""
    from sqlalchemy import delete as sa_delete

    from asset_hub.models.state_transition import StateTransitionRecord
    from asset_hub.services.attachment import AttachmentService
    from asset_hub.storage import get_default_storage

    a = self.get_asset(asset_id)

    att_svc = AttachmentService(self.session, get_default_storage())
    for att in att_svc.list(asset_id=asset_id):
        att_svc.delete(att.id)

    self.session.exec(
        sa_delete(StateTransitionRecord).where(StateTransitionRecord.asset_id == asset_id)
    )

    self.repo.delete(a)
    self.session.commit()
```

注意：删除原 `current_checkout_id = None` + `self.session.flush()` 步骤；且 cascade 表从 `CheckoutRecord` 改为 `StateTransitionRecord`。

- [ ] **Step 5.6: 跑现有 asset service 测试**

Run: `uv run pytest tests/unit/test_asset_service.py -v` （如文件不存在跳过此步）
Expected: 现有测试中如有调用 `change_status` 或 `update_asset(status=...)` 会失败——下一步修。

- [ ] **Step 5.7: 删除/修订过期测试**

如 `tests/unit/test_asset_service.py` 中存在以下测试，整体删除：

- `test_change_status_*`
- `test_update_asset_status_*`

或将其改为通过 `TransitionService.record_transition` 测试同等行为（已在 Task 4 覆盖，可直接删）。

- [ ] **Step 5.8: 跑测试确认通过**

Run: `uv run pytest tests/unit/ -v`
Expected: 全部 PASS

- [ ] **Step 5.9: Commit**

```bash
git add src/asset_hub/services/asset.py src/asset_hub/repositories/asset.py tests/unit/
git commit -m "refactor(asset-service): 删 change_status，限制 update_asset，list_assets 加 include_retired/include_disposed，cascade 切到 state_transition_records"
```

---

### Task 6: Transition DTOs + API router + 端点测试

**Files:**
- Create: `src/asset_hub/api/schemas/transition.py`
- Create: `src/asset_hub/api/routers/transitions.py`
- Modify: `src/asset_hub/api/app.py`（注册新 router；移除 checkouts router）
- Create: `tests/api/test_transitions.py`

- [ ] **Step 6.1: 写 transition DTO**

新建 `src/asset_hub/api/schemas/transition.py`：

```python
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from asset_hub.models.asset import AssetStatus
from asset_hub.models.state_transition import TransitionKind


class TransitionCreate(BaseModel):
    kind: TransitionKind
    to_holder: str | None = None
    to_location: str | None = None
    note: str | None = None
    due_at: datetime | None = None


class TransitionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    asset_id: uuid.UUID
    kind: TransitionKind
    from_status: AssetStatus
    to_status: AssetStatus
    from_holder: str | None
    to_holder: str | None
    from_location: str | None
    to_location: str | None
    note: str | None
    due_at: datetime | None
    closes_transition_id: uuid.UUID | None
    created_at: datetime
```

- [ ] **Step 6.2: 写 transitions router**

新建 `src/asset_hub/api/routers/transitions.py`：

```python
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session

from asset_hub.api.deps import get_session
from asset_hub.api.schemas.transition import TransitionCreate, TransitionRead
from asset_hub.services.transition import TransitionService

router = APIRouter()


def _get_svc(session: Annotated[Session, Depends(get_session)]) -> TransitionService:
    return TransitionService(session)


@router.post("/{asset_id}/transitions", status_code=201, response_model=TransitionRead)
def create_transition(
    asset_id: uuid.UUID,
    body: TransitionCreate,
    svc: Annotated[TransitionService, Depends(_get_svc)],
):
    return svc.record_transition(
        asset_id=asset_id,
        kind=body.kind,
        to_holder=body.to_holder,
        to_location=body.to_location,
        note=body.note,
        due_at=body.due_at,
    )


@router.get("/{asset_id}/transitions", response_model=list[TransitionRead])
def list_transitions(
    asset_id: uuid.UUID,
    svc: Annotated[TransitionService, Depends(_get_svc)],
):
    return svc.list_transitions(asset_id)
```

- [ ] **Step 6.3: 注册 router + 移除 checkouts router**

修改 `src/asset_hub/api/app.py`：

- 删除 `from asset_hub.api.routers import checkouts`（或类似 import 行）
- 删除 `app.include_router(checkouts.router, ...)`
- 加 `from asset_hub.api.routers import transitions`
- 加 `app.include_router(transitions.router, prefix="/api/assets", tags=["transitions"])`
- 同时为 assets router 的 list 端点加 `include_retired/include_disposed` query params（见 Step 6.4）

- [ ] **Step 6.4: assets router list 端点加新 query params**

修改 `src/asset_hub/api/routers/assets.py:36-44` 的 `list_assets`：

```python
@router.get("", response_model=list[AssetRead])
def list_assets(
    svc: Annotated[AssetService, Depends(_get_svc)],
    type_id: uuid.UUID | None = None,
    status: AssetStatus | None = None,
    holder: str | None = None,
    q: str | None = None,
    include_retired: bool = False,
    include_disposed: bool = False,
):
    return svc.list_assets(
        type_id=type_id,
        status=status,
        holder=holder,
        q=q,
        include_retired=include_retired,
        include_disposed=include_disposed,
    )
```

同时修订 `update_asset` 端点：删除 status/holder/location 字段在 `AssetUpdate` schema（在 `src/asset_hub/api/schemas/asset.py` 处理），改为仅接受 name/serial_number/notes/custom_data/acquired_at。

- [ ] **Step 6.5: 写 transitions API 测试**

新建 `tests/api/test_transitions.py`：

```python
import uuid

import pytest


def test_post_transition_checkout_internal(client, idle_asset):
    resp = client.post(
        f"/api/assets/{idle_asset.id}/transitions",
        json={"kind": "CHECKOUT_INTERNAL", "to_holder": "张三", "to_location": "1F"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["kind"] == "CHECKOUT_INTERNAL"
    assert body["from_status"] == "IDLE"
    assert body["to_status"] == "IN_USE"
    assert body["to_holder"] == "张三"


def test_post_transition_illegal_returns_409(client, idle_asset):
    # IDLE 不能直接 DISPOSE
    resp = client.post(
        f"/api/assets/{idle_asset.id}/transitions",
        json={"kind": "DISPOSE"},
    )
    assert resp.status_code == 409
    assert "不能从" in resp.json()["detail"]


def test_post_transition_required_field_missing_returns_409(client, idle_asset):
    resp = client.post(
        f"/api/assets/{idle_asset.id}/transitions",
        json={"kind": "CHECKOUT_INTERNAL"},  # 缺 to_holder
    )
    assert resp.status_code == 409
    assert "to_holder" in resp.json()["detail"]


def test_post_transition_404_when_asset_missing(client):
    resp = client.post(
        f"/api/assets/{uuid.uuid4()}/transitions",
        json={"kind": "CHECKOUT_INTERNAL", "to_holder": "X"},
    )
    assert resp.status_code == 404


def test_get_transitions_returns_desc_order(client, idle_asset):
    client.post(f"/api/assets/{idle_asset.id}/transitions", json={"kind": "CHECKOUT_INTERNAL", "to_holder": "X"})
    client.post(f"/api/assets/{idle_asset.id}/transitions", json={"kind": "RETURN", "to_holder": "Y"})

    resp = client.get(f"/api/assets/{idle_asset.id}/transitions")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 2
    assert rows[0]["kind"] == "RETURN"
    assert rows[1]["kind"] == "CHECKOUT_INTERNAL"


def test_get_transitions_404_when_asset_missing(client):
    resp = client.get(f"/api/assets/{uuid.uuid4()}/transitions")
    assert resp.status_code == 404


def test_list_assets_default_excludes_retired_and_disposed(client, idle_asset, retired_asset, disposed_asset):
    resp = client.get("/api/assets")
    assert resp.status_code == 200
    statuses = [a["status"] for a in resp.json()]
    assert "IDLE" in statuses
    assert "RETIRED" not in statuses
    assert "DISPOSED" not in statuses


def test_list_assets_include_retired(client, idle_asset, retired_asset):
    resp = client.get("/api/assets?include_retired=true")
    assert resp.status_code == 200
    statuses = [a["status"] for a in resp.json()]
    assert "RETIRED" in statuses


def test_list_assets_include_disposed(client, idle_asset, disposed_asset):
    resp = client.get("/api/assets?include_disposed=true")
    assert resp.status_code == 200
    statuses = [a["status"] for a in resp.json()]
    assert "DISPOSED" in statuses
```

- [ ] **Step 6.6: 在 `tests/api/conftest.py` 加 fixture**

修改/新增 `tests/api/conftest.py`：

```python
@pytest.fixture
def idle_asset(client, asset_type):
    resp = client.post(
        "/api/assets",
        json={
            "name": "测试笔记本",
            "type_id": str(asset_type.id),
            "custom_data": {},
        },
    )
    assert resp.status_code == 201
    return type("AssetRef", (), {"id": resp.json()["id"]})()


@pytest.fixture
def retired_asset(client, idle_asset):
    client.post(
        f"/api/assets/{idle_asset.id}/transitions",
        json={"kind": "RETIRE"},
    )
    return idle_asset


@pytest.fixture
def disposed_asset(client, asset_type):
    resp = client.post("/api/assets", json={"name": "处置", "type_id": str(asset_type.id), "custom_data": {}})
    aid = resp.json()["id"]
    client.post(f"/api/assets/{aid}/transitions", json={"kind": "RETIRE"})
    client.post(f"/api/assets/{aid}/transitions", json={"kind": "DISPOSE"})
    return type("AssetRef", (), {"id": aid})()
```

- [ ] **Step 6.7: 跑 API 测试**

Run: `uv run pytest tests/api/test_transitions.py -v`
Expected: 全部 PASS

- [ ] **Step 6.8: Commit**

```bash
git add src/asset_hub/api/schemas/transition.py src/asset_hub/api/routers/transitions.py src/asset_hub/api/app.py src/asset_hub/api/routers/assets.py src/asset_hub/api/schemas/asset.py tests/api/
git commit -m "feat(api): POST/GET /api/assets/{id}/transitions + list 加 include_retired/include_disposed + 移除 checkouts router"
```

---

### Task 7: 删除旧 Checkout 链路文件

**Files:**
- Delete: `src/asset_hub/services/checkout.py`
- Delete: `src/asset_hub/repositories/checkout.py`
- Delete: `src/asset_hub/api/routers/checkouts.py`
- Delete: `src/asset_hub/api/schemas/checkout.py`
- Delete: `src/asset_hub/models/checkout.py`
- Delete: `tests/unit/test_checkout*.py`、`tests/api/test_checkout*.py`、`tests/cli/test_checkout*.py`（如有）

- [ ] **Step 7.1: 删除文件**

```bash
git rm src/asset_hub/services/checkout.py src/asset_hub/repositories/checkout.py src/asset_hub/api/routers/checkouts.py src/asset_hub/api/schemas/checkout.py src/asset_hub/models/checkout.py
```

如有以下测试文件存在亦删：

```bash
git rm tests/unit/test_checkout*.py tests/api/test_checkout*.py tests/cli/test_checkout*.py
```

（用 `git ls-files | grep -i checkout` 确认范围。）

- [ ] **Step 7.2: 检查 import 残留**

Run: `uv run python -c "from asset_hub.api.app import app"`
Expected: 不报 ImportError；如报错按提示删除残留 import 行（最常见在 `tests/conftest.py` 或 `services/__init__.py`）

Run: `grep -rn "from asset_hub.models.checkout\|from asset_hub.services.checkout\|from asset_hub.repositories.checkout\|from asset_hub.api.schemas.checkout\|from asset_hub.api.routers.checkouts" src/ tests/`
Expected: 0 命中

- [ ] **Step 7.3: 跑全部测试**

Run: `uv run pytest`
Expected: 全部 PASS（旧 checkout 测试已删；新 transition 测试通过）

- [ ] **Step 7.4: Commit**

```bash
git add -A
git commit -m "chore: 删除旧 CheckoutRecord/CheckoutService/CheckoutRepository + checkouts router/schemas + 相关测试"
```

---

### Task 8: CLI 重构（保留命令名 + 改实现） + 测试

**Files:**
- Modify: `src/asset_hub/cli/asset_cmd.py`（重构 checkout/return/history；删 change-status；新增 7 命令）
- Create: `tests/cli/test_transition_cmds.py`

- [ ] **Step 8.1: 顶部 import 修订**

修改 `src/asset_hub/cli/asset_cmd.py` 顶部 import：

```python
import json
from datetime import date, datetime
from typing import Annotated

import typer

from asset_hub.api.schemas.asset import AssetRead
from asset_hub.api.schemas.transition import TransitionRead
from asset_hub.cli.deps import cli_session, parse_enum, parse_uuid
from asset_hub.cli.envelope import (
    handle_domain_errors,
    print_dry_run,
    print_result,
    to_json_dict,
)
from asset_hub.models.asset import AssetStatus
from asset_hub.models.state_transition import TransitionKind
from asset_hub.services.asset import AssetService
from asset_hub.services.transition import TransitionService
```

删除 `from asset_hub.api.schemas.checkout import CheckoutRead` 与 `from asset_hub.services.checkout import CheckoutService`。

- [ ] **Step 8.2: 重写 asset checkout（带 --kind flag）**

替换 `src/asset_hub/cli/asset_cmd.py` 现有 `asset_checkout` 命令：

```python
@asset_app.command("checkout")
def asset_checkout(
    asset_id: Annotated[str, typer.Argument(help="资产 UUID")],
    to: Annotated[str, typer.Option("--to", help="派发给谁（保管人）")],
    kind: Annotated[
        str, typer.Option("--kind", help="派发类型：internal=组内派发，external=出借给外部")
    ] = "internal",
    location: Annotated[str | None, typer.Option(help="位置")] = None,
    note: Annotated[str | None, typer.Option(help="备注")] = None,
    due_at: Annotated[
        str | None, typer.Option("--due-at", help="期望归还时间（ISO8601）")
    ] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """派发资产（kind: internal 内部派发 / external 对外出借）。"""
    uid = parse_uuid(asset_id, json_output)
    kind_map = {
        "internal": TransitionKind.CHECKOUT_INTERNAL,
        "external": TransitionKind.CHECKOUT_EXTERNAL,
    }
    if kind not in kind_map:
        raise typer.BadParameter(f"--kind 必须是 internal 或 external，得到: {kind}")
    parsed_due = datetime.fromisoformat(due_at) if due_at else None

    with cli_session() as session, handle_domain_errors(json_output):
        svc = TransitionService(session)
        rec = svc.record_transition(
            asset_id=uid,
            kind=kind_map[kind],
            to_holder=to,
            to_location=location,
            note=note,
            due_at=parsed_due,
        )
    print_result(to_json_dict(TransitionRead, rec), json_output)
```

- [ ] **Step 8.3: 重写 asset return（保留 --receiver 兼容）**

替换 `asset_return` 命令：

```python
@asset_app.command("return")
def asset_return(
    asset_id: Annotated[str, typer.Argument(help="资产 UUID")],
    receiver: Annotated[
        str | None, typer.Option("--receiver", help="归还接收人/仓管（成为新 holder）")
    ] = None,
    location: Annotated[str | None, typer.Option(help="归还位置")] = None,
    note: Annotated[str | None, typer.Option(help="归还备注")] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """归还资产（--receiver 是归还接收人，归还后成为新 holder；不传则资产无 holder）。"""
    uid = parse_uuid(asset_id, json_output)

    with cli_session() as session, handle_domain_errors(json_output):
        svc = TransitionService(session)
        rec = svc.record_transition(
            asset_id=uid,
            kind=TransitionKind.RETURN,
            to_holder=receiver,
            to_location=location,
            note=note,
        )
    print_result(to_json_dict(TransitionRead, rec), json_output)
```

- [ ] **Step 8.4: 重写 asset history**

替换 `asset_history` 命令：

```python
@asset_app.command("history")
def asset_history(
    asset_id: Annotated[str, typer.Argument(help="资产 UUID")],
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """查看资产流转历史（10 transition kind 全覆盖）。"""
    uid = parse_uuid(asset_id, json_output)
    with cli_session() as session, handle_domain_errors(json_output):
        svc = TransitionService(session)
        records = svc.list_transitions(asset_id=uid)
    data = [to_json_dict(TransitionRead, r) for r in records]
    print_result(data, json_output, count=len(data))
```

- [ ] **Step 8.5: 删除 asset change-status 命令**

删除 `src/asset_hub/cli/asset_cmd.py` 中 `asset_change_status` 整个函数定义。

- [ ] **Step 8.6: 加 send-to-maintenance 命令**

append 到 `src/asset_hub/cli/asset_cmd.py`：

```python
def _record_simple_transition(
    asset_id: str,
    kind: TransitionKind,
    *,
    holder: str | None = None,
    location: str | None = None,
    note: str | None = None,
    json_output: bool = False,
) -> None:
    """通用 transition 命令封装（无特殊参数的 kind 共用）。"""
    uid = parse_uuid(asset_id, json_output)
    with cli_session() as session, handle_domain_errors(json_output):
        svc = TransitionService(session)
        rec = svc.record_transition(
            asset_id=uid,
            kind=kind,
            to_holder=holder,
            to_location=location,
            note=note,
        )
    print_result(to_json_dict(TransitionRead, rec), json_output)


@asset_app.command("send-to-maintenance")
def asset_send_to_maintenance(
    asset_id: Annotated[str, typer.Argument(help="资产 UUID")],
    holder: Annotated[str | None, typer.Option(help="维修联系人")] = None,
    location: Annotated[str | None, typer.Option(help="维修地点")] = None,
    note: Annotated[str | None, typer.Option(help="备注")] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """送修。"""
    _record_simple_transition(
        asset_id, TransitionKind.SEND_TO_MAINTENANCE,
        holder=holder, location=location, note=note, json_output=json_output,
    )
```

- [ ] **Step 8.7: 加 recover / reinstate 命令**

append：

```python
@asset_app.command("recover")
def asset_recover(
    asset_id: Annotated[str, typer.Argument(help="资产 UUID")],
    holder: Annotated[str | None, typer.Option(help="新保管人/仓管")] = None,
    location: Annotated[str | None, typer.Option(help="新位置")] = None,
    note: Annotated[str | None, typer.Option(help="备注")] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """维修完成回库。"""
    _record_simple_transition(
        asset_id, TransitionKind.RECOVER_FROM_MAINTENANCE,
        holder=holder, location=location, note=note, json_output=json_output,
    )


@asset_app.command("reinstate")
def asset_reinstate(
    asset_id: Annotated[str, typer.Argument(help="资产 UUID")],
    holder: Annotated[str | None, typer.Option(help="新保管人/仓管")] = None,
    location: Annotated[str | None, typer.Option(help="新位置")] = None,
    note: Annotated[str | None, typer.Option(help="备注")] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """重新启用（从已退役回到闲置）。"""
    _record_simple_transition(
        asset_id, TransitionKind.REINSTATE,
        holder=holder, location=location, note=note, json_output=json_output,
    )
```

- [ ] **Step 8.8: 加 retire 命令（带 --dry-run）**

append：

```python
@asset_app.command("retire")
def asset_retire(
    asset_id: Annotated[str, typer.Argument(help="资产 UUID")],
    holder: Annotated[str | None, typer.Option(help="备件库管理员")] = None,
    location: Annotated[str | None, typer.Option(help="存放位置")] = None,
    note: Annotated[str | None, typer.Option(help="备注")] = None,
    yes: Annotated[bool, typer.Option("--yes", help="跳过确认")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="预览，不实际执行")] = False,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """退役（可通过 reinstate 复活）。"""
    uid = parse_uuid(asset_id, json_output)
    with cli_session() as session, handle_domain_errors(json_output):
        asset_svc = AssetService(session)
        a = asset_svc.get_asset(uid)

        if dry_run:
            print_dry_run(
                {"would_retire": to_json_dict(AssetRead, a)},
                json_output,
                message=f"将退役 {a.name} ({a.id})",
            )
            return

        if not yes:
            confirm = typer.confirm(f"确定退役 {a.name}?")
            if not confirm:
                raise typer.Abort()

        svc = TransitionService(session)
        rec = svc.record_transition(
            asset_id=uid, kind=TransitionKind.RETIRE,
            to_holder=holder, to_location=location, note=note,
        )
    print_result(to_json_dict(TransitionRead, rec), json_output)
```

- [ ] **Step 8.9: 加 dispose 命令（终态，带 --dry-run + 二次确认）**

append：

```python
@asset_app.command("dispose")
def asset_dispose(
    asset_id: Annotated[str, typer.Argument(help="资产 UUID")],
    note: Annotated[str | None, typer.Option(help="备注")] = None,
    yes: Annotated[bool, typer.Option("--yes", help="跳过确认")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="预览，不实际执行")] = False,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """处置（终态，不可撤销，holder/location 将被清空）。仅可从 RETIRED/MAINTENANCE 出发。"""
    uid = parse_uuid(asset_id, json_output)
    with cli_session() as session, handle_domain_errors(json_output):
        asset_svc = AssetService(session)
        a = asset_svc.get_asset(uid)

        if dry_run:
            print_dry_run(
                {"would_dispose": to_json_dict(AssetRead, a)},
                json_output,
                message=f"将处置 {a.name} ({a.id})（终态、不可撤销）",
            )
            return

        if not yes:
            confirm = typer.confirm(
                f"⚠️ 确定处置 {a.name}？此操作不可撤销，holder 与 location 将被清空。"
            )
            if not confirm:
                raise typer.Abort()

        svc = TransitionService(session)
        rec = svc.record_transition(
            asset_id=uid, kind=TransitionKind.DISPOSE, note=note,
        )
    print_result(to_json_dict(TransitionRead, rec), json_output)
```

- [ ] **Step 8.10: 加 relocate / transfer-holder 命令**

append：

```python
@asset_app.command("relocate")
def asset_relocate(
    asset_id: Annotated[str, typer.Argument(help="资产 UUID")],
    to_location: Annotated[str, typer.Option("--to-location", help="新位置（必填）")],
    note: Annotated[str | None, typer.Option(help="备注")] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """变更资产位置（不改 status，holder 保持不变）。"""
    uid = parse_uuid(asset_id, json_output)
    with cli_session() as session, handle_domain_errors(json_output):
        svc = TransitionService(session)
        rec = svc.record_transition(
            asset_id=uid, kind=TransitionKind.RELOCATE,
            to_location=to_location, note=note,
        )
    print_result(to_json_dict(TransitionRead, rec), json_output)


@asset_app.command("transfer-holder")
def asset_transfer_holder(
    asset_id: Annotated[str, typer.Argument(help="资产 UUID")],
    to_holder: Annotated[str, typer.Option("--to-holder", help="新保管人（必填）")],
    location: Annotated[str | None, typer.Option(help="同时变更位置")] = None,
    note: Annotated[str | None, typer.Option(help="备注")] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """变更资产保管人（不改 status，可同时变更位置）。"""
    uid = parse_uuid(asset_id, json_output)
    with cli_session() as session, handle_domain_errors(json_output):
        svc = TransitionService(session)
        rec = svc.record_transition(
            asset_id=uid, kind=TransitionKind.TRANSFER_HOLDER,
            to_holder=to_holder, to_location=location, note=note,
        )
    print_result(to_json_dict(TransitionRead, rec), json_output)
```

- [ ] **Step 8.11: 写 CLI transition 命令测试**

新建 `tests/cli/test_transition_cmds.py`：

```python
import json
import uuid

import pytest
from typer.testing import CliRunner

from asset_hub.cli.main import app

runner = CliRunner()


@pytest.fixture
def idle_asset_id(isolated_db):
    """通过 CLI 创建一个 IDLE 资产，返回 id。"""
    # 先建 type
    res = runner.invoke(app, [
        "type", "define", "--name", "笔记本", "--prefix", "NB", "--json",
    ])
    assert res.exit_code == 0
    # 再建 asset
    res = runner.invoke(app, [
        "asset", "register",
        "--name", "测试机",
        "--type-id", json.loads(res.stdout)["data"]["id"],
        "--json",
    ])
    assert res.exit_code == 0
    return json.loads(res.stdout)["data"]["id"]


def test_checkout_internal_default_kind(idle_asset_id):
    res = runner.invoke(app, [
        "asset", "checkout", idle_asset_id,
        "--to", "张三", "--json",
    ])
    assert res.exit_code == 0
    body = json.loads(res.stdout)
    assert body["success"] is True
    assert body["data"]["kind"] == "CHECKOUT_INTERNAL"
    assert body["data"]["to_holder"] == "张三"


def test_checkout_external_with_kind_flag(idle_asset_id):
    res = runner.invoke(app, [
        "asset", "checkout", idle_asset_id,
        "--to", "客户A", "--kind", "external", "--json",
    ])
    assert res.exit_code == 0
    assert json.loads(res.stdout)["data"]["kind"] == "CHECKOUT_EXTERNAL"


def test_checkout_invalid_kind_returns_error(idle_asset_id):
    res = runner.invoke(app, [
        "asset", "checkout", idle_asset_id,
        "--to", "X", "--kind", "weird", "--json",
    ])
    assert res.exit_code != 0


def test_return_after_checkout(idle_asset_id):
    runner.invoke(app, ["asset", "checkout", idle_asset_id, "--to", "X", "--json"])
    res = runner.invoke(app, [
        "asset", "return", idle_asset_id,
        "--receiver", "仓管", "--json",
    ])
    assert res.exit_code == 0
    body = json.loads(res.stdout)
    assert body["data"]["kind"] == "RETURN"
    assert body["data"]["to_holder"] == "仓管"


def test_return_without_open_checkout_exits_1(idle_asset_id):
    res = runner.invoke(app, [
        "asset", "return", idle_asset_id, "--json",
    ])
    assert res.exit_code == 1
    body = json.loads(res.stdout)
    assert body["success"] is False


def test_send_to_maintenance(idle_asset_id):
    res = runner.invoke(app, [
        "asset", "send-to-maintenance", idle_asset_id, "--json",
    ])
    assert res.exit_code == 0
    assert json.loads(res.stdout)["data"]["to_status"] == "MAINTENANCE"


def test_recover_after_maintenance(idle_asset_id):
    runner.invoke(app, ["asset", "send-to-maintenance", idle_asset_id, "--json"])
    res = runner.invoke(app, ["asset", "recover", idle_asset_id, "--json"])
    assert res.exit_code == 0
    assert json.loads(res.stdout)["data"]["to_status"] == "IDLE"


def test_retire_with_yes(idle_asset_id):
    res = runner.invoke(app, [
        "asset", "retire", idle_asset_id, "--yes", "--json",
    ])
    assert res.exit_code == 0
    assert json.loads(res.stdout)["data"]["to_status"] == "RETIRED"


def test_retire_dry_run_does_not_change_status(idle_asset_id):
    res = runner.invoke(app, [
        "asset", "retire", idle_asset_id, "--dry-run", "--json",
    ])
    assert res.exit_code == 10  # dry-run 退出码
    # 资产仍然是 IDLE
    res2 = runner.invoke(app, ["asset", "show", idle_asset_id, "--json"])
    assert json.loads(res2.stdout)["data"]["status"] == "IDLE"


def test_reinstate_after_retire(idle_asset_id):
    runner.invoke(app, ["asset", "retire", idle_asset_id, "--yes", "--json"])
    res = runner.invoke(app, ["asset", "reinstate", idle_asset_id, "--json"])
    assert res.exit_code == 0
    assert json.loads(res.stdout)["data"]["to_status"] == "IDLE"


def test_dispose_from_retired_with_yes(idle_asset_id):
    runner.invoke(app, ["asset", "retire", idle_asset_id, "--yes", "--json"])
    res = runner.invoke(app, [
        "asset", "dispose", idle_asset_id, "--yes", "--json",
    ])
    assert res.exit_code == 0
    body = json.loads(res.stdout)
    assert body["data"]["to_status"] == "DISPOSED"
    assert body["data"]["to_holder"] is None
    assert body["data"]["to_location"] is None


def test_dispose_from_idle_exits_1(idle_asset_id):
    res = runner.invoke(app, [
        "asset", "dispose", idle_asset_id, "--yes", "--json",
    ])
    assert res.exit_code == 1


def test_relocate(idle_asset_id):
    res = runner.invoke(app, [
        "asset", "relocate", idle_asset_id,
        "--to-location", "新仓库", "--json",
    ])
    assert res.exit_code == 0
    body = json.loads(res.stdout)
    assert body["data"]["kind"] == "RELOCATE"
    assert body["data"]["to_location"] == "新仓库"


def test_transfer_holder(idle_asset_id):
    res = runner.invoke(app, [
        "asset", "transfer-holder", idle_asset_id,
        "--to-holder", "李四", "--json",
    ])
    assert res.exit_code == 0
    body = json.loads(res.stdout)
    assert body["data"]["kind"] == "TRANSFER_HOLDER"
    assert body["data"]["to_holder"] == "李四"


def test_history_after_multiple_transitions(idle_asset_id):
    runner.invoke(app, ["asset", "checkout", idle_asset_id, "--to", "X", "--json"])
    runner.invoke(app, ["asset", "return", idle_asset_id, "--json"])
    res = runner.invoke(app, ["asset", "history", idle_asset_id, "--json"])
    assert res.exit_code == 0
    body = json.loads(res.stdout)
    assert body["metadata"]["count"] == 2


def test_change_status_command_removed(idle_asset_id):
    """change-status 命令在 M3a 已删除。"""
    res = runner.invoke(app, [
        "asset", "change-status", idle_asset_id, "--to", "MAINTENANCE",
    ])
    assert res.exit_code != 0  # 命令不存在
```

- [ ] **Step 8.12: 跑 CLI 测试**

Run: `uv run pytest tests/cli/test_transition_cmds.py -v`
Expected: 全部 PASS

- [ ] **Step 8.13: Commit**

```bash
git add src/asset_hub/cli/asset_cmd.py tests/cli/test_transition_cmds.py
git commit -m "feat(cli): 9 transition 命令重构（保留 checkout/return/history 命令名 + 新增 7 命令）+ 删 change-status"
```

---

### Task 9: Alembic schema migration

**Files:**
- Create: `src/asset_hub/alembic/versions/<new>_m3a_state_machine.py`

- [ ] **Step 9.1: 用户手动清空测试数据库**

⚠️ **此步必须在生成 migration 之前手动执行**：

```bash
rm -f data/asset_hub.db
rm -rf data/attachments/*
```

如未执行，autogenerate 可能因旧 checkout_records 表的现有数据而生成错误的 migration。

- [ ] **Step 9.2: 生成 alembic migration**

Run: `uv run alembic revision --autogenerate -m "m3a_state_machine"`
Expected: 在 `src/asset_hub/alembic/versions/` 生成新文件

- [ ] **Step 9.3: 检查并校正生成的 migration**

打开新生成的 migration 文件，确认 `upgrade()` 包含（且**仅**包含）以下操作：

```python
def upgrade() -> None:
    # 1. 加 DISPOSED 到 status enum（SQLite 走 batch mode）
    with op.batch_alter_table("assets") as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=sa.Enum("IN_USE", "IDLE", "MAINTENANCE", "RETIRED", name="assetstatus"),
            type_=sa.Enum("IN_USE", "IDLE", "MAINTENANCE", "RETIRED", "DISPOSED", name="assetstatus"),
            existing_nullable=False,
        )
        batch_op.drop_index("ix_assets_current_checkout_id")
        batch_op.drop_column("current_checkout_id")

    # 2. 删 checkout_records 表
    op.drop_index("ix_one_open_checkout_per_asset", table_name="checkout_records")
    op.drop_index("ix_checkout_records_asset_id", table_name="checkout_records")
    op.drop_index("ix_checkout_records_returned_at", table_name="checkout_records")
    op.drop_table("checkout_records")

    # 3. 建 state_transition_records 表
    op.create_table(
        "state_transition_records",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("asset_id", sa.UUID(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "CHECKOUT_INTERNAL", "CHECKOUT_EXTERNAL", "RETURN",
                "SEND_TO_MAINTENANCE", "RECOVER_FROM_MAINTENANCE",
                "RETIRE", "REINSTATE", "DISPOSE",
                "RELOCATE", "TRANSFER_HOLDER",
                name="transitionkind",
            ),
            nullable=False,
        ),
        sa.Column(
            "from_status",
            sa.Enum("IN_USE", "IDLE", "MAINTENANCE", "RETIRED", "DISPOSED", name="assetstatus"),
            nullable=False,
        ),
        sa.Column(
            "to_status",
            sa.Enum("IN_USE", "IDLE", "MAINTENANCE", "RETIRED", "DISPOSED", name="assetstatus"),
            nullable=False,
        ),
        sa.Column("from_holder", sa.String(), nullable=True),
        sa.Column("to_holder", sa.String(), nullable=True),
        sa.Column("from_location", sa.String(), nullable=True),
        sa.Column("to_location", sa.String(), nullable=True),
        sa.Column("note", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("due_at", sa.DateTime(), nullable=True),
        sa.Column("closes_transition_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.ForeignKeyConstraint(["closes_transition_id"], ["state_transition_records.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_state_transition_records_asset_id", "state_transition_records", ["asset_id"])
    op.create_index("ix_state_transition_records_created_at", "state_transition_records", ["created_at"])
    op.create_index("ix_state_transition_records_closes_transition_id", "state_transition_records", ["closes_transition_id"])
    op.create_index("ix_transition_asset_created", "state_transition_records", ["asset_id", "created_at"])
```

`downgrade()` 反向（drop state_transition_records、recreate checkout_records、回退 status enum）。

- [ ] **Step 9.4: 用 ruff 格式化 migration**

Run: `uv run ruff format src/asset_hub/alembic/versions/`
Expected: migration 文件被格式化

- [ ] **Step 9.5: 跑 migration**

Run: `uv run alembic upgrade head`
Expected: migration 应用成功，`data/asset_hub.db` 创建（如不存在）

- [ ] **Step 9.6: 验证 schema**

Run: `uv run python -c "import sqlite3; con = sqlite3.connect('data/asset_hub.db'); cur = con.cursor(); print([r[0] for r in cur.execute('SELECT name FROM sqlite_master WHERE type=\"table\"').fetchall()])"`
Expected: `['assets', 'asset_types', 'attachments', 'state_transition_records', 'alembic_version']`（无 `checkout_records`）

- [ ] **Step 9.7: 跑全部测试**

Run: `uv run pytest`
Expected: 全部 PASS

- [ ] **Step 9.8: Commit**

```bash
git add src/asset_hub/alembic/versions/
git commit -m "feat(migration): m3a 纯 schema 变更（add DISPOSED enum / create state_transition_records / drop checkout_records / drop Asset.current_checkout_id）"
```

---

### Task 10: 前端 OpenAPI schema 重新生成（PR-1 末步）

**Files:**
- Modify: `frontend/src/api/generated/schema.d.ts`（自动生成）

- [ ] **Step 10.1: 启动后端 dev server**

Run: `uv run uvicorn asset_hub.api.app:app --reload &`（背景运行；确保 :8000 可访问）

或新开一个 terminal 跑（确保 server 起到 :8000）。

- [ ] **Step 10.2: 重新生成 frontend types**

Run: `pnpm --dir frontend gen:api`
Expected: `frontend/src/api/generated/schema.d.ts` 重新生成（含 transition 端点 + AssetStatus 5 态 + TransitionKind 10 值）

- [ ] **Step 10.3: 关闭后端 dev server**

```bash
# 找到 uvicorn 进程并 kill；如用 asset-hub serve 启动则 asset-hub serve stop
```

- [ ] **Step 10.4: 验证 schema 内容**

Run: `grep -c '"DISPOSED"' frontend/src/api/generated/schema.d.ts`
Expected: ≥ 1（DISPOSED 出现在 enum 中）

Run: `grep -c '"CHECKOUT_INTERNAL"' frontend/src/api/generated/schema.d.ts`
Expected: ≥ 1（TransitionKind 已生成）

Run: `grep -c '"/api/assets/{asset_id}/transitions"' frontend/src/api/generated/schema.d.ts`
Expected: ≥ 1（端点路径已生成）

- [ ] **Step 10.5: Commit（PR-1 完整快照）**

```bash
git add frontend/src/api/generated/schema.d.ts
git commit -m "chore(frontend): 重新生成 schema.d.ts 以匹配 M3a 后端 API（含 5 态 + 10 transition kind + transitions 端点）"
```

---

### Task 11: PR-1 验收清单

**Files:** 无文件改动；用作 checklist。

- [ ] **Step 11.1: 跑全部后端测试**

Run: `uv run pytest -v`
Expected: 全部 PASS（约 50-70 新增 transition 相关 case + 现有测试不退化）

- [ ] **Step 11.2: lint**

Run: `uv run ruff check .`
Expected: 0 issue

- [ ] **Step 11.3: 验证 alembic 双向**

Run: `uv run alembic downgrade -1 && uv run alembic upgrade head`
Expected: 双向均成功

- [ ] **Step 11.4: 手工烟测 CLI（每个新命令一次）**

```bash
uv run asset-hub type define --name 笔记本 --prefix NB --json
# 拿到 type id
uv run asset-hub asset register --name 测试机 --type-id <id> --json
# 拿到 asset id
uv run asset-hub asset checkout <aid> --to 张三 --json
uv run asset-hub asset return <aid> --receiver 仓管 --json
uv run asset-hub asset send-to-maintenance <aid> --json
uv run asset-hub asset recover <aid> --json
uv run asset-hub asset relocate <aid> --to-location 仓库 --json
uv run asset-hub asset transfer-holder <aid> --to-holder 王五 --json
uv run asset-hub asset retire <aid> --yes --json
uv run asset-hub asset reinstate <aid> --json
uv run asset-hub asset retire <aid> --yes --json
uv run asset-hub asset dispose <aid> --yes --json
uv run asset-hub asset history <aid> --json
```

每个命令应 exit 0 + envelope `success: true`。

- [ ] **Step 11.5: 手工烟测 API**

Run: `uv run uvicorn asset_hub.api.app:app --reload &` 在另一 terminal：

```bash
curl http://localhost:8000/openapi.json | grep -o "transitions" | head -1
# 验证 IllegalTransitionError 返回 409：
# 创建一个 IDLE asset，然后尝试 DISPOSE：
# curl -X POST http://localhost:8000/api/assets/<id>/transitions -H 'Content-Type: application/json' -d '{"kind":"DISPOSE"}'
# 期待 status 409
```

- [ ] **Step 11.6: PR-1 push + 创建 PR**

```bash
git log --oneline main..HEAD  # 确认 commit 链
git push -u origin <branch>
gh pr create --title "M3a PR-1: 状态机基建（后端契约 + schema migration）" --body "..."
```

PR 描述应包含：
- M3a spec 链接
- PR-1 范围（task 1-10）
- 测试结果（pytest 全绿 + alembic 双向）
- 已知影响：`pnpm gen:api` 已跑；前端 ts 类型有变更，PR-2 修复消费侧

---


