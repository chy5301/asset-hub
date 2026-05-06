# M3b PR-1 实施计划：后端 stats 端点 + list 三参数搭车 + idle_days helper

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** M3b PR-1 落地——`GET /api/stats` 4 段聚合 + `?fields=` 段选择 + `summary` 业务摘要；CLI `asset-hub stats` 配 `--fields` / `--include-retired/disposed`；`asset list` 搭车扩 `sort_by` / `sort_order` / `limit` / `offset`（agent-native C2 原子化）；`AssetRead` 补 `idle_days` 字段；C3 加回归测试锁定 `type_name` 现状。

**Architecture:** service 层是唯一事实——`StatsService.get_dashboard_stats()` 返 domain DTO；`AssetService.list_assets()` 加 4 参数；idle_days 子查询封装 `_idle_days_subquery()` helper 双方共享。CLI `from asset_hub.services import ...` 直接调，不走 HTTP（CLAUDE.md 三层分离）。

**Tech Stack:** Python / SQLModel / SQLAlchemy 2.x `select()` / FastAPI / Pydantic v2 / Typer / rich / pytest。

**Spec:** [`docs/superpowers/specs/2026-05-06-m3b-dashboard-stats-design.md`](../specs/2026-05-06-m3b-dashboard-stats-design.md)

**前置约束**：

- M3a 已合并 → `StateTransitionRecord` model 就位（字段：`asset_id` / `to_status` / `created_at` / `kind` 等；时间戳字段是 `created_at` 不是 `recorded_at`）
- main 上 `AssetRead.type_name` 已存在（M3a 已落 `Asset.type_name @property` + relationship lazy="joined"），C3 后端无须做（仅加回归测试）
- `AssetService.list_assets()` 当前不支持 sort/limit/offset，本 PR 扩展

**任务总览**（13 任务）：

1. `StatsRead` / `StatsField` Pydantic schemas + `StatsField` Literal
2. `_idle_days_subquery()` helper（service 层抽出）
3. `AssetRead.idle_days` 字段（搭车 §2.1）
4. `AssetService.list_assets()` 加 sort/order/limit/offset 参数（agent-native C2）
5. `GET /api/assets` router 透传 4 参数
6. `asset list` CLI 加 `--sort` / `--order` / `--limit` / `--offset`
7. C3 回归测试：`GET /api/assets/{id}` 含 `type_name`
8. `StatsService.get_dashboard_stats()` 4 段聚合（含 fields 子集 + summary）
9. `GET /api/stats` router（含 `_parse_fields()`）
10. `asset-hub stats` CLI（含 `--fields` + envelope）
11. `asset-hub stats` CLI 人类可读 rich 双列表格输出
12. CLI 命名例外注释 + main.py 注册 stats_app
13. PR-1 验收：全套 backend 测试 + ruff + alembic check

---

## Task 1: 定义 stats schemas

**Files:**
- Create: `src/asset_hub/api/schemas/stats.py`
- Test: `tests/unit/test_stats_schemas.py`

- [ ] **Step 1.1: 写失败测试**

```python
# tests/unit/test_stats_schemas.py
from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from asset_hub.api.schemas.stats import (
    HolderRankingItem,
    IdleTopItem,
    StatsField,
    StatsRead,
    StatsSummary,
    TypeDistributionItem,
)


def test_stats_field_literal_values():
    """StatsField 必须是 4 段名固定字面量."""
    valid: StatsField = "idle_top"
    assert valid == "idle_top"


def test_stats_summary_required_fields():
    s = StatsSummary(
        total_assets=187,
        registered_assets=182,
        idle_count=78,
        include_retired=False,
        include_disposed=False,
        generated_at=datetime(2026, 5, 6, 10, 30, 0),
    )
    assert s.total_assets == 187
    assert s.registered_assets == 182


def test_idle_top_item_required_fields():
    item = IdleTopItem(
        asset_id=uuid4(),
        asset_code="GPU-A100-03",
        type_name="GPU",
        current_location="仓库",
        idle_days=152,
        idle_since=datetime(2025, 12, 4),
    )
    assert item.idle_days == 152


def test_stats_read_all_sections_optional():
    """所有段都是 optional，summary 必填."""
    s = StatsRead(
        summary=StatsSummary(
            total_assets=0, registered_assets=0, idle_count=0,
            include_retired=False, include_disposed=False,
            generated_at=datetime.now(),
        )
    )
    assert s.idle_top is None
    assert s.type_distribution is None


def test_stats_read_full_payload():
    s = StatsRead(
        type_distribution=[TypeDistributionItem(type_id=uuid4(), type_name="Laptop", count=71)],
        status_distribution={"IDLE": 78, "IN_USE": 92},
        holder_ranking=[HolderRankingItem(holder="张三", count=28)],
        idle_top=[],
        summary=StatsSummary(
            total_assets=187, registered_assets=182, idle_count=78,
            include_retired=False, include_disposed=False,
            generated_at=datetime.now(),
        ),
    )
    assert len(s.type_distribution) == 1
    assert s.holder_ranking[0].holder == "张三"
```

- [ ] **Step 1.2: 运行测试，确认失败**

```bash
uv run pytest tests/unit/test_stats_schemas.py -v
```

预期：`ImportError: cannot import name 'StatsField' from 'asset_hub.api.schemas.stats'`

- [ ] **Step 1.3: 实现 schemas**

```python
# src/asset_hub/api/schemas/stats.py
"""M3b 看板 / stats 端点 DTO."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# 4 段名 — fields 参数 + service 函数签名都引用
StatsField = Literal[
    "type_distribution",
    "status_distribution",
    "holder_ranking",
    "idle_top",
]


class TypeDistributionItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    type_id: UUID
    type_name: str
    count: int


class HolderRankingItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    holder: str
    count: int


class IdleTopItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    asset_id: UUID
    asset_code: str
    type_name: str | None
    current_location: str | None
    idle_days: int
    idle_since: datetime


class StatsSummary(BaseModel):
    """业务摘要——命名 summary 而非 metadata，避免与 CLI envelope 顶层 metadata 冲突."""
    total_assets: int
    registered_assets: int
    idle_count: int
    include_retired: bool
    include_disposed: bool
    generated_at: datetime


class StatsRead(BaseModel):
    """4 段聚合响应 + summary。各段在响应里通过 fields 子集控制；summary 始终返回."""
    model_config = ConfigDict(from_attributes=True)

    type_distribution: list[TypeDistributionItem] | None = None
    status_distribution: dict[str, int] | None = None
    holder_ranking: list[HolderRankingItem] | None = None
    idle_top: list[IdleTopItem] | None = None
    summary: StatsSummary
```

- [ ] **Step 1.4: 运行测试，确认通过**

```bash
uv run pytest tests/unit/test_stats_schemas.py -v
```

预期：5 PASS。

- [ ] **Step 1.5: ruff + 提交**

```bash
uv run ruff check src/asset_hub/api/schemas/stats.py tests/unit/test_stats_schemas.py
git add src/asset_hub/api/schemas/stats.py tests/unit/test_stats_schemas.py
git commit -m "feat(stats): 加 StatsRead/StatsSummary/StatsField 等 DTO

4 段段名 Literal 类型；summary 命名避免与 CLI envelope metadata 冲突；各段 optional 支持 fields 子集查询。"
```

---

## Task 2: idle_days 子查询 helper

**Files:**
- Create: `src/asset_hub/services/_idle_days.py`
- Test: `tests/unit/test_idle_days_helper.py`

**理由**：spec §2.6 要求 `_idle_days_subquery()` helper 被 `list_assets`（搭车）和 `get_dashboard_stats` 双方共用。先抽 helper 让后续 task 复用。

- [ ] **Step 2.1: 写失败测试**

```python
# tests/unit/test_idle_days_helper.py
"""idle_days 子查询 helper：取 Asset 上次进入 IDLE 的时间，
fallback 为 created_at（资产从未发生过 transition）。"""
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlmodel import Session, select

from asset_hub.models.asset import Asset, AssetStatus
from asset_hub.models.asset_type import AssetType
from asset_hub.models.state_transition import StateTransitionRecord, TransitionKind
from asset_hub.services._idle_days import compute_idle_days_for_asset


@pytest.fixture
def session_with_idle_asset(session: Session):
    at = AssetType(name="Laptop", custom_fields=[])
    session.add(at)
    session.flush()
    a = Asset(
        asset_code="L-001", name="MBP", type_id=at.id,
        status=AssetStatus.IDLE,
    )
    session.add(a)
    session.flush()
    return session, a


def test_idle_days_no_transitions_falls_back_to_created_at(session_with_idle_asset):
    """资产从未发生 transition → fallback Asset.created_at."""
    session, asset = session_with_idle_asset
    asset.created_at = datetime.now(UTC) - timedelta(days=42)
    session.flush()

    days = compute_idle_days_for_asset(session, asset.id)
    assert days == 42


def test_idle_days_uses_latest_idle_transition(session_with_idle_asset):
    """有多次进出 IDLE 的 transition → 取最近一次 to_status=IDLE 的 created_at."""
    session, asset = session_with_idle_asset
    # 历史：早 30 天进 IDLE → 20 天前出 IDLE → 5 天前回 IDLE
    session.add(StateTransitionRecord(
        asset_id=asset.id,
        kind=TransitionKind.RETURN,
        from_status=AssetStatus.IN_USE, to_status=AssetStatus.IDLE,
        created_at=datetime.now(UTC) - timedelta(days=30),
    ))
    session.add(StateTransitionRecord(
        asset_id=asset.id,
        kind=TransitionKind.CHECKOUT_INTERNAL,
        from_status=AssetStatus.IDLE, to_status=AssetStatus.IN_USE,
        created_at=datetime.now(UTC) - timedelta(days=20),
    ))
    session.add(StateTransitionRecord(
        asset_id=asset.id,
        kind=TransitionKind.RETURN,
        from_status=AssetStatus.IN_USE, to_status=AssetStatus.IDLE,
        created_at=datetime.now(UTC) - timedelta(days=5),
    ))
    session.flush()

    days = compute_idle_days_for_asset(session, asset.id)
    assert days == 5
```

- [ ] **Step 2.2: 运行测试，确认失败**

```bash
uv run pytest tests/unit/test_idle_days_helper.py -v
```

预期：`ModuleNotFoundError: No module named 'asset_hub.services._idle_days'`

- [ ] **Step 2.3: 实现 helper**

```python
# src/asset_hub/services/_idle_days.py
"""idle_days 计算：从 StateTransitionRecord 取上次 to_status=IDLE 的 created_at；
新登记后未发生 transition 的 IDLE 资产 fallback Asset.created_at。

提供两种用法：
- compute_idle_days_for_asset(): 单 asset 标量查询（list/detail DTO 用）
- idle_since_subquery(): 可拼到 select(Asset).join(...).order_by() 的子查询表达式
  （stats 闲置 Top 10 / list_assets sort_by=idle_days 用）
"""
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlmodel import Session

from asset_hub.models.asset import Asset, AssetStatus
from asset_hub.models.state_transition import StateTransitionRecord


def _last_idle_subq():
    """子查询：每个 asset 上次进入 IDLE 的时间."""
    return (
        select(
            StateTransitionRecord.asset_id.label("asset_id"),
            func.max(StateTransitionRecord.created_at).label("last_idle_at"),
        )
        .where(StateTransitionRecord.to_status == AssetStatus.IDLE)
        .group_by(StateTransitionRecord.asset_id)
        .subquery()
    )


def idle_since_expr(asset_alias=Asset, last_idle_subq=None):
    """COALESCE(last_idle_at, asset.created_at) 表达式 — 用作排序/选择列."""
    sq = last_idle_subq if last_idle_subq is not None else _last_idle_subq()
    return func.coalesce(sq.c.last_idle_at, asset_alias.created_at)


def compute_idle_days_for_asset(session: Session, asset_id: uuid.UUID) -> int | None:
    """返回某资产的 idle_days；非 IDLE 状态返 None。"""
    asset = session.get(Asset, asset_id)
    if asset is None or asset.status != AssetStatus.IDLE:
        return None

    sq = _last_idle_subq()
    stmt = select(idle_since_expr(Asset, sq)).select_from(Asset).join(
        sq, sq.c.asset_id == Asset.id, isouter=True,
    ).where(Asset.id == asset_id)
    idle_since = session.exec(stmt).one()
    if idle_since is None:
        return None
    delta = datetime.now(UTC) - _ensure_aware(idle_since)
    return int(delta.total_seconds() // 86400)


def _ensure_aware(dt: datetime) -> datetime:
    """SQLite 取出来可能是 naive；统一为 UTC aware."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt
```

- [ ] **Step 2.4: 运行测试，确认通过**

```bash
uv run pytest tests/unit/test_idle_days_helper.py -v
```

预期：2 PASS。

- [ ] **Step 2.5: ruff + 提交**

```bash
uv run ruff check src/asset_hub/services/_idle_days.py tests/unit/test_idle_days_helper.py
git add src/asset_hub/services/_idle_days.py tests/unit/test_idle_days_helper.py
git commit -m "feat(services): idle_days 子查询 helper

抽 _idle_days.py 暴露 compute_idle_days_for_asset() 标量计算
+ idle_since_expr() 子查询表达式；list_assets 与 stats 服务双方共用。
COALESCE(last_idle_transition_at, asset.created_at) 实现 fallback。"
```

---

## Task 3: AssetRead 补 idle_days 字段

**Files:**
- Modify: `src/asset_hub/api/schemas/asset.py:36-52`
- Modify: `src/asset_hub/services/asset.py:97-113`
- Modify: `src/asset_hub/models/asset.py`（加 @property）
- Test: `tests/api/test_asset_router.py`（加 case）

- [ ] **Step 3.1: 写失败测试**

```python
# tests/api/test_asset_router.py 增量
def test_list_assets_response_contains_idle_days(client, idle_asset):
    """IDLE 资产的 list 响应必须含 idle_days."""
    res = client.get("/api/assets")
    assert res.status_code == 200
    body = res.json()
    assert any(a.get("idle_days") is not None for a in body if a["status"] == "IDLE")


def test_in_use_asset_idle_days_is_null(client, in_use_asset):
    """非 IDLE 资产 idle_days 必须为 null."""
    res = client.get(f"/api/assets/{in_use_asset.id}")
    assert res.status_code == 200
    assert res.json()["idle_days"] is None
```

- [ ] **Step 3.2: 运行测试，确认失败**

```bash
uv run pytest tests/api/test_asset_router.py -v -k idle_days
```

预期：FAIL（`idle_days` key 不在响应里）

- [ ] **Step 3.3: Asset model 加 @property**

```python
# src/asset_hub/models/asset.py 在 type_name @property 同级附近加：
    @property
    def idle_days(self) -> int | None:
        """非 IDLE 状态返 None；IDLE 状态返 N 天数。
        惰性计算——通过 session 的 _idle_days helper 单独查询。
        Pydantic 序列化时由 schema 层填充（避免 ORM 层访问 session）。
        """
        return None  # 占位；真实值由 service 层填充
```

- [ ] **Step 3.4: AssetRead schema 加字段**

```python
# src/asset_hub/api/schemas/asset.py:36-52 修改后：
class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    asset_code: str
    name: str
    serial_number: str | None
    type_id: UUID
    type_name: str | None
    status: AssetStatus
    holder: str | None
    location: str | None
    notes: str | None
    custom_data: dict
    acquired_at: date | None
    idle_days: int | None = None  # 新；非 IDLE 状态为 None
    created_at: datetime
    updated_at: datetime
```

- [ ] **Step 3.5: AssetService.list_assets 与 get_asset 填充 idle_days**

```python
# src/asset_hub/services/asset.py 改 list_assets/get_asset 返回——把 idle_days 计算注入返回值
# 由于 AssetRead 用 from_attributes，需要让 ORM 对象有 idle_days 属性
# 简单做法：service 层不动 ORM，由 router 层在序列化前注入

# 在 src/asset_hub/services/asset.py 加方法：
    def annotate_idle_days(self, assets: list[Asset]) -> list[Asset]:
        """给 IDLE 资产填充 idle_days；in-place 设属性，让 AssetRead 序列化能读到。"""
        from asset_hub.services._idle_days import compute_idle_days_for_asset

        for a in assets:
            if a.status == AssetStatus.IDLE:
                # @property 是只读的，用 setattr 注入实例属性覆盖
                setattr(a, "_idle_days_value", compute_idle_days_for_asset(self.session, a.id))
            else:
                setattr(a, "_idle_days_value", None)
        return assets
```

把 Asset.idle_days 改为 property 读取 instance attr：

```python
# src/asset_hub/models/asset.py
    @property
    def idle_days(self) -> int | None:
        return getattr(self, "_idle_days_value", None)
```

- [ ] **Step 3.6: router 层调用 annotate**

```python
# src/asset_hub/api/routers/assets.py:36-53
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
    assets = svc.list_assets(
        type_id=type_id, status=status, holder=holder, q=q,
        include_retired=include_retired, include_disposed=include_disposed,
    )
    return svc.annotate_idle_days(assets)


@router.get("/{asset_id}", response_model=AssetRead)
def get_asset(
    asset_id: uuid.UUID,
    svc: Annotated[AssetService, Depends(_get_svc)],
):
    asset = svc.get_asset(asset_id)
    return svc.annotate_idle_days([asset])[0]
```

- [ ] **Step 3.7: 运行测试，确认通过**

```bash
uv run pytest tests/api/test_asset_router.py -v -k idle_days
```

预期：2 PASS。

- [ ] **Step 3.8: 提交**

```bash
git add src/asset_hub/api/schemas/asset.py src/asset_hub/services/asset.py src/asset_hub/models/asset.py src/asset_hub/api/routers/assets.py tests/api/test_asset_router.py
git commit -m "feat(asset): AssetRead 补 idle_days 字段

非 IDLE 资产 idle_days=null；IDLE 资产由 service.annotate_idle_days() 计算填充
（复用 services/_idle_days.compute_idle_days_for_asset()，单一来源）。
搭车 M3b §2.1：list 闲置时长列与看板同源。"
```

---

## Task 4: AssetService.list_assets 加 sort/order/limit/offset

**Files:**
- Modify: `src/asset_hub/services/asset.py:97-113`
- Modify: `src/asset_hub/repositories/asset.py`
- Test: `tests/unit/test_asset_service.py`（增量）

- [ ] **Step 4.1: 写失败测试**

```python
# tests/unit/test_asset_service.py 增量
import pytest
from datetime import UTC, datetime, timedelta
from sqlmodel import Session

from asset_hub.errors import ValidationError
from asset_hub.services.asset import AssetService
from asset_hub.models.asset import Asset, AssetStatus
from asset_hub.models.asset_type import AssetType


def _create_idle_assets(session: Session, count: int) -> list[Asset]:
    at = AssetType(name="Laptop", custom_fields=[])
    session.add(at); session.flush()
    assets = []
    for i in range(count):
        a = Asset(asset_code=f"L-{i:03d}", name=f"L{i}", type_id=at.id, status=AssetStatus.IDLE)
        session.add(a); session.flush()
        # 让 created_at 错开
        a.created_at = datetime.now(UTC) - timedelta(days=count - i)
        assets.append(a)
    session.flush()
    return assets


def test_list_assets_sort_by_idle_days_desc(session: Session):
    """sort_by=idle_days, sort_order=desc → 最闲置的（早 created_at）排首位."""
    _create_idle_assets(session, 5)
    svc = AssetService(session)
    result = svc.list_assets(sort_by="idle_days", sort_order="desc")
    assert result[0].asset_code == "L-000"  # 最早创建 = 最闲置


def test_list_assets_limit_truncates(session: Session):
    _create_idle_assets(session, 10)
    svc = AssetService(session)
    result = svc.list_assets(limit=3)
    assert len(result) == 3


def test_list_assets_offset_skips(session: Session):
    _create_idle_assets(session, 5)
    svc = AssetService(session)
    full = svc.list_assets(sort_by="created_at", sort_order="asc")
    paged = svc.list_assets(sort_by="created_at", sort_order="asc", offset=2, limit=2)
    assert [a.id for a in paged] == [full[2].id, full[3].id]


def test_list_assets_unknown_sort_by_raises(session: Session):
    svc = AssetService(session)
    with pytest.raises(ValidationError, match="sort_by"):
        svc.list_assets(sort_by="invalid_field")


def test_list_assets_invalid_sort_order_raises(session: Session):
    svc = AssetService(session)
    with pytest.raises(ValidationError, match="sort_order"):
        svc.list_assets(sort_order="up")


def test_list_assets_negative_offset_raises(session: Session):
    svc = AssetService(session)
    with pytest.raises(ValidationError, match="offset"):
        svc.list_assets(offset=-1)


def test_list_assets_limit_over_max_raises(session: Session):
    svc = AssetService(session)
    with pytest.raises(ValidationError, match="limit"):
        svc.list_assets(limit=2000)


def test_list_assets_default_no_sort_no_limit(session: Session):
    """不传 sort/limit/offset → 行为与 main 当前一致（兼容）."""
    _create_idle_assets(session, 3)
    svc = AssetService(session)
    result = svc.list_assets()  # 全默认
    assert len(result) == 3
```

- [ ] **Step 4.2: 运行测试，确认失败**

```bash
uv run pytest tests/unit/test_asset_service.py -v -k "sort or limit or offset"
```

预期：8 FAIL（list_assets 不接这些参数）

- [ ] **Step 4.3: 扩 AssetService.list_assets**

```python
# src/asset_hub/services/asset.py:97-113
from typing import Literal

SortOrder = Literal["asc", "desc"]
SORT_FIELD_WHITELIST = frozenset({
    "name", "asset_code", "created_at", "updated_at", "acquired_at", "idle_days",
})
LIMIT_MAX = 1000


def list_assets(
    self,
    type_id: uuid.UUID | None = None,
    status: AssetStatus | None = None,
    holder: str | None = None,
    q: str | None = None,
    include_retired: bool = False,
    include_disposed: bool = False,
    sort_by: str | None = None,
    sort_order: SortOrder = "desc",
    limit: int | None = None,
    offset: int | None = None,
) -> list[Asset]:
    if sort_by is not None and sort_by not in SORT_FIELD_WHITELIST:
        raise ValidationError(
            f"sort_by 不支持：{sort_by!r}，可选：{sorted(SORT_FIELD_WHITELIST)}"
        )
    if sort_order not in ("asc", "desc"):
        raise ValidationError(f"sort_order 必须是 'asc' 或 'desc'，收到：{sort_order!r}")
    if offset is not None and offset < 0:
        raise ValidationError(f"offset 不能为负，收到：{offset}")
    if limit is not None and (limit < 1 or limit > LIMIT_MAX):
        raise ValidationError(f"limit 必须在 1..{LIMIT_MAX}，收到：{limit}")

    return self.repo.list_filtered(
        type_id=type_id, status=status, holder=holder, q=q,
        include_retired=include_retired, include_disposed=include_disposed,
        sort_by=sort_by, sort_order=sort_order, limit=limit, offset=offset,
    )
```

- [ ] **Step 4.4: 扩 repository.list_filtered**

```python
# src/asset_hub/repositories/asset.py
# 找到 list_filtered 方法，加参数 + 排序逻辑：
from sqlalchemy import asc, desc
from asset_hub.services._idle_days import _last_idle_subq, idle_since_expr


def list_filtered(
    self,
    type_id: uuid.UUID | None = None,
    status: AssetStatus | None = None,
    holder: str | None = None,
    q: str | None = None,
    include_retired: bool = False,
    include_disposed: bool = False,
    sort_by: str | None = None,
    sort_order: str = "desc",
    limit: int | None = None,
    offset: int | None = None,
) -> list[Asset]:
    stmt = select(Asset)

    # 现有 filter 逻辑保留……
    if type_id is not None:
        stmt = stmt.where(Asset.type_id == type_id)
    if status is not None:
        stmt = stmt.where(Asset.status == status)
    if holder is not None:
        stmt = stmt.where(Asset.holder.ilike(f"%{holder}%"))
    if q is not None:
        stmt = stmt.where(Asset.name.ilike(f"%{q}%") | Asset.asset_code.ilike(f"%{q}%"))
    if not include_retired:
        stmt = stmt.where(Asset.status != AssetStatus.RETIRED)
    if not include_disposed:
        stmt = stmt.where(Asset.status != AssetStatus.DISPOSED)

    # 新：排序
    direction = desc if sort_order == "desc" else asc
    if sort_by == "idle_days":
        sq = _last_idle_subq()
        stmt = stmt.outerjoin(sq, sq.c.asset_id == Asset.id).order_by(
            direction(idle_since_expr(Asset, sq)).nullslast() if sort_order == "desc"
            else direction(idle_since_expr(Asset, sq)).nullsfirst()
        )
    elif sort_by is not None:
        col = getattr(Asset, sort_by)
        stmt = stmt.order_by(direction(col))
    else:
        # 默认行为：created_at desc（与 main 行为兼容）
        stmt = stmt.order_by(desc(Asset.created_at))

    # 新：limit/offset
    if offset is not None:
        stmt = stmt.offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)

    return list(self.session.exec(stmt).all())
```

> 注意 `idle_days` 排序：sort_order=desc 表示"最久闲置在前"——即 idle_since 越早越靠前。所以 desc 实际是 idle_since 的 asc。但 spec / 用户视角是 "idle_days desc = 最久闲置在前"，所以代码按 spec 用户视角实现：`sort_by=idle_days desc → idle_since asc`。下面修一下：

```python
    if sort_by == "idle_days":
        sq = _last_idle_subq()
        # idle_days desc ≡ idle_since asc（越早 idle 越久）
        # idle_days asc ≡ idle_since desc
        idle_since = idle_since_expr(Asset, sq)
        sort_dir = asc if sort_order == "desc" else desc
        stmt = stmt.outerjoin(sq, sq.c.asset_id == Asset.id).order_by(sort_dir(idle_since))
```

- [ ] **Step 4.5: 运行测试，确认通过**

```bash
uv run pytest tests/unit/test_asset_service.py -v -k "sort or limit or offset"
```

预期：8 PASS。

- [ ] **Step 4.6: 跑全套 service 测试确保兼容**

```bash
uv run pytest tests/unit/test_asset_service.py -v
```

预期：全 PASS（含老测试，确认默认参数行为兼容）

- [ ] **Step 4.7: 提交**

```bash
git add src/asset_hub/services/asset.py src/asset_hub/repositories/asset.py tests/unit/test_asset_service.py
git commit -m "feat(asset): list_assets 加 sort_by/sort_order/limit/offset 参数

agent-native C2 原子化（spec §2.6）：让 Agent 能 'asset list --status IDLE
--sort idle_days --limit 10' 等价 stats idle_top 段，不再让 stats 端点垄断
'闲置 Top N' 原子能力。

sort_by 白名单 6 项；limit 1..1000；offset >= 0；越界 raise ValidationError → 422。
idle_days 排序复用 services/_idle_days helper。"
```

---

## Task 5: GET /api/assets router 透传 4 参数

**Files:**
- Modify: `src/asset_hub/api/routers/assets.py:36-53`
- Test: `tests/api/test_asset_router.py`（增量）

- [ ] **Step 5.1: 写失败测试**

```python
# tests/api/test_asset_router.py 增量
def test_list_assets_with_sort_idle_days(client, idle_assets_5):
    res = client.get("/api/assets?status=IDLE&sort_by=idle_days&sort_order=desc&limit=3")
    assert res.status_code == 200
    body = res.json()
    assert len(body) == 3


def test_list_assets_unknown_sort_by_returns_422(client):
    res = client.get("/api/assets?sort_by=foo")
    assert res.status_code == 422


def test_list_assets_limit_over_max_returns_422(client):
    res = client.get("/api/assets?limit=2000")
    assert res.status_code == 422


def test_list_assets_negative_offset_returns_422(client):
    res = client.get("/api/assets?offset=-1")
    assert res.status_code == 422
```

- [ ] **Step 5.2: 运行测试，确认失败**

```bash
uv run pytest tests/api/test_asset_router.py -v -k "sort_idle_days or sort_by or limit_over or negative_offset"
```

预期：4 FAIL（router 不接这些参数）

- [ ] **Step 5.3: 扩 router**

```python
# src/asset_hub/api/routers/assets.py:36-53
from typing import Literal


@router.get("", response_model=list[AssetRead])
def list_assets(
    svc: Annotated[AssetService, Depends(_get_svc)],
    type_id: uuid.UUID | None = None,
    status: AssetStatus | None = None,
    holder: str | None = None,
    q: str | None = None,
    include_retired: bool = False,
    include_disposed: bool = False,
    sort_by: str | None = None,
    sort_order: Literal["asc", "desc"] = "desc",
    limit: int | None = None,
    offset: int | None = None,
):
    assets = svc.list_assets(
        type_id=type_id, status=status, holder=holder, q=q,
        include_retired=include_retired, include_disposed=include_disposed,
        sort_by=sort_by, sort_order=sort_order, limit=limit, offset=offset,
    )
    return svc.annotate_idle_days(assets)
```

> ValidationError 由 service 层 raise → app.py 现有映射转 422。无须 router 改异常处理。

- [ ] **Step 5.4: 运行测试，确认通过**

```bash
uv run pytest tests/api/test_asset_router.py -v -k "sort_idle_days or sort_by or limit_over or negative_offset"
```

预期：4 PASS。

- [ ] **Step 5.5: 提交**

```bash
git add src/asset_hub/api/routers/assets.py tests/api/test_asset_router.py
git commit -m "feat(api): GET /api/assets 透传 sort_by/sort_order/limit/offset

ValidationError 由 service 层抛 → app.py 既有映射转 422。"
```

---

## Task 6: asset list CLI 加 --sort/--order/--limit/--offset

**Files:**
- Modify: `src/asset_hub/cli/asset_cmd.py`（找 `asset_app.command("list")`）
- Test: `tests/cli/test_asset_cli.py`（增量）

- [ ] **Step 6.1: 找现有 list 命令**

```bash
grep -n 'command\("list"\)' src/asset_hub/cli/asset_cmd.py
```

记录行号 N，下面引用。

- [ ] **Step 6.2: 写失败测试**

```python
# tests/cli/test_asset_cli.py 增量
import json
from typer.testing import CliRunner

from asset_hub.cli.main import app

runner = CliRunner()


def test_asset_list_with_sort_idle_days(isolated_db_with_idle_assets):
    """--sort idle_days --order desc --limit 5 等价 stats idle_top（spec §2.6）."""
    result = runner.invoke(app, [
        "asset", "list",
        "--status", "IDLE",
        "--sort", "idle_days",
        "--order", "desc",
        "--limit", "5",
        "--json",
    ])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["success"] is True
    assert len(payload["data"]) == 5


def test_asset_list_unknown_sort_field_exits_2(isolated_db):
    result = runner.invoke(app, ["asset", "list", "--sort", "bogus", "--json"])
    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["success"] is False
    assert "sort_by" in payload["error"]


def test_asset_list_limit_over_max_exits_2(isolated_db):
    result = runner.invoke(app, ["asset", "list", "--limit", "2000", "--json"])
    assert result.exit_code == 2
```

- [ ] **Step 6.3: 运行测试，确认失败**

```bash
uv run pytest tests/cli/test_asset_cli.py -v -k "sort_idle_days or unknown_sort or limit_over"
```

预期：3 FAIL。

- [ ] **Step 6.4: 扩 CLI list 命令**

定位 `asset_cmd.py` 中的 `asset_list` 函数，加参数：

```python
# src/asset_hub/cli/asset_cmd.py 中 asset_list 函数
@asset_app.command("list")
def asset_list(
    type_id: Annotated[str | None, typer.Option("--type-id")] = None,
    status: Annotated[str | None, typer.Option()] = None,
    holder: Annotated[str | None, typer.Option()] = None,
    q: Annotated[str | None, typer.Option("--q", help="搜索 name/asset_code")] = None,
    include_retired: Annotated[bool, typer.Option("--include-retired/--no-include-retired")] = False,
    include_disposed: Annotated[bool, typer.Option("--include-disposed/--no-include-disposed")] = False,
    sort: Annotated[str | None, typer.Option("--sort", help="排序字段：name/asset_code/created_at/updated_at/acquired_at/idle_days")] = None,
    order: Annotated[str, typer.Option("--order", help="asc/desc，默认 desc")] = "desc",
    limit: Annotated[int | None, typer.Option("--limit", help="返回上限，1-1000")] = None,
    offset: Annotated[int | None, typer.Option("--offset", help=">=0")] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """列出资产。"""
    type_uid = parse_uuid(type_id, json_output) if type_id else None
    status_enum = parse_enum(AssetStatus, status, json_output) if status else None

    with cli_session() as session, handle_domain_errors(json_output, exit_2_on_validation=True):
        svc = AssetService(session)
        assets = svc.list_assets(
            type_id=type_uid, status=status_enum, holder=holder, q=q,
            include_retired=include_retired, include_disposed=include_disposed,
            sort_by=sort, sort_order=order, limit=limit, offset=offset,
        )
        annotated = svc.annotate_idle_days(assets)
    print_result([to_json_dict(AssetRead, a) for a in annotated], json_output, count=len(annotated))
```

> 注意：`handle_domain_errors` 需支持 `exit_2_on_validation=True` 让 `ValidationError` 退出码 2 而非 1。检查现有 envelope.py：

```bash
grep -n "ValidationError\|exit_code" src/asset_hub/cli/envelope.py
```

如不支持，本 task 顺手扩 envelope.py 加 `exit_2_on_validation` 参数：

```python
# src/asset_hub/cli/envelope.py 中 handle_domain_errors
@contextmanager
def handle_domain_errors(json_output: bool, exit_2_on_validation: bool = False):
    try:
        yield
    except ValidationError as e:
        exit_code = 2 if exit_2_on_validation else 1
        print_error(str(e), json_output, exit_code=exit_code)
    except (NotFoundError, DuplicateError, IllegalTransitionError, StateError, ConflictError) as e:
        print_error(str(e), json_output, exit_code=1)
```

- [ ] **Step 6.5: 运行测试，确认通过**

```bash
uv run pytest tests/cli/test_asset_cli.py -v -k "sort_idle_days or unknown_sort or limit_over"
uv run pytest tests/cli/test_asset_cli.py -v  # 老测试也得过
```

预期：全 PASS。

- [ ] **Step 6.6: 提交**

```bash
git add src/asset_hub/cli/asset_cmd.py src/asset_hub/cli/envelope.py tests/cli/test_asset_cli.py
git commit -m "feat(cli): asset list 加 --sort/--order/--limit/--offset

agent-native C2 原子化（spec §2.6）。envelope handle_domain_errors 增
exit_2_on_validation 参数，让 ValidationError 退出码 2（用法错误），
其他域异常仍退出 1。"
```

---

## Task 7: C3 回归测试 — GET /api/assets/{id} 含 type_name

**Files:**
- Test: `tests/api/test_asset_router.py`（增量）

**理由**：spec §5 follow-up 表已明：M3a 已落 `Asset.type_name @property` + `AssetRead.type_name`，C3 后端无须做。本 task 仅加回归测试锁定行为，避免未来重构误删。

- [ ] **Step 7.1: 写测试**

```python
# tests/api/test_asset_router.py 增量
def test_get_asset_response_contains_type_name(client, asset_with_type):
    """C3 回归（spec §5）：detail 响应必须含 type_name 字段（非 null）.
    M3a 已通过 Asset.type_name @property 实现，此测试锁定行为。"""
    res = client.get(f"/api/assets/{asset_with_type.id}")
    assert res.status_code == 200
    body = res.json()
    assert "type_name" in body
    assert body["type_name"] is not None
    assert body["type_name"] == asset_with_type.asset_type.name
```

- [ ] **Step 7.2: 运行测试**

```bash
uv run pytest tests/api/test_asset_router.py::test_get_asset_response_contains_type_name -v
```

预期：PASS（M3a 已实现）。如果 FAIL → spec 与代码不符，需先调研。

- [ ] **Step 7.3: 提交**

```bash
git add tests/api/test_asset_router.py
git commit -m "test(api): C3 回归——锁定 GET /api/assets/{id} 含 type_name

M3a 已通过 Asset.type_name @property + AssetRead.type_name 实现。
此测试避免未来重构误删 @property 或 AssetRead 字段。"
```

---

## Task 8: StatsService.get_dashboard_stats 4 段聚合

**Files:**
- Create: `src/asset_hub/services/stats.py`
- Test: `tests/unit/test_stats_service.py`

- [ ] **Step 8.1: 写失败测试**

```python
# tests/unit/test_stats_service.py
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlmodel import Session

from asset_hub.api.schemas.stats import StatsRead
from asset_hub.errors import ValidationError
from asset_hub.models.asset import Asset, AssetStatus
from asset_hub.models.asset_type import AssetType
from asset_hub.models.state_transition import StateTransitionRecord, TransitionKind
from asset_hub.services.stats import StatsService


@pytest.fixture
def populated_session(session: Session):
    """5 资产：3 IDLE / 1 IN_USE / 1 RETIRED；2 type；2 holder."""
    laptop = AssetType(name="Laptop", custom_fields=[])
    gpu = AssetType(name="GPU", custom_fields=[])
    session.add(laptop); session.add(gpu); session.flush()

    a1 = Asset(asset_code="L-001", name="L1", type_id=laptop.id, status=AssetStatus.IDLE, holder=None)
    a2 = Asset(asset_code="L-002", name="L2", type_id=laptop.id, status=AssetStatus.IDLE, holder="张三")
    a3 = Asset(asset_code="G-001", name="G1", type_id=gpu.id, status=AssetStatus.IDLE)
    a4 = Asset(asset_code="L-003", name="L3", type_id=laptop.id, status=AssetStatus.IN_USE, holder="李四")
    a5 = Asset(asset_code="G-002", name="G2", type_id=gpu.id, status=AssetStatus.RETIRED, holder="王五")
    for a in [a1, a2, a3, a4, a5]:
        session.add(a)
    session.flush()

    # a1 30 天前进 IDLE，a2 5 天前进 IDLE，a3 created_at = 50 天前（fallback）
    session.add(StateTransitionRecord(
        asset_id=a1.id, kind=TransitionKind.RETURN,
        from_status=AssetStatus.IN_USE, to_status=AssetStatus.IDLE,
        created_at=datetime.now(UTC) - timedelta(days=30),
    ))
    session.add(StateTransitionRecord(
        asset_id=a2.id, kind=TransitionKind.RETURN,
        from_status=AssetStatus.IN_USE, to_status=AssetStatus.IDLE,
        created_at=datetime.now(UTC) - timedelta(days=5),
    ))
    a3.created_at = datetime.now(UTC) - timedelta(days=50)
    session.flush()

    return session


def test_get_dashboard_stats_default_excludes_retired_disposed(populated_session):
    svc = StatsService(populated_session)
    stats = svc.get_dashboard_stats()
    # status_distribution 不应含 RETIRED
    assert "RETIRED" not in stats.status_distribution
    assert stats.status_distribution.get("IDLE") == 3
    assert stats.status_distribution.get("IN_USE") == 1
    # summary 反映 toggle
    assert stats.summary.include_retired is False
    assert stats.summary.total_assets == 5  # 全部
    assert stats.summary.registered_assets == 4  # 不含 RETIRED


def test_get_dashboard_stats_include_retired(populated_session):
    svc = StatsService(populated_session)
    stats = svc.get_dashboard_stats(include_retired=True)
    assert stats.status_distribution.get("RETIRED") == 1
    assert stats.summary.registered_assets == 5  # 全部含 RETIRED


def test_get_dashboard_stats_idle_top_ordering(populated_session):
    svc = StatsService(populated_session)
    stats = svc.get_dashboard_stats()
    # 闲置 Top：a3 (50d, fallback created_at) > a1 (30d) > a2 (5d)
    assert len(stats.idle_top) == 3
    assert stats.idle_top[0].asset_code == "G-001"  # 50d
    assert stats.idle_top[0].idle_days >= 49  # 略放宽时间精度
    assert stats.idle_top[1].asset_code == "L-001"  # 30d
    assert stats.idle_top[2].asset_code == "L-002"  # 5d


def test_get_dashboard_stats_holder_ranking_skips_null(populated_session):
    svc = StatsService(populated_session)
    stats = svc.get_dashboard_stats()
    holders = [h.holder for h in stats.holder_ranking]
    assert None not in holders
    assert "张三" in holders
    assert "李四" in holders


def test_get_dashboard_stats_fields_idle_top_only(populated_session):
    svc = StatsService(populated_session)
    stats = svc.get_dashboard_stats(fields={"idle_top"})
    assert stats.idle_top is not None
    assert stats.type_distribution is None
    assert stats.status_distribution is None
    assert stats.holder_ranking is None
    # summary 始终返回
    assert stats.summary is not None


def test_get_dashboard_stats_fields_multiple(populated_session):
    svc = StatsService(populated_session)
    stats = svc.get_dashboard_stats(fields={"idle_top", "status_distribution"})
    assert stats.idle_top is not None
    assert stats.status_distribution is not None
    assert stats.type_distribution is None


def test_get_dashboard_stats_fields_unknown_raises(populated_session):
    svc = StatsService(populated_session)
    with pytest.raises(ValidationError, match="fields"):
        svc.get_dashboard_stats(fields={"foo"})  # type: ignore


def test_get_dashboard_stats_idle_top_max_10(session: Session):
    """IDLE 资产 > 10 件时严格截断 10 件."""
    at = AssetType(name="Bulk", custom_fields=[])
    session.add(at); session.flush()
    for i in range(15):
        a = Asset(asset_code=f"B-{i:03d}", name=f"B{i}", type_id=at.id, status=AssetStatus.IDLE)
        a.created_at = datetime.now(UTC) - timedelta(days=15 - i)
        session.add(a)
    session.flush()
    stats = StatsService(session).get_dashboard_stats()
    assert len(stats.idle_top) == 10


def test_get_dashboard_stats_idle_top_under_10_no_padding(session: Session):
    """IDLE 资产 < 10 时不补位."""
    at = AssetType(name="Few", custom_fields=[])
    session.add(at); session.flush()
    for i in range(3):
        session.add(Asset(asset_code=f"F-{i:03d}", name=f"F{i}", type_id=at.id, status=AssetStatus.IDLE))
    session.flush()
    stats = StatsService(session).get_dashboard_stats()
    assert len(stats.idle_top) == 3


def test_get_dashboard_stats_summary_always_returned(populated_session):
    """summary 不受 fields 控制."""
    svc = StatsService(populated_session)
    stats = svc.get_dashboard_stats(fields=set())  # 空 fields
    assert stats.summary is not None
    assert stats.idle_top is None
```

- [ ] **Step 8.2: 运行测试，确认失败**

```bash
uv run pytest tests/unit/test_stats_service.py -v
```

预期：全 FAIL（`StatsService` 不存在）。

- [ ] **Step 8.3: 实现 StatsService**

```python
# src/asset_hub/services/stats.py
"""M3b 看板 stats service。

4 段聚合 + summary 业务摘要；fields 子集查询省 token。
idle_top 复用 services/_idle_days helper（与 list_assets 同源）。
"""
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import case, func, select
from sqlmodel import Session

from asset_hub.api.schemas.stats import (
    HolderRankingItem,
    IdleTopItem,
    StatsField,
    StatsRead,
    StatsSummary,
    TypeDistributionItem,
)
from asset_hub.errors import ValidationError
from asset_hub.models.asset import Asset, AssetStatus
from asset_hub.models.asset_type import AssetType
from asset_hub.services._idle_days import _last_idle_subq, idle_since_expr

ALL_FIELDS: frozenset[StatsField] = frozenset({
    "type_distribution", "status_distribution", "holder_ranking", "idle_top",
})


def _ensure_aware(dt: datetime) -> datetime:
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt


class StatsService:
    def __init__(self, session: Session):
        self.session = session

    def get_dashboard_stats(
        self,
        *,
        include_retired: bool = False,
        include_disposed: bool = False,
        fields: set[StatsField] | None = None,
    ) -> StatsRead:
        if fields is not None:
            unknown = fields - ALL_FIELDS
            if unknown:
                raise ValidationError(
                    f"fields 含未知段：{sorted(unknown)}；可选：{sorted(ALL_FIELDS)}"
                )
        wanted = fields if fields is not None else ALL_FIELDS

        type_dist = self._type_distribution(include_retired, include_disposed) if "type_distribution" in wanted else None
        status_dist = self._status_distribution(include_retired, include_disposed) if "status_distribution" in wanted else None
        holders = self._holder_ranking(include_retired, include_disposed) if "holder_ranking" in wanted else None
        idle = self._idle_top(limit=10) if "idle_top" in wanted else None
        summary = self._summary(include_retired, include_disposed)

        return StatsRead(
            type_distribution=type_dist,
            status_distribution=status_dist,
            holder_ranking=holders,
            idle_top=idle,
            summary=summary,
        )

    def _base_filter(self, stmt, include_retired: bool, include_disposed: bool):
        if not include_retired:
            stmt = stmt.where(Asset.status != AssetStatus.RETIRED)
        if not include_disposed:
            stmt = stmt.where(Asset.status != AssetStatus.DISPOSED)
        return stmt

    def _type_distribution(self, ir: bool, idp: bool) -> list[TypeDistributionItem]:
        stmt = (
            select(Asset.type_id, AssetType.name, func.count(Asset.id))
            .join(AssetType, AssetType.id == Asset.type_id)
            .group_by(Asset.type_id, AssetType.name)
            .order_by(func.count(Asset.id).desc())
        )
        stmt = self._base_filter(stmt, ir, idp)
        return [
            TypeDistributionItem(type_id=tid, type_name=name, count=cnt)
            for tid, name, cnt in self.session.exec(stmt).all()
        ]

    def _status_distribution(self, ir: bool, idp: bool) -> dict[str, int]:
        stmt = select(Asset.status, func.count()).group_by(Asset.status)
        stmt = self._base_filter(stmt, ir, idp)
        result = {status.value: count for status, count in self.session.exec(stmt).all()}
        return result

    def _holder_ranking(self, ir: bool, idp: bool) -> list[HolderRankingItem]:
        stmt = (
            select(Asset.holder, func.count())
            .where(Asset.holder.is_not(None))
            .group_by(Asset.holder)
            .order_by(func.count().desc())
        )
        stmt = self._base_filter(stmt, ir, idp)
        return [
            HolderRankingItem(holder=h, count=cnt)
            for h, cnt in self.session.exec(stmt).all() if h is not None
        ]

    def _idle_top(self, limit: int) -> list[IdleTopItem]:
        sq = _last_idle_subq()
        idle_since = idle_since_expr(Asset, sq)
        stmt = (
            select(
                Asset.id, Asset.asset_code, AssetType.name, Asset.location, idle_since,
            )
            .join(AssetType, AssetType.id == Asset.type_id)
            .outerjoin(sq, sq.c.asset_id == Asset.id)
            .where(Asset.status == AssetStatus.IDLE)
            .order_by(idle_since.asc())
            .limit(limit)
        )
        now = datetime.now(UTC)
        items = []
        for aid, code, type_name, location, since in self.session.exec(stmt).all():
            since_aware = _ensure_aware(since)
            days = int((now - since_aware).total_seconds() // 86400)
            items.append(IdleTopItem(
                asset_id=aid, asset_code=code, type_name=type_name,
                current_location=location, idle_days=days, idle_since=since_aware,
            ))
        return items

    def _summary(self, ir: bool, idp: bool) -> StatsSummary:
        total = self.session.exec(select(func.count(Asset.id))).one()
        registered_stmt = select(func.count(Asset.id)).where(
            Asset.status != AssetStatus.RETIRED,
            Asset.status != AssetStatus.DISPOSED,
        )
        registered = self.session.exec(registered_stmt).one()
        idle_stmt = select(func.count(Asset.id)).where(Asset.status == AssetStatus.IDLE)
        idle_count = self.session.exec(idle_stmt).one()
        return StatsSummary(
            total_assets=total,
            registered_assets=registered,
            idle_count=idle_count,
            include_retired=ir,
            include_disposed=idp,
            generated_at=datetime.now(UTC),
        )
```

- [ ] **Step 8.4: 运行测试，确认通过**

```bash
uv run pytest tests/unit/test_stats_service.py -v
```

预期：10 PASS。如有时间精度问题（`>= 49` 的 fixture），微调 fixture timestamp 即可。

- [ ] **Step 8.5: ruff + 提交**

```bash
uv run ruff check src/asset_hub/services/stats.py tests/unit/test_stats_service.py
git add src/asset_hub/services/stats.py tests/unit/test_stats_service.py
git commit -m "feat(stats): StatsService.get_dashboard_stats 4 段聚合 + summary

fields 子集查询（agent-native P3 输出即产品）；summary 始终返回；
idle_top 复用 services/_idle_days helper 与 list_assets 同源；
holder_ranking 全量倒序 + skip null。"
```

---

## Task 9: GET /api/stats router

**Files:**
- Create: `src/asset_hub/api/routers/stats.py`
- Modify: `src/asset_hub/api/app.py`（注册 router）
- Test: `tests/api/test_stats_router.py`

- [ ] **Step 9.1: 写失败测试**

```python
# tests/api/test_stats_router.py
import pytest
from fastapi.testclient import TestClient


def test_get_stats_default_returns_all_4_sections(client, populated_db):
    res = client.get("/api/stats")
    assert res.status_code == 200
    body = res.json()
    assert "type_distribution" in body
    assert "status_distribution" in body
    assert "holder_ranking" in body
    assert "idle_top" in body
    assert "summary" in body


def test_get_stats_summary_fields_complete(client, populated_db):
    res = client.get("/api/stats")
    summary = res.json()["summary"]
    assert "total_assets" in summary
    assert "registered_assets" in summary
    assert "idle_count" in summary
    assert summary["include_retired"] is False
    assert summary["include_disposed"] is False
    assert "generated_at" in summary


def test_get_stats_fields_idle_top_only(client, populated_db):
    res = client.get("/api/stats?fields=idle_top")
    assert res.status_code == 200
    body = res.json()
    assert body["idle_top"] is not None
    assert body.get("type_distribution") is None
    assert body.get("status_distribution") is None
    assert body.get("holder_ranking") is None
    assert body["summary"] is not None  # 始终返回


def test_get_stats_fields_multiple(client, populated_db):
    res = client.get("/api/stats?fields=idle_top,status_distribution")
    body = res.json()
    assert body["idle_top"] is not None
    assert body["status_distribution"] is not None
    assert body.get("type_distribution") is None


def test_get_stats_fields_unknown_returns_422(client):
    res = client.get("/api/stats?fields=foo")
    assert res.status_code == 422


def test_get_stats_fields_includes_unknown_returns_422(client):
    res = client.get("/api/stats?fields=idle_top,foo")
    assert res.status_code == 422


def test_get_stats_include_retired_passes_to_summary(client, populated_db):
    res = client.get("/api/stats?include_retired=true")
    body = res.json()
    assert body["summary"]["include_retired"] is True


def test_get_stats_invalid_bool_returns_422(client):
    res = client.get("/api/stats?include_retired=maybe")
    assert res.status_code == 422
```

- [ ] **Step 9.2: 运行测试，确认失败**

```bash
uv run pytest tests/api/test_stats_router.py -v
```

预期：全 FAIL（router 不存在）。

- [ ] **Step 9.3: 实现 router**

```python
# src/asset_hub/api/routers/stats.py
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session

from asset_hub.api.deps import get_session
from asset_hub.api.schemas.stats import StatsField, StatsRead
from asset_hub.errors import ValidationError
from asset_hub.services.stats import ALL_FIELDS, StatsService

router = APIRouter()


def _parse_fields(raw: str | None) -> set[StatsField] | None:
    if raw is None or raw == "":
        return None
    parts = {p.strip() for p in raw.split(",") if p.strip()}
    unknown = parts - ALL_FIELDS
    if unknown:
        raise ValidationError(
            f"fields 含未知段：{sorted(unknown)}；可选：{sorted(ALL_FIELDS)}"
        )
    return parts  # type: ignore[return-value]


@router.get(
    "",
    response_model=StatsRead,
    response_model_exclude_none=True,  # 让未请求段在 JSON 中缺省而非显式 null
)
def get_stats(
    session: Annotated[Session, Depends(get_session)],
    include_retired: bool = False,
    include_disposed: bool = False,
    fields: str | None = None,
):
    parsed = _parse_fields(fields)
    return StatsService(session).get_dashboard_stats(
        include_retired=include_retired,
        include_disposed=include_disposed,
        fields=parsed,
    )
```

注册：

```python
# src/asset_hub/api/app.py 找到 app.include_router(...) 段，增：
from asset_hub.api.routers import stats as stats_router
app.include_router(stats_router.router, prefix="/api/stats", tags=["stats"])
```

- [ ] **Step 9.4: 运行测试，确认通过**

```bash
uv run pytest tests/api/test_stats_router.py -v
```

预期：8 PASS。

- [ ] **Step 9.5: 提交**

```bash
git add src/asset_hub/api/routers/stats.py src/asset_hub/api/app.py tests/api/test_stats_router.py
git commit -m "feat(api): GET /api/stats 4 段聚合 + ?fields= 段选择

response_model_exclude_none=True 让未请求段在 JSON 中缺省，不返 null。
ValidationError 由 _parse_fields 抛 → app.py 既有映射转 422。"
```

---

## Task 10: asset-hub stats CLI（envelope + --fields）

**Files:**
- Create: `src/asset_hub/cli/stats_cmd.py`
- Modify: `src/asset_hub/cli/main.py`（注册 stats_app）
- Test: `tests/cli/test_stats_cli.py`

- [ ] **Step 10.1: 写失败测试**

```python
# tests/cli/test_stats_cli.py
import json

import pytest
from typer.testing import CliRunner

from asset_hub.cli.main import app

runner = CliRunner()


def test_stats_default_json_envelope(isolated_db_with_assets):
    result = runner.invoke(app, ["stats", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["success"] is True
    assert payload["error"] is None
    data = payload["data"]
    assert "type_distribution" in data
    assert "status_distribution" in data
    assert "holder_ranking" in data
    assert "idle_top" in data
    assert "summary" in data


def test_stats_fields_idle_top_only(isolated_db_with_assets):
    result = runner.invoke(app, ["stats", "--fields", "idle_top", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)["data"]
    assert data["idle_top"] is not None
    assert data.get("type_distribution") is None
    assert data["summary"] is not None  # 始终返回


def test_stats_fields_multiple(isolated_db_with_assets):
    result = runner.invoke(app, ["stats", "--fields", "idle_top,status_distribution", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)["data"]
    assert data["idle_top"] is not None
    assert data["status_distribution"] is not None


def test_stats_unknown_field_exits_2(isolated_db):
    result = runner.invoke(app, ["stats", "--fields", "foo", "--json"])
    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["success"] is False
    assert "fields" in payload["error"]


def test_stats_include_retired_reflects_in_summary(isolated_db_with_assets):
    result = runner.invoke(app, ["stats", "--include-retired", "--json"])
    data = json.loads(result.stdout)["data"]
    assert data["summary"]["include_retired"] is True
```

- [ ] **Step 10.2: 运行测试，确认失败**

```bash
uv run pytest tests/cli/test_stats_cli.py -v
```

预期：全 FAIL（无 stats 命令）

- [ ] **Step 10.3: 实现 CLI**

```python
# src/asset_hub/cli/stats_cmd.py
"""asset-hub stats — 看板 4 段聚合 / Agent 友好 fields 段选择.

命名说明（spec §B.an5）：单 token 'stats' 是项目其它命令 <resource> <action>
模式的有意例外。聚合查询 CLI 惯例（git stats / npm stats）；如未来需扩展
（如 stats refresh 缓存触发），届时升为 'stats show' 等子命令。
"""
from typing import Annotated

import typer

from asset_hub.cli.deps import cli_session
from asset_hub.cli.envelope import handle_domain_errors, print_result, to_json_dict
from asset_hub.api.schemas.stats import StatsRead
from asset_hub.services.stats import ALL_FIELDS, StatsService

stats_app = typer.Typer(
    name="stats",
    help="看板统计：4 段聚合 (类型/状态/保管人/闲置 Top 10) + summary 业务摘要。"
         "支持 --fields 段选择，Agent 仅需单段时省 token。",
    invoke_without_command=True,
    no_args_is_help=False,
)


@stats_app.callback(invoke_without_command=True)
def stats_root(
    ctx: typer.Context,
    include_retired: Annotated[bool, typer.Option("--include-retired/--no-include-retired",
        help="统计中是否包含 RETIRED 资产 (默认排除)")] = False,
    include_disposed: Annotated[bool, typer.Option("--include-disposed/--no-include-disposed",
        help="统计中是否包含 DISPOSED 资产 (默认排除)")] = False,
    fields: Annotated[str | None, typer.Option("--fields",
        help="按段选择，逗号分隔；可选 type_distribution/status_distribution/holder_ranking/idle_top；"
             "不传 = 返全部 4 段；summary 始终返回")] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """看板 4 段聚合查询。"""
    if ctx.invoked_subcommand is not None:
        return
    parsed_fields = _parse_fields_cli(fields, json_output)

    with cli_session() as session, handle_domain_errors(json_output, exit_2_on_validation=True):
        svc = StatsService(session)
        stats = svc.get_dashboard_stats(
            include_retired=include_retired,
            include_disposed=include_disposed,
            fields=parsed_fields,
        )

    if json_output:
        # response_model_exclude_none 等价：dump 时排除 None 段
        data = stats.model_dump(mode="json", exclude_none=True)
        print_result(data, json_output=True)
    else:
        _render_human_table(stats)


def _parse_fields_cli(raw: str | None, json_output: bool) -> set | None:
    if raw is None:
        return None
    parts = {p.strip() for p in raw.split(",") if p.strip()}
    unknown = parts - ALL_FIELDS
    if unknown:
        from asset_hub.errors import ValidationError
        raise ValidationError(
            f"--fields 含未知段：{sorted(unknown)}；可选：{sorted(ALL_FIELDS)}"
        )
    return parts


def _render_human_table(stats: StatsRead) -> None:
    """rich 双列表格输出（Task 11 实现，此处占位）."""
    from rich import print as rprint
    rprint(stats.model_dump(mode="python"))   # Task 11 替换为 rich Table
```

注册到 main：

```python
# src/asset_hub/cli/main.py 找到其它 app.add_typer(...)，增：
from asset_hub.cli.stats_cmd import stats_app
app.add_typer(stats_app)
```

- [ ] **Step 10.4: 运行测试，确认通过**

```bash
uv run pytest tests/cli/test_stats_cli.py -v
```

预期：5 PASS（其中人类输出测试此 task 不覆盖，Task 11 才补完）。

- [ ] **Step 10.5: 提交**

```bash
git add src/asset_hub/cli/stats_cmd.py src/asset_hub/cli/main.py tests/cli/test_stats_cli.py
git commit -m "feat(cli): asset-hub stats 命令 + --fields 段选择

agent-native P3 输出即产品：Agent 仅需单段时 token 节省 60-80%。
envelope --json 沿用项目当前形态（M2d serve 等命令同款），K1 envelope
统一与 M3e SKILL.md 同期一锅端。

命名例外：stats 单 token，spec §B.an5 注释说明非疏忽。"
```

---

## Task 11: stats CLI 人类可读 rich 双列表格

**Files:**
- Modify: `src/asset_hub/cli/stats_cmd.py`（替换 `_render_human_table`）
- Test: `tests/cli/test_stats_cli.py`（增量）

- [ ] **Step 11.1: 写失败测试**

```python
# tests/cli/test_stats_cli.py 增量
def test_stats_human_output_contains_section_headers(isolated_db_with_assets):
    """非 --json 模式 rich Table 输出应含 4 段标题."""
    result = runner.invoke(app, ["stats"])
    assert result.exit_code == 0
    out = result.stdout
    assert "类型分布" in out
    assert "状态分布" in out
    assert "保管人持有" in out
    assert "闲置时长 Top 10" in out


def test_stats_human_output_with_fields_omits_unrequested(isolated_db_with_assets):
    """--fields idle_top 模式只渲染 idle_top + summary，不显示其他段标题."""
    result = runner.invoke(app, ["stats", "--fields", "idle_top"])
    assert result.exit_code == 0
    out = result.stdout
    assert "闲置时长 Top 10" in out
    assert "类型分布" not in out
    assert "状态分布" not in out


def test_stats_human_output_shows_summary(isolated_db_with_assets):
    result = runner.invoke(app, ["stats"])
    out = result.stdout
    assert "总资产" in out or "总数" in out
    assert "在册" in out
```

- [ ] **Step 11.2: 运行测试，确认失败**

```bash
uv run pytest tests/cli/test_stats_cli.py::test_stats_human_output_contains_section_headers -v
```

预期：FAIL（Task 10 占位输出没有这些 token）

- [ ] **Step 11.3: 实现 rich Table 输出**

```python
# src/asset_hub/cli/stats_cmd.py 替换 _render_human_table
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


def _render_human_table(stats: StatsRead) -> None:
    """双列布局：左列 类型分布 + 状态分布；右列 保管人持有 + 闲置 Top 10；
    顶部 summary 摘要面板；--fields 限定时未请求段不渲染."""
    console = Console()

    # Summary panel
    summary = stats.summary
    summary_lines = [
        f"总资产 [bold]{summary.total_assets}[/bold]   "
        f"在册 [bold]{summary.registered_assets}[/bold]   "
        f"闲置 [bold]{summary.idle_count}[/bold]"
    ]
    if summary.include_retired:
        summary_lines.append("[dim]含 RETIRED[/dim]")
    if summary.include_disposed:
        summary_lines.append("[dim]含 DISPOSED[/dim]")
    console.print(Panel("\n".join(summary_lines), title="📊 概览", border_style="blue"))

    left: list = []
    right: list = []

    if stats.type_distribution is not None:
        t = Table(title="类型分布", show_header=True, header_style="bold cyan")
        t.add_column("Type"); t.add_column("Count", justify="right")
        for item in stats.type_distribution:
            t.add_row(item.type_name, str(item.count))
        left.append(t)

    if stats.status_distribution is not None:
        t = Table(title="状态分布", show_header=True, header_style="bold cyan")
        t.add_column("Status"); t.add_column("Count", justify="right")
        for status_name, count in stats.status_distribution.items():
            t.add_row(status_name, str(count))
        left.append(t)

    if stats.holder_ranking is not None:
        t = Table(title="保管人持有", show_header=True, header_style="bold cyan")
        t.add_column("Holder"); t.add_column("Count", justify="right")
        for h in stats.holder_ranking:
            t.add_row(h.holder, str(h.count))
        right.append(t)

    if stats.idle_top is not None:
        t = Table(title="闲置时长 Top 10", show_header=True, header_style="bold yellow")
        t.add_column("Code"); t.add_column("Type"); t.add_column("Days", justify="right")
        for it in stats.idle_top:
            days_style = "[red]{0}d[/red]" if it.idle_days > 90 else "{0}d"
            t.add_row(it.asset_code, it.type_name or "-", days_style.format(it.idle_days))
        right.append(t)

    # 双列展示——不存在的段那列就少
    if left and right:
        console.print(Columns([Panel.fit(_stack(left)), Panel.fit(_stack(right))]))
    elif left:
        for tbl in left:
            console.print(tbl)
    elif right:
        for tbl in right:
            console.print(tbl)


def _stack(tables: list) -> "RenderableType":
    from rich.console import Group
    return Group(*tables)
```

> 不要 import `RenderableType`——只在 doc 里提；`Group` 直接返回。

- [ ] **Step 11.4: 运行测试，确认通过**

```bash
uv run pytest tests/cli/test_stats_cli.py -v
```

预期：8 PASS（含人类输出 3 个）。

- [ ] **Step 11.5: 提交**

```bash
git add src/asset_hub/cli/stats_cmd.py tests/cli/test_stats_cli.py
git commit -m "feat(cli): stats 人类可读双列 rich Table 输出

顶部 summary panel；左列 类型/状态分布；右列 保管人/闲置 Top 10；
> 90 天闲置行染红；--fields 限定时未请求段不渲染。"
```

---

## Task 12: idle_days 字段 list 路径回归补测

**Files:**
- Test: `tests/unit/test_asset_idle_days.py`（新建）
- Test: `tests/cli/test_asset_cli.py`（增量验证 idle_days 字段）

**理由**：spec §6.1 测试矩阵列了 `tests/unit/test_asset_idle_days.py` 单测 helper 同源；前面 Task 2 单测 helper 的 `compute_idle_days_for_asset()`，但 list 路径下 `annotate_idle_days()` 应一并测。

- [ ] **Step 12.1: 写测试**

```python
# tests/unit/test_asset_idle_days.py
"""验证 AssetRead.idle_days 与 stats.idle_top.idle_days 同源."""
from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session

from asset_hub.api.schemas.asset import AssetRead
from asset_hub.models.asset import Asset, AssetStatus
from asset_hub.models.asset_type import AssetType
from asset_hub.models.state_transition import StateTransitionRecord, TransitionKind
from asset_hub.services.asset import AssetService
from asset_hub.services.stats import StatsService


def test_assetread_idle_days_matches_stats_idle_top(session: Session):
    """同一资产在 list 路径与 stats idle_top 的 idle_days 应一致."""
    at = AssetType(name="L", custom_fields=[])
    session.add(at); session.flush()
    a = Asset(asset_code="L-001", name="L1", type_id=at.id, status=AssetStatus.IDLE)
    session.add(a); session.flush()
    session.add(StateTransitionRecord(
        asset_id=a.id, kind=TransitionKind.RETURN,
        from_status=AssetStatus.IN_USE, to_status=AssetStatus.IDLE,
        created_at=datetime.now(UTC) - timedelta(days=42),
    ))
    session.flush()

    asset_svc = AssetService(session)
    stats_svc = StatsService(session)

    annotated = asset_svc.annotate_idle_days([a])[0]
    list_days = AssetRead.model_validate(annotated).idle_days

    stats = stats_svc.get_dashboard_stats(fields={"idle_top"})
    stats_days = stats.idle_top[0].idle_days

    assert list_days == stats_days
    assert list_days == 42  # 时间精度允许 ±1


def test_in_use_asset_idle_days_is_none(session: Session):
    at = AssetType(name="L", custom_fields=[])
    session.add(at); session.flush()
    a = Asset(asset_code="L-002", name="L2", type_id=at.id, status=AssetStatus.IN_USE, holder="x")
    session.add(a); session.flush()

    annotated = AssetService(session).annotate_idle_days([a])[0]
    assert AssetRead.model_validate(annotated).idle_days is None
```

- [ ] **Step 12.2: 运行测试**

```bash
uv run pytest tests/unit/test_asset_idle_days.py -v
```

预期：2 PASS。

- [ ] **Step 12.3: 提交**

```bash
git add tests/unit/test_asset_idle_days.py
git commit -m "test(asset): idle_days 跨 list/stats 路径同源回归"
```

---

## Task 13: PR-1 验收

**Files:** N/A（纯验证）

- [ ] **Step 13.1: 全套后端测试通过**

```bash
uv run pytest -v
```

预期：全 PASS。新增/修改 ≥ 50 个测试 case。

- [ ] **Step 13.2: ruff 全 clean**

```bash
uv run ruff check .
```

预期：无 issue。

- [ ] **Step 13.3: alembic 无悬挂迁移**

```bash
uv run alembic check
```

预期：无 unmerged migration。本 PR 无 schema 变更（idle_days 是 @property + DTO 字段，非 DB 列）。

- [ ] **Step 13.4: 手动 CLI 烟测**

```bash
uv run asset-hub stats --json | head -50
uv run asset-hub stats --fields idle_top --json
uv run asset-hub stats --include-retired
uv run asset-hub asset list --status IDLE --sort idle_days --order desc --limit 5 --json
uv run asset-hub asset list --sort foo --json   # 应 exit 2
```

预期：前 4 条返合理结构；最后一条 exit code 2 + error envelope。

- [ ] **Step 13.5: PR 描述准备**

```bash
git log --oneline main..HEAD
```

确认 commit 顺序：

1. `feat(stats): 加 StatsRead/StatsSummary/StatsField`
2. `feat(services): idle_days 子查询 helper`
3. `feat(asset): AssetRead 补 idle_days`
4. `feat(asset): list_assets 加 sort/order/limit/offset`
5. `feat(api): GET /api/assets 透传 4 参数`
6. `feat(cli): asset list 加 --sort/--order/--limit/--offset`
7. `test(api): C3 回归——锁定 type_name`
8. `feat(stats): StatsService.get_dashboard_stats`
9. `feat(api): GET /api/stats + ?fields=`
10. `feat(cli): asset-hub stats + --fields`
11. `feat(cli): stats 人类可读双列 rich Table`
12. `test(asset): idle_days 跨路径同源回归`

- [ ] **Step 13.6: PR-1 完结**

提交 PR，附 spec link + 改动面摘要：

```
M3b PR-1：后端 stats 端点 + list 三参数搭车

主线：
- GET /api/stats 4 段聚合 + ?fields= 段选择 + summary 业务摘要
- asset-hub stats CLI（含 --fields）
- AssetRead 补 idle_days 字段

搭车（agent-native C2 原子化）：
- asset list service/router/CLI 加 sort/order/limit/offset；Agent 可
  asset list --status IDLE --sort idle_days --limit 10 等价 stats idle_top

C3 follow-up：仅加回归测试锁定 AssetRead.type_name 现状（M3a 已实现）。

测试：50+ case 覆盖 unit / api / cli 三层；TDD 节奏每段聚合先测后实现。

Spec: docs/superpowers/specs/2026-05-06-m3b-dashboard-stats-design.md
```

---

## Self-Review Checklist

实施期完成 13 task 后跑：

- [ ] spec §1.1 包含项 9 条都有对应 task 覆盖
- [ ] §2.1 响应字段 / §2.2 service 签名 / §2.3 4 段查询 / §2.4 router / §2.6 list 三参数 全部落地
- [ ] §4 CLI `--fields` / 命名例外注释 落地
- [ ] §6.1 测试矩阵后端 6 行全有对应 test 文件
- [ ] §8 决策追踪 11 项中后端涉及（B.idle / B.an1 / an2 / an5 / an6）全部体现在代码里
- [ ] 无 TBD/TODO/placeholder
- [ ] PR commit 顺序与 §5.1 / 实施期实际一致
- [ ] alembic 无变更（idle_days 非 DB 列）

PR-1 合并后跑 `pnpm --dir frontend gen:api` 拉新 schema，开 PR-2。
