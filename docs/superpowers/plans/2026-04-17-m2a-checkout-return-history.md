# M2a · 流转（checkout / return / history）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 M1 骨架上实现资产的派发（checkout）、归还（return）、历史查询（history），覆盖 service / CLI / API 三层，严格保证「单个资产至多一条未归还记录」。

**Architecture:** 新增 `CheckoutRecord` 表 + 部分唯一索引（`UNIQUE(asset_id) WHERE returned_at IS NULL`）。`CheckoutService` 作为唯一事实源，在同事务内写入 checkout 记录并副作用更新 `Asset.status / holder / location`。CLI 通过 `asset checkout/return/history` 暴露，API 通过 `/api/assets/{id}/{checkout|return|history}` 暴露。

**Tech Stack:** 沿用 M1（Python 3.12 + FastAPI + SQLModel + Typer + pytest）。新增用法：SQLAlchemy 的部分索引 `Index(..., sqlite_where=text(...))`。

## 关键决策（先读再动手）

1. **放弃 spec §5.1 的 `Asset.current_checkout_id` 外键**。维护双向指针成本大于价值，"当前未归还记录" 通过 `SELECT ... WHERE asset_id=X AND returned_at IS NULL LIMIT 1` 查询得出。单一事实源在 `CheckoutRecord`，不需要在 Asset 上再冗余。
2. **部分唯一索引兜底业务不变量**：`CheckoutRecord` 上建 `UNIQUE(asset_id) WHERE returned_at IS NULL`。service 层会先显式检查并抛友好错误，但数据库层兜底防止并发窗口。
3. **新增 `StateError` 域异常，API 层映射到 409 Conflict**。区别于 `ValidationError`（输入格式问题，422）：状态冲突（如「资产已派发」）是业务规则问题，语义上 409 更准确。
4. **状态约束**：只有 `IDLE` 资产可以被 checkout；`RETIRED` / `MAINTENANCE` / `IN_USE` 都抛 `StateError`。return 要求存在未归还记录，否则抛 `StateError`。
5. **Service 返回值** 全部是 `CheckoutRecord` 或其列表；Asset 的副作用更新是同事务内完成的隐式效果，调用方如需最新 Asset 自行再读（API/CLI 测试里验证这一点）。
6. **Commit message 规范** 遵循全局 Angular 约定，中文 subject，**不**附带工具标记或 Co-Authored-By。

---

## 文件结构

M2a 结束后，相关新增/修改如下：

```
asset-hub/
├── src/asset_hub/
│   ├── errors.py                                  # 修改：新增 StateError
│   │
│   ├── models/
│   │   ├── __init__.py                            # 修改：注册 CheckoutRecord
│   │   └── checkout.py                            # 新增：CheckoutRecord + 部分唯一索引
│   │
│   ├── repositories/
│   │   └── checkout.py                            # 新增：CheckoutRepository
│   │
│   ├── services/
│   │   └── checkout.py                            # 新增：CheckoutService
│   │
│   ├── api/
│   │   ├── app.py                                 # 修改：StateError→409 handler + 挂载 checkouts 路由
│   │   ├── schemas/
│   │   │   └── checkout.py                        # 新增：CheckoutCreate/CheckoutReturn/CheckoutRead
│   │   └── routers/
│   │       └── checkouts.py                       # 新增：派发/归还/历史 端点
│   │
│   └── cli/
│       └── asset_cmd.py                           # 修改：新增 checkout / return / history 子命令
│
└── tests/
    ├── unit/
    │   ├── test_checkout_model.py                 # 新增：模型 smoke + 部分唯一索引
    │   └── test_checkout_service.py               # 新增：service 行为
    ├── cli/
    │   └── test_asset_checkout_cli.py             # 新增：CLI 信封 + 退出码
    └── api/
        └── test_checkout_routes.py                # 新增：HTTP 状态码与响应
```

---

## Task 1: 模型 + 异常 + 异常映射

**Files:**
- Create: `src/asset_hub/models/checkout.py`
- Modify: `src/asset_hub/models/__init__.py`
- Modify: `src/asset_hub/errors.py`
- Modify: `src/asset_hub/api/app.py`
- Create: `tests/unit/test_checkout_model.py`

- [ ] **Step 1.1: 写失败测试（模型 smoke + 部分唯一索引）**

Create `tests/unit/test_checkout_model.py`:

```python
from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from asset_hub.models.asset import Asset
from asset_hub.models.asset_type import AssetType
from asset_hub.models.checkout import CheckoutRecord


def _make_asset(session: Session) -> Asset:
    t = AssetType(name="T", custom_fields=[])
    session.add(t)
    session.flush()
    a = Asset(name="A", type_id=t.id, custom_data={})
    session.add(a)
    session.commit()
    session.refresh(a)
    return a


def test_checkout_record_can_be_persisted(session: Session):
    a = _make_asset(session)
    rec = CheckoutRecord(
        asset_id=a.id,
        holder="张三",
        location="工位 5",
        checkout_note="借用一周",
    )
    session.add(rec)
    session.commit()
    session.refresh(rec)

    assert rec.id is not None
    assert rec.returned_at is None
    assert isinstance(rec.checked_out_at, datetime)


def test_partial_unique_index_blocks_second_open_checkout(session: Session):
    a = _make_asset(session)
    session.add(CheckoutRecord(asset_id=a.id, holder="张三"))
    session.commit()

    session.add(CheckoutRecord(asset_id=a.id, holder="李四"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_closed_checkout_allows_new_open_checkout(session: Session):
    a = _make_asset(session)
    first = CheckoutRecord(asset_id=a.id, holder="张三")
    session.add(first)
    session.commit()

    first.returned_at = datetime.now(UTC)
    session.add(first)
    session.commit()

    session.add(CheckoutRecord(asset_id=a.id, holder="李四"))
    session.commit()  # 不应抛异常
```

- [ ] **Step 1.2: 运行测试确认失败**

Run: `uv run pytest tests/unit/test_checkout_model.py -v`

Expected: `ModuleNotFoundError: No module named 'asset_hub.models.checkout'`

- [ ] **Step 1.3: 创建 CheckoutRecord 模型**

Create `src/asset_hub/models/checkout.py`:

```python
import uuid
from datetime import UTC, datetime

from sqlalchemy import Index, text
from sqlmodel import Field, SQLModel


class CheckoutRecord(SQLModel, table=True):
    __tablename__ = "checkout_records"
    __table_args__ = (
        Index(
            "ix_one_open_checkout_per_asset",
            "asset_id",
            unique=True,
            sqlite_where=text("returned_at IS NULL"),
            postgresql_where=text("returned_at IS NULL"),
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    asset_id: uuid.UUID = Field(foreign_key="assets.id", index=True)
    holder: str
    location: str | None = None
    checked_out_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    returned_at: datetime | None = Field(default=None, index=True)
    checkout_note: str | None = None
    return_note: str | None = None
```

- [ ] **Step 1.4: 注册到 models/__init__.py**

Overwrite `src/asset_hub/models/__init__.py` with:

```python
# 汇总导出，确保 SQLModel.metadata.create_all 能发现所有表模型
from asset_hub.models.asset import Asset, AssetStatus
from asset_hub.models.asset_type import AssetType
from asset_hub.models.checkout import CheckoutRecord

__all__ = ["Asset", "AssetStatus", "AssetType", "CheckoutRecord"]
```

- [ ] **Step 1.5: 运行模型测试确认通过**

Run: `uv run pytest tests/unit/test_checkout_model.py -v`

Expected: 3 tests PASS

- [ ] **Step 1.6: 新增 StateError**

Modify `src/asset_hub/errors.py`, append at end:

```python
class StateError(AssetHubError):
    """业务规则冲突：对象存在，但当前状态不允许此操作。

    例：对 IN_USE 资产再次派发；对无未归还记录的资产归还。"""
    pass
```

- [ ] **Step 1.7: 在 API 层注册 StateError → 409 映射**

Modify `src/asset_hub/api/app.py`:

- 修改导入行，从 `from asset_hub.errors import DuplicateError, NotFoundError, ValidationError` 改为：

```python
from asset_hub.errors import DuplicateError, NotFoundError, StateError, ValidationError
```

- 在 `duplicate_handler` 与 `validation_handler` 之间（顺序不影响功能，但保持读起来自然），新增 handler：

```python
    @app.exception_handler(StateError)
    async def state_handler(request: Request, exc: StateError):
        return JSONResponse(status_code=409, content={"detail": str(exc)})
```

- [ ] **Step 1.8: 回归全量测试**

Run: `uv run pytest -q`

Expected: 既有 M1 测试全部通过 + 新 3 条模型测试通过。

- [ ] **Step 1.9: 提交**

```bash
git add src/asset_hub/models/checkout.py src/asset_hub/models/__init__.py src/asset_hub/errors.py src/asset_hub/api/app.py tests/unit/test_checkout_model.py
git commit -m "$(cat <<'EOF'
feat(model): 新增 CheckoutRecord 与 StateError

- CheckoutRecord 表：asset_id/holder/location/两端时间戳/两端备注
- 部分唯一索引 ix_one_open_checkout_per_asset 保证单资产至多一个未归还
- StateError 域异常，API 层映射到 409 Conflict
EOF
)"
```

---

## Task 2: CheckoutRepository + CheckoutService.checkout() (TDD)

**Files:**
- Create: `src/asset_hub/repositories/checkout.py`
- Create: `src/asset_hub/services/checkout.py`
- Create: `tests/unit/test_checkout_service.py`

- [ ] **Step 2.1: 写失败测试**

Create `tests/unit/test_checkout_service.py`:

```python
from uuid import uuid4

import pytest
from sqlmodel import Session

from asset_hub.errors import NotFoundError, StateError
from asset_hub.models.asset import AssetStatus
from asset_hub.services.asset import AssetService
from asset_hub.services.asset_type import TypeService
from asset_hub.services.checkout import CheckoutService


@pytest.fixture()
def type_svc(session: Session) -> TypeService:
    return TypeService(session)


@pytest.fixture()
def asset_svc(session: Session) -> AssetService:
    return AssetService(session)


@pytest.fixture()
def checkout_svc(session: Session) -> CheckoutService:
    return CheckoutService(session)


@pytest.fixture()
def simple_type(type_svc: TypeService):
    return type_svc.create_type(name="笔记本", custom_fields=[])


@pytest.fixture()
def idle_asset(asset_svc: AssetService, simple_type):
    return asset_svc.register(name="X1", type_id=simple_type.id, custom_data={})


class TestCheckout:
    def test_checkout_idle_asset(
        self,
        checkout_svc: CheckoutService,
        asset_svc: AssetService,
        idle_asset,
    ):
        rec = checkout_svc.checkout(
            asset_id=idle_asset.id,
            holder="张三",
            location="工位 5",
            note="借用一周",
        )

        assert rec.asset_id == idle_asset.id
        assert rec.holder == "张三"
        assert rec.location == "工位 5"
        assert rec.checkout_note == "借用一周"
        assert rec.returned_at is None

        updated = asset_svc.get_asset(idle_asset.id)
        assert updated.status == AssetStatus.IN_USE
        assert updated.holder == "张三"
        assert updated.location == "工位 5"

    def test_checkout_nonexistent_raises(self, checkout_svc: CheckoutService):
        with pytest.raises(NotFoundError):
            checkout_svc.checkout(asset_id=uuid4(), holder="张三")

    def test_checkout_already_in_use_raises(
        self,
        checkout_svc: CheckoutService,
        idle_asset,
    ):
        checkout_svc.checkout(asset_id=idle_asset.id, holder="张三")
        with pytest.raises(StateError, match="已派发"):
            checkout_svc.checkout(asset_id=idle_asset.id, holder="李四")

    def test_checkout_retired_raises(
        self,
        checkout_svc: CheckoutService,
        asset_svc: AssetService,
        idle_asset,
    ):
        asset_svc.update_asset(idle_asset.id, status=AssetStatus.RETIRED)
        with pytest.raises(StateError, match="RETIRED"):
            checkout_svc.checkout(asset_id=idle_asset.id, holder="张三")

    def test_checkout_maintenance_raises(
        self,
        checkout_svc: CheckoutService,
        asset_svc: AssetService,
        idle_asset,
    ):
        asset_svc.update_asset(idle_asset.id, status=AssetStatus.MAINTENANCE)
        with pytest.raises(StateError, match="MAINTENANCE"):
            checkout_svc.checkout(asset_id=idle_asset.id, holder="张三")

    def test_checkout_location_optional(
        self,
        checkout_svc: CheckoutService,
        idle_asset,
    ):
        rec = checkout_svc.checkout(asset_id=idle_asset.id, holder="张三")
        assert rec.location is None
        assert rec.checkout_note is None
```

- [ ] **Step 2.2: 运行测试确认失败**

Run: `uv run pytest tests/unit/test_checkout_service.py -v`

Expected: `ModuleNotFoundError: No module named 'asset_hub.services.checkout'`

- [ ] **Step 2.3: 创建 CheckoutRepository**

Create `src/asset_hub/repositories/checkout.py`:

```python
import uuid

from sqlmodel import Session, select

from asset_hub.models.checkout import CheckoutRecord


class CheckoutRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, record: CheckoutRecord) -> CheckoutRecord:
        self.session.add(record)
        self.session.flush()
        return record

    def find_open_by_asset(self, asset_id: uuid.UUID) -> CheckoutRecord | None:
        stmt = (
            select(CheckoutRecord)
            .where(CheckoutRecord.asset_id == asset_id)
            .where(CheckoutRecord.returned_at.is_(None))
        )
        return self.session.exec(stmt).first()

    def list_by_asset(self, asset_id: uuid.UUID) -> list[CheckoutRecord]:
        stmt = (
            select(CheckoutRecord)
            .where(CheckoutRecord.asset_id == asset_id)
            .order_by(CheckoutRecord.checked_out_at.desc())
        )
        return list(self.session.exec(stmt).all())
```

- [ ] **Step 2.4: 创建 CheckoutService.checkout()**

Create `src/asset_hub/services/checkout.py`:

```python
import uuid
from datetime import UTC, datetime

from sqlmodel import Session

from asset_hub.errors import NotFoundError, StateError
from asset_hub.models.asset import AssetStatus
from asset_hub.models.checkout import CheckoutRecord
from asset_hub.repositories.asset import AssetRepository
from asset_hub.repositories.checkout import CheckoutRepository


class CheckoutService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = CheckoutRepository(session)
        self.asset_repo = AssetRepository(session)

    def checkout(
        self,
        asset_id: uuid.UUID,
        holder: str,
        location: str | None = None,
        note: str | None = None,
    ) -> CheckoutRecord:
        asset = self.asset_repo.get(asset_id)
        if asset is None:
            raise NotFoundError(f"资产不存在: {asset_id}")

        if asset.status == AssetStatus.IN_USE:
            raise StateError(f"资产已派发，请先归还: {asset_id}")
        if asset.status in (AssetStatus.RETIRED, AssetStatus.MAINTENANCE):
            raise StateError(
                f"资产状态 {asset.status.value} 不允许派发: {asset_id}"
            )

        record = CheckoutRecord(
            asset_id=asset_id,
            holder=holder,
            location=location,
            checkout_note=note,
        )
        self.repo.add(record)

        asset.status = AssetStatus.IN_USE
        asset.holder = holder
        asset.location = location
        asset.updated_at = datetime.now(UTC)

        self.session.commit()
        self.session.refresh(record)
        return record
```

- [ ] **Step 2.5: 运行测试确认通过**

Run: `uv run pytest tests/unit/test_checkout_service.py -v`

Expected: 6 tests PASS

- [ ] **Step 2.6: 提交**

```bash
git add src/asset_hub/repositories/checkout.py src/asset_hub/services/checkout.py tests/unit/test_checkout_service.py
git commit -m "$(cat <<'EOF'
feat(service): CheckoutService.checkout — 派发资产并更新状态

- CheckoutRepository 封装常用查询（find_open_by_asset / list_by_asset）
- checkout 校验：资产存在、非 IN_USE / RETIRED / MAINTENANCE
- 同事务内创建 CheckoutRecord 并更新 Asset.status/holder/location
EOF
)"
```

---

## Task 3: CheckoutService.return_() (TDD)

**Files:**
- Modify: `src/asset_hub/services/checkout.py`
- Modify: `tests/unit/test_checkout_service.py`

- [ ] **Step 3.1: 追加失败测试**

Append to `tests/unit/test_checkout_service.py`:

```python
class TestReturn:
    def test_return_closes_record(
        self,
        checkout_svc: CheckoutService,
        asset_svc: AssetService,
        idle_asset,
    ):
        checkout_svc.checkout(
            asset_id=idle_asset.id, holder="张三", location="工位 5"
        )
        rec = checkout_svc.return_(asset_id=idle_asset.id, note="完好")

        assert rec.returned_at is not None
        assert rec.return_note == "完好"

        updated = asset_svc.get_asset(idle_asset.id)
        assert updated.status == AssetStatus.IDLE
        assert updated.holder is None
        assert updated.location is None

    def test_return_without_open_checkout_raises(
        self,
        checkout_svc: CheckoutService,
        idle_asset,
    ):
        with pytest.raises(StateError, match="无未归还"):
            checkout_svc.return_(asset_id=idle_asset.id)

    def test_return_nonexistent_raises(self, checkout_svc: CheckoutService):
        with pytest.raises(NotFoundError):
            checkout_svc.return_(asset_id=uuid4())

    def test_return_allows_recheckout(
        self,
        checkout_svc: CheckoutService,
        idle_asset,
    ):
        checkout_svc.checkout(asset_id=idle_asset.id, holder="张三")
        checkout_svc.return_(asset_id=idle_asset.id)
        rec = checkout_svc.checkout(asset_id=idle_asset.id, holder="李四")
        assert rec.holder == "李四"
```

- [ ] **Step 3.2: 运行测试确认失败**

Run: `uv run pytest tests/unit/test_checkout_service.py::TestReturn -v`

Expected: `AttributeError: 'CheckoutService' object has no attribute 'return_'`

- [ ] **Step 3.3: 实现 return_**

Append to `src/asset_hub/services/checkout.py`:

```python
    def return_(
        self,
        asset_id: uuid.UUID,
        note: str | None = None,
    ) -> CheckoutRecord:
        asset = self.asset_repo.get(asset_id)
        if asset is None:
            raise NotFoundError(f"资产不存在: {asset_id}")

        record = self.repo.find_open_by_asset(asset_id)
        if record is None:
            raise StateError(f"资产无未归还记录: {asset_id}")

        record.returned_at = datetime.now(UTC)
        record.return_note = note

        asset.status = AssetStatus.IDLE
        asset.holder = None
        asset.location = None
        asset.updated_at = datetime.now(UTC)

        self.session.commit()
        self.session.refresh(record)
        return record
```

- [ ] **Step 3.4: 运行测试确认通过**

Run: `uv run pytest tests/unit/test_checkout_service.py -v`

Expected: 10 tests PASS（6 + 4）

- [ ] **Step 3.5: 提交**

```bash
git add src/asset_hub/services/checkout.py tests/unit/test_checkout_service.py
git commit -m "feat(service): CheckoutService.return_ — 归还并复位资产状态"
```

---

## Task 4: CheckoutService.history() (TDD)

**Files:**
- Modify: `src/asset_hub/services/checkout.py`
- Modify: `tests/unit/test_checkout_service.py`

- [ ] **Step 4.1: 追加失败测试**

Append to `tests/unit/test_checkout_service.py`:

```python
class TestHistory:
    def test_history_empty(
        self,
        checkout_svc: CheckoutService,
        idle_asset,
    ):
        assert checkout_svc.history(asset_id=idle_asset.id) == []

    def test_history_lists_all_records_newest_first(
        self,
        checkout_svc: CheckoutService,
        idle_asset,
    ):
        first = checkout_svc.checkout(asset_id=idle_asset.id, holder="张三")
        checkout_svc.return_(asset_id=idle_asset.id)
        second = checkout_svc.checkout(asset_id=idle_asset.id, holder="李四")

        records = checkout_svc.history(asset_id=idle_asset.id)

        assert [r.id for r in records] == [second.id, first.id]
        assert records[0].returned_at is None
        assert records[1].returned_at is not None

    def test_history_nonexistent_asset_raises(
        self, checkout_svc: CheckoutService
    ):
        with pytest.raises(NotFoundError):
            checkout_svc.history(asset_id=uuid4())
```

- [ ] **Step 4.2: 运行测试确认失败**

Run: `uv run pytest tests/unit/test_checkout_service.py::TestHistory -v`

Expected: `AttributeError: 'CheckoutService' object has no attribute 'history'`

- [ ] **Step 4.3: 实现 history**

Append to `src/asset_hub/services/checkout.py`:

```python
    def history(self, asset_id: uuid.UUID) -> list[CheckoutRecord]:
        asset = self.asset_repo.get(asset_id)
        if asset is None:
            raise NotFoundError(f"资产不存在: {asset_id}")
        return self.repo.list_by_asset(asset_id)
```

- [ ] **Step 4.4: 运行测试确认通过**

Run: `uv run pytest tests/unit/test_checkout_service.py -v`

Expected: 13 tests PASS

- [ ] **Step 4.5: 提交**

```bash
git add src/asset_hub/services/checkout.py tests/unit/test_checkout_service.py
git commit -m "feat(service): CheckoutService.history — 按派发时间倒序返回记录"
```

---

## Task 5: CheckoutRead DTO + CLI `asset checkout` (TDD)

**Files:**
- Create: `src/asset_hub/api/schemas/checkout.py`
- Modify: `src/asset_hub/cli/asset_cmd.py`
- Create: `tests/cli/test_asset_checkout_cli.py`

- [ ] **Step 5.1: 写失败测试**

Create `tests/cli/test_asset_checkout_cli.py`:

```python
import json
from uuid import uuid4

from typer.testing import CliRunner

from asset_hub.cli.main import app

runner = CliRunner()


def _define_type_and_asset() -> tuple[str, str]:
    r = runner.invoke(app, ["type", "define", "--name", "笔记本", "--json"])
    type_id = json.loads(r.stdout)["data"]["id"]
    r = runner.invoke(app, [
        "asset", "register", "--name", "X1", "--type-id", type_id, "--json",
    ])
    asset_id = json.loads(r.stdout)["data"]["id"]
    return type_id, asset_id


class TestAssetCheckout:
    def test_checkout_idle_asset(self):
        _, asset_id = _define_type_and_asset()
        result = runner.invoke(app, [
            "asset", "checkout", asset_id,
            "--to", "张三",
            "--location", "工位 5",
            "--note", "借用一周",
            "--json",
        ])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert data["data"]["holder"] == "张三"
        assert data["data"]["location"] == "工位 5"
        assert data["data"]["checkout_note"] == "借用一周"
        assert data["data"]["returned_at"] is None

        r = runner.invoke(app, ["asset", "show", asset_id, "--json"])
        shown = json.loads(r.stdout)["data"]
        assert shown["status"] == "IN_USE"
        assert shown["holder"] == "张三"

    def test_checkout_nonexistent_exits_3(self):
        result = runner.invoke(app, [
            "asset", "checkout", str(uuid4()),
            "--to", "张三", "--json",
        ])
        assert result.exit_code == 3

    def test_checkout_already_in_use_exits_1(self):
        _, asset_id = _define_type_and_asset()
        runner.invoke(app, [
            "asset", "checkout", asset_id, "--to", "张三", "--json",
        ])
        result = runner.invoke(app, [
            "asset", "checkout", asset_id, "--to", "李四", "--json",
        ])
        assert result.exit_code == 1
        data = json.loads(result.stdout)
        assert data["success"] is False
        assert "已派发" in data["error"]

    def test_checkout_bad_uuid_exits_2(self):
        result = runner.invoke(app, [
            "asset", "checkout", "not-a-uuid",
            "--to", "张三", "--json",
        ])
        assert result.exit_code == 2
```

- [ ] **Step 5.2: 运行测试确认失败**

Run: `uv run pytest tests/cli/test_asset_checkout_cli.py -v`

Expected: 全部失败（typer 报 "No such command 'checkout'"，exit_code 非 0）

- [ ] **Step 5.3: 创建 checkout DTO**

Create `src/asset_hub/api/schemas/checkout.py`:

```python
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CheckoutCreate(BaseModel):
    holder: str
    location: str | None = None
    note: str | None = None


class CheckoutReturn(BaseModel):
    note: str | None = None


class CheckoutRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    asset_id: UUID
    holder: str
    location: str | None
    checked_out_at: datetime
    returned_at: datetime | None
    checkout_note: str | None
    return_note: str | None
```

- [ ] **Step 5.4: 修改 asset_cmd.py — 导入**

Modify `src/asset_hub/cli/asset_cmd.py`:

- 将现有的
  ```python
  from asset_hub.errors import DuplicateError, NotFoundError, ValidationError
  ```
  替换为
  ```python
  from asset_hub.errors import DuplicateError, NotFoundError, StateError, ValidationError
  ```

- 在已有的 `from asset_hub.services.asset import AssetService` 之后追加：
  ```python
  from asset_hub.api.schemas.checkout import CheckoutRead
  from asset_hub.services.checkout import CheckoutService
  ```

- [ ] **Step 5.5: 修改 asset_cmd.py — 新增序列化帮助函数**

在 `_asset_to_dict` 下方追加：

```python
def _checkout_to_dict(r) -> dict:
    return CheckoutRead.model_validate(r).model_dump(mode="json")
```

- [ ] **Step 5.6: 修改 asset_cmd.py — 新增 checkout 命令**

在文件末尾追加：

```python
@asset_app.command("checkout")
def asset_checkout(
    asset_id: Annotated[str, typer.Argument(help="资产 UUID")],
    to: Annotated[str, typer.Option("--to", help="派发给谁（保管人）")],
    location: Annotated[str | None, typer.Option(help="位置")] = None,
    note: Annotated[str | None, typer.Option(help="派发备注")] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """派发资产给某人。"""
    uid = parse_uuid(asset_id, json_output)
    with cli_session() as session:
        svc = CheckoutService(session)
        try:
            rec = svc.checkout(asset_id=uid, holder=to, location=location, note=note)
        except NotFoundError as e:
            print_error(str(e), json_output, exit_code=3)
            return
        except StateError as e:
            print_error(str(e), json_output, exit_code=1)
            return
    print_result(_checkout_to_dict(rec), json_output)
```

- [ ] **Step 5.7: 运行测试确认通过**

Run: `uv run pytest tests/cli/test_asset_checkout_cli.py -v`

Expected: 4 tests PASS

- [ ] **Step 5.8: 提交**

```bash
git add src/asset_hub/api/schemas/checkout.py src/asset_hub/cli/asset_cmd.py tests/cli/test_asset_checkout_cli.py
git commit -m "feat(cli): asset checkout 命令 + CheckoutRead DTO"
```

---

## Task 6: CLI `asset return` (TDD)

**Files:**
- Modify: `src/asset_hub/cli/asset_cmd.py`
- Modify: `tests/cli/test_asset_checkout_cli.py`

- [ ] **Step 6.1: 追加失败测试**

Append to `tests/cli/test_asset_checkout_cli.py`:

```python
class TestAssetReturn:
    def test_return_closes_checkout(self):
        _, asset_id = _define_type_and_asset()
        runner.invoke(app, [
            "asset", "checkout", asset_id, "--to", "张三", "--json",
        ])
        result = runner.invoke(app, [
            "asset", "return", asset_id, "--note", "完好", "--json",
        ])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["data"]["returned_at"] is not None
        assert data["data"]["return_note"] == "完好"

        r = runner.invoke(app, ["asset", "show", asset_id, "--json"])
        shown = json.loads(r.stdout)["data"]
        assert shown["status"] == "IDLE"
        assert shown["holder"] is None

    def test_return_without_open_exits_1(self):
        _, asset_id = _define_type_and_asset()
        result = runner.invoke(app, [
            "asset", "return", asset_id, "--json",
        ])
        assert result.exit_code == 1
        data = json.loads(result.stdout)
        assert "无未归还" in data["error"]

    def test_return_nonexistent_exits_3(self):
        result = runner.invoke(app, [
            "asset", "return", str(uuid4()), "--json",
        ])
        assert result.exit_code == 3
```

- [ ] **Step 6.2: 运行测试确认失败**

Run: `uv run pytest tests/cli/test_asset_checkout_cli.py::TestAssetReturn -v`

Expected: 全部失败（"No such command 'return'"）

- [ ] **Step 6.3: 实现 CLI return 命令**

Append to `src/asset_hub/cli/asset_cmd.py`:

```python
@asset_app.command("return")
def asset_return(
    asset_id: Annotated[str, typer.Argument(help="资产 UUID")],
    note: Annotated[str | None, typer.Option(help="归还备注")] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """归还资产。"""
    uid = parse_uuid(asset_id, json_output)
    with cli_session() as session:
        svc = CheckoutService(session)
        try:
            rec = svc.return_(asset_id=uid, note=note)
        except NotFoundError as e:
            print_error(str(e), json_output, exit_code=3)
            return
        except StateError as e:
            print_error(str(e), json_output, exit_code=1)
            return
    print_result(_checkout_to_dict(rec), json_output)
```

- [ ] **Step 6.4: 运行测试确认通过**

Run: `uv run pytest tests/cli/test_asset_checkout_cli.py -v`

Expected: 7 tests PASS

- [ ] **Step 6.5: 提交**

```bash
git add src/asset_hub/cli/asset_cmd.py tests/cli/test_asset_checkout_cli.py
git commit -m "feat(cli): asset return 命令"
```

---

## Task 7: CLI `asset history` (TDD)

**Files:**
- Modify: `src/asset_hub/cli/asset_cmd.py`
- Modify: `tests/cli/test_asset_checkout_cli.py`

- [ ] **Step 7.1: 追加失败测试**

Append to `tests/cli/test_asset_checkout_cli.py`:

```python
class TestAssetHistory:
    def test_history_empty(self):
        _, asset_id = _define_type_and_asset()
        result = runner.invoke(app, [
            "asset", "history", asset_id, "--json",
        ])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["data"] == []
        assert data["metadata"]["count"] == 0

    def test_history_lists_records(self):
        _, asset_id = _define_type_and_asset()
        runner.invoke(app, ["asset", "checkout", asset_id, "--to", "张三", "--json"])
        runner.invoke(app, ["asset", "return", asset_id, "--json"])
        runner.invoke(app, ["asset", "checkout", asset_id, "--to", "李四", "--json"])

        result = runner.invoke(app, ["asset", "history", asset_id, "--json"])
        data = json.loads(result.stdout)
        assert data["metadata"]["count"] == 2
        assert data["data"][0]["holder"] == "李四"
        assert data["data"][1]["holder"] == "张三"

    def test_history_nonexistent_exits_3(self):
        result = runner.invoke(app, [
            "asset", "history", str(uuid4()), "--json",
        ])
        assert result.exit_code == 3
```

- [ ] **Step 7.2: 运行测试确认失败**

Run: `uv run pytest tests/cli/test_asset_checkout_cli.py::TestAssetHistory -v`

Expected: 全部失败（"No such command 'history'"）

- [ ] **Step 7.3: 实现 CLI history 命令**

Append to `src/asset_hub/cli/asset_cmd.py`:

```python
@asset_app.command("history")
def asset_history(
    asset_id: Annotated[str, typer.Argument(help="资产 UUID")],
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """查看资产流转历史。"""
    uid = parse_uuid(asset_id, json_output)
    with cli_session() as session:
        svc = CheckoutService(session)
        try:
            records = svc.history(asset_id=uid)
        except NotFoundError as e:
            print_error(str(e), json_output, exit_code=3)
            return
    data = [_checkout_to_dict(r) for r in records]
    print_result(data, json_output, count=len(data))
```

- [ ] **Step 7.4: 运行测试确认通过**

Run: `uv run pytest tests/cli/test_asset_checkout_cli.py -v`

Expected: 10 tests PASS

- [ ] **Step 7.5: 提交**

```bash
git add src/asset_hub/cli/asset_cmd.py tests/cli/test_asset_checkout_cli.py
git commit -m "feat(cli): asset history 命令"
```

---

## Task 8: API 路由（checkout / return / history）(TDD)

**Files:**
- Create: `src/asset_hub/api/routers/checkouts.py`
- Modify: `src/asset_hub/api/app.py`
- Create: `tests/api/test_checkout_routes.py`

- [ ] **Step 8.1: 写失败测试**

Create `tests/api/test_checkout_routes.py`:

```python
from uuid import uuid4

from fastapi.testclient import TestClient


def _create_type_and_asset(client: TestClient) -> str:
    r = client.post("/api/types", json={"name": "笔记本"})
    type_id = r.json()["id"]
    r = client.post("/api/assets", json={
        "name": "X1", "type_id": type_id, "custom_data": {},
    })
    return r.json()["id"]


class TestCheckoutEndpoint:
    def test_checkout_idle_asset(self, client: TestClient):
        asset_id = _create_type_and_asset(client)
        resp = client.post(f"/api/assets/{asset_id}/checkout", json={
            "holder": "张三",
            "location": "工位 5",
            "note": "借用一周",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["holder"] == "张三"
        assert data["location"] == "工位 5"
        assert data["checkout_note"] == "借用一周"
        assert data["returned_at"] is None

        r = client.get(f"/api/assets/{asset_id}")
        assert r.json()["status"] == "IN_USE"

    def test_checkout_nonexistent_404(self, client: TestClient):
        resp = client.post(f"/api/assets/{uuid4()}/checkout", json={
            "holder": "张三",
        })
        assert resp.status_code == 404

    def test_checkout_already_in_use_409(self, client: TestClient):
        asset_id = _create_type_and_asset(client)
        client.post(f"/api/assets/{asset_id}/checkout", json={"holder": "张三"})
        resp = client.post(f"/api/assets/{asset_id}/checkout", json={"holder": "李四"})
        assert resp.status_code == 409


class TestReturnEndpoint:
    def test_return_closes_checkout(self, client: TestClient):
        asset_id = _create_type_and_asset(client)
        client.post(f"/api/assets/{asset_id}/checkout", json={"holder": "张三"})
        resp = client.post(f"/api/assets/{asset_id}/return", json={"note": "完好"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["returned_at"] is not None
        assert data["return_note"] == "完好"

        r = client.get(f"/api/assets/{asset_id}")
        assert r.json()["status"] == "IDLE"

    def test_return_without_open_409(self, client: TestClient):
        asset_id = _create_type_and_asset(client)
        resp = client.post(f"/api/assets/{asset_id}/return", json={})
        assert resp.status_code == 409

    def test_return_nonexistent_404(self, client: TestClient):
        resp = client.post(f"/api/assets/{uuid4()}/return", json={})
        assert resp.status_code == 404


class TestHistoryEndpoint:
    def test_history_empty(self, client: TestClient):
        asset_id = _create_type_and_asset(client)
        resp = client.get(f"/api/assets/{asset_id}/history")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_history_lists_records(self, client: TestClient):
        asset_id = _create_type_and_asset(client)
        client.post(f"/api/assets/{asset_id}/checkout", json={"holder": "张三"})
        client.post(f"/api/assets/{asset_id}/return", json={})
        client.post(f"/api/assets/{asset_id}/checkout", json={"holder": "李四"})

        resp = client.get(f"/api/assets/{asset_id}/history")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["holder"] == "李四"
        assert data[1]["holder"] == "张三"

    def test_history_nonexistent_404(self, client: TestClient):
        resp = client.get(f"/api/assets/{uuid4()}/history")
        assert resp.status_code == 404
```

- [ ] **Step 8.2: 运行测试确认失败**

Run: `uv run pytest tests/api/test_checkout_routes.py -v`

Expected: 全部 404（endpoint 尚未挂载）

- [ ] **Step 8.3: 创建 routers/checkouts.py**

Create `src/asset_hub/api/routers/checkouts.py`:

```python
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session

from asset_hub.api.deps import get_session
from asset_hub.api.schemas.checkout import (
    CheckoutCreate,
    CheckoutRead,
    CheckoutReturn,
)
from asset_hub.services.checkout import CheckoutService

router = APIRouter()


def _get_svc(session: Annotated[Session, Depends(get_session)]) -> CheckoutService:
    return CheckoutService(session)


@router.post("/{asset_id}/checkout", status_code=201, response_model=CheckoutRead)
def checkout_asset(
    asset_id: uuid.UUID,
    body: CheckoutCreate,
    svc: Annotated[CheckoutService, Depends(_get_svc)],
):
    return svc.checkout(
        asset_id=asset_id,
        holder=body.holder,
        location=body.location,
        note=body.note,
    )


@router.post("/{asset_id}/return", response_model=CheckoutRead)
def return_asset(
    asset_id: uuid.UUID,
    body: CheckoutReturn,
    svc: Annotated[CheckoutService, Depends(_get_svc)],
):
    return svc.return_(asset_id=asset_id, note=body.note)


@router.get("/{asset_id}/history", response_model=list[CheckoutRead])
def asset_history(
    asset_id: uuid.UUID,
    svc: Annotated[CheckoutService, Depends(_get_svc)],
):
    return svc.history(asset_id=asset_id)
```

- [ ] **Step 8.4: 挂载路由**

Modify `src/asset_hub/api/app.py`:

- 修改 router 导入行：
  从
  ```python
  from asset_hub.api.routers import assets, types
  ```
  改为
  ```python
  from asset_hub.api.routers import assets, checkouts, types
  ```

- 在 `app.include_router(assets.router, prefix="/api/assets", tags=["assets"])` 之后追加：

  ```python
      app.include_router(checkouts.router, prefix="/api/assets", tags=["checkouts"])
  ```

- [ ] **Step 8.5: 运行测试确认通过**

Run: `uv run pytest tests/api/test_checkout_routes.py -v`

Expected: 9 tests PASS

- [ ] **Step 8.6: 回归全量测试**

Run: `uv run pytest -q`

Expected: M1 + M2a 全部测试通过，无回归。

- [ ] **Step 8.7: 提交**

```bash
git add src/asset_hub/api/routers/checkouts.py src/asset_hub/api/app.py tests/api/test_checkout_routes.py
git commit -m "feat(api): 派发/归还/历史端点 /api/assets/{id}/{checkout,return,history}"
```

---

## Task 9: 收尾（lint + 手工烟测）

本任务不写新测试；目标是确保 lint 干净、OpenAPI schema 暴露新端点、CLI 可实际调用。

- [ ] **Step 9.1: ruff 检查**

Run: `uv run ruff check .`

Expected: `All checks passed!`。若有报错，修复后重新运行。

- [ ] **Step 9.2: 全量测试（详细输出便于对照）**

Run: `uv run pytest -v`

Expected: 全绿；新增测试合计 ≥ 22（模型 3 + service 13 + CLI 10 + API 9 = 35）。

- [ ] **Step 9.3: 手工烟测 CLI**

```bash
# 使用临时 DATA_DIR 避免污染真实数据
export ASSET_HUB_DATA_DIR=/tmp/asset-hub-smoke
rm -rf "$ASSET_HUB_DATA_DIR" && mkdir -p "$ASSET_HUB_DATA_DIR"

TYPE_ID=$(uv run asset-hub type define --name "笔记本" --json | python -c "import sys,json; print(json.load(sys.stdin)['data']['id'])")
ASSET_ID=$(uv run asset-hub asset register --name "X1" --type-id "$TYPE_ID" --json | python -c "import sys,json; print(json.load(sys.stdin)['data']['id'])")

# 派发
uv run asset-hub asset checkout "$ASSET_ID" --to 张三 --location "工位 5" --json
# 期望：success=true、holder=张三

uv run asset-hub asset show "$ASSET_ID" --json
# 期望：status=IN_USE, holder=张三

# 再派发应失败
uv run asset-hub asset checkout "$ASSET_ID" --to 李四 --json
echo "exit=$?"
# 期望：success=false、error 含「已派发」、exit=1

# 归还
uv run asset-hub asset return "$ASSET_ID" --note "完好" --json

# 查询历史
uv run asset-hub asset history "$ASSET_ID" --json
# 期望：count=1，returned_at 非 null
```

- [ ] **Step 9.4: 手工烟测 OpenAPI**

```bash
uv run uvicorn asset_hub.api.app:app --port 8000 &
UVICORN_PID=$!
sleep 1
curl -s http://localhost:8000/openapi.json | python -c "
import sys, json
spec = json.load(sys.stdin)
paths = list(spec['paths'].keys())
expected = [
    '/api/assets/{asset_id}/checkout',
    '/api/assets/{asset_id}/return',
    '/api/assets/{asset_id}/history',
]
for p in expected:
    assert p in paths, f'missing: {p}'
print('OK:', expected)
"
kill $UVICORN_PID
```

Expected: `OK: [...三条路径...]`。

- [ ] **Step 9.5: 若有修复，提交收尾**

如有 lint 或其它无害修正：

```bash
git add -u
git commit -m "chore: M2a 收尾——lint 与格式修正"
```

若无改动跳过此步骤。

---

## 自检清单

| 需求 / 来源                                                           | 对应 Task                                                               |
| --------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| `CheckoutRecord` 表结构（spec §5.2）                                  | Task 1                                                                  |
| 「每资产至多一个未归还」不变量                                        | Task 1（部分唯一索引）+ Task 2（service 预校验）                        |
| 派发：IDLE → IN_USE，记录 holder/location/note                        | Task 2                                                                  |
| 归还：IN_USE → IDLE，写 returned_at/return_note，清空 holder/location | Task 3                                                                  |
| 历史时间线（spec §5.2 / §6.1）                                        | Task 4（service）+ Task 7（CLI）+ Task 8（API）                         |
| CLI `asset checkout / return / history`（spec §6.1）                  | Task 5–7                                                                |
| CLI `--json` 标准信封（spec §6.2）                                    | Task 5–7 测试覆盖                                                       |
| CLI 退出码 0/1/2/3（spec §6.3，参见 CLAUDE.md）                       | Task 5–7 测试覆盖                                                       |
| API 端点（spec §11 M2 目标）                                          | Task 8                                                                  |
| 异常映射 NotFound→404 / State→409 / Validation→422（CLAUDE.md §5）    | Task 1（StateError 注册）+ Task 8 测试覆盖                              |
| ORM/DTO 隔离（service 返回 ORM，router 用 `response_model`）          | Task 5（DTO）+ Task 8（router）                                         |
| Service 层为唯一事实源，CLI 不走 HTTP（CLAUDE.md §1）                 | Task 5–7 直接 `from asset_hub.services.checkout import CheckoutService` |

**明确不在本计划范围内：**

- 附件上传 → M2b
- Web 前端消费上述 API → M2c
- 看板 / 导出 → M3
- 批量派发 / 批量归还 → v2+
- `Asset.current_checkout_id` 外键列 → 已放弃（见「关键决策」第 1 条）
