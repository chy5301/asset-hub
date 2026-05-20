# CL-1 · brand 升 Asset 顶层公共字段 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `brand` 从 `AssetType.custom_fields` 升为 `Asset` 顶层公共字段（沿用 v2.0 PR-3 `model` 拆列模式）。全栈列序统一为 `name → brand → model`。同步加 `AssetType` reserved key 全集校验（16 项），杜绝顶层 vs custom 同名共存。

**Architecture:** 数据模型 `Asset.brand` 紧贴 `name`、`model` 之间，加 `ix_assets_brand` 索引；alembic v4 migration 同次扫表把 `custom_data.brand`（顶层为 null 时）回填到顶层；`services/asset_type.py` 加 `RESERVED_CUSTOM_FIELD_KEYS` frozenset 在 `create_type` / `update_type` 校验；DTO / Router / CLI / 前端表单 / 详情 / 列表 / 导出 / examples / SKILL.md 跟随。

**Tech Stack:** SQLModel + alembic `batch_alter_table`（SQLite 改表必需）/ Pydantic v2 / Typer / React + TanStack + Zod。

**Spec 来源**：`docs/superpowers/specs/2026-05-17-m4-batch-plan-design.md` CL-1 段。
**先决条件**：当前 alembic head `2d589d84e584`（v3 model column）；下一份 migration `down_revision = "2d589d84e584"`。
**预期开销**：单 PR / 6 phase / ~20 task / commit 主干约 8-10 条。SemVer MINOR（加 user-visible 字段）。**阻塞 M4 主 PR**。

---

## Phase 1：数据模型 + alembic v4 migration

### Task 1.1：写 migration 失败测试

**Files:**

- Modify: `D:\CONGHAOYANG\Projects\tools\asset-hub\tests\migration\test_v3_asset_model_column.py`（如不存在则 `Create` 一个 `test_v4_asset_brand_column.py`）

参考现有 v3 migration 测试模式（spec scan §15 提到 `test_v2_state_machine.py downgrade -2` 已适配 v3 head）。

- [ ] **Step 1：在 `tests/migration/` 下新建 `test_v4_asset_brand_column.py`**

```python
"""v4 asset brand column migration tests.

校验 alembic v4 migration：
- upgrade 在 assets 表加 brand 列 + ix_assets_brand 索引
- 数据回填：custom_data.brand 在顶层 brand 为 null 时回填到顶层
- downgrade 反向 drop（仅 schema 反向；数据回填不可逆）
"""

from alembic import command
from sqlalchemy import inspect, text


def test_v4_upgrade_adds_brand_column_and_index(alembic_config, session):
    """upgrade head 后 assets 表应有 brand 列 + ix_assets_brand 索引。"""
    command.upgrade(alembic_config, "head")

    insp = inspect(session.bind)
    columns = {c["name"] for c in insp.get_columns("assets")}
    assert "brand" in columns

    indexes = {i["name"] for i in insp.get_indexes("assets")}
    assert "ix_assets_brand" in indexes


def test_v4_data_migration_backfills_custom_data_brand(alembic_config, session):
    """custom_data.brand 在顶层 brand 为 null 时应回填到顶层。"""
    # 先 upgrade 到 v3 head（含 model 列但无 brand）
    command.upgrade(alembic_config, "2d589d84e584")

    # 造 3 行测试数据：
    # row1: custom_data 含 brand，顶层暂不存在 brand 列 → 回填后顶层 = "Lenovo"
    # row2: custom_data 无 brand → 回填后顶层 = null
    # row3: custom_data.brand = "" 空字符串 → 回填后顶层 = null（spec 决策：空串视同未填）
    session.execute(
        text(
            "INSERT INTO assets (id, asset_code, name, model, type_id, status, "
            "custom_data, created_at, updated_at) VALUES "
            "(:id1, 'LP-001', 'Asset 1', NULL, :tid, 'IDLE', "
            ":cd1, '2026-01-01', '2026-01-01'),"
            "(:id2, 'LP-002', 'Asset 2', NULL, :tid, 'IDLE', "
            ":cd2, '2026-01-01', '2026-01-01'),"
            "(:id3, 'LP-003', 'Asset 3', NULL, :tid, 'IDLE', "
            ":cd3, '2026-01-01', '2026-01-01')"
        ),
        {
            "id1": "11111111-1111-1111-1111-111111111111",
            "id2": "22222222-2222-2222-2222-222222222222",
            "id3": "33333333-3333-3333-3333-333333333333",
            "tid": "00000000-0000-0000-0000-000000000000",
            "cd1": '{"brand": "Lenovo"}',
            "cd2": "{}",
            "cd3": '{"brand": ""}',
        },
    )
    session.commit()

    # 升 head 触发 v4 migration（含数据回填）
    command.upgrade(alembic_config, "head")

    rows = session.execute(
        text("SELECT asset_code, brand FROM assets ORDER BY asset_code")
    ).all()
    assert rows[0] == ("LP-001", "Lenovo")
    assert rows[1] == ("LP-002", None)
    assert rows[2] == ("LP-003", None)


def test_v4_downgrade_drops_brand_column(alembic_config, session):
    """downgrade -1 应反向 drop brand 列 + 索引（数据不可逆已 ack）。"""
    command.upgrade(alembic_config, "head")
    command.downgrade(alembic_config, "-1")

    insp = inspect(session.bind)
    columns = {c["name"] for c in insp.get_columns("assets")}
    assert "brand" not in columns
    indexes = {i["name"] for i in insp.get_indexes("assets")}
    assert "ix_assets_brand" not in indexes
```

**fixture 来源**：`alembic_config` 和 `session` fixture 在 `tests/migration/conftest.py`（spec scan 没列出但 v3 migration 测试一定用了同套）。如签名不对，对齐 v3 测试的 import。

- [ ] **Step 2：跑测试看 fail**

```bash
uv run pytest tests/migration/test_v4_asset_brand_column.py -v
```

期望 3 个全 FAIL（迁移文件还没写）。

### Task 1.2：改 Asset 模型加 brand 字段

**Files:**

- Modify: `D:\CONGHAOYANG\Projects\tools\asset-hub\src\asset_hub\models\asset.py`（行 31-34 之间插入 brand；当前 v3 model 在行 32-34）

- [ ] **Step 1：插入 brand 字段**

当前 `Asset` 类定义（行 23-45，spec scan 已贴）行 31-34 为：

```python
    name: str = Field(index=True)
    model: str | None = Field(
        default=None, index=True
    )  # nullable / non-unique; index 与 name 对齐
```

改为：

```python
    name: str = Field(index=True)
    brand: str | None = Field(
        default=None, index=True
    )  # nullable / non-unique; index 与 name 对齐
    model: str | None = Field(
        default=None, index=True
    )  # nullable / non-unique; index 与 name 对齐
```

**说明**：

- 列序 `name → brand → model` 锁定（spec 决策 Y）
- index=True：与 model 对齐，便于按品牌排序 / 筛选

### Task 1.3：用 alembic autogenerate 生成 v4 migration

**Files:**

- Create: `D:\CONGHAOYANG\Projects\tools\asset-hub\src\asset_hub\alembic\versions\<timestamp>_<rev_id>_v4_asset_brand_column.py`

- [ ] **Step 1：autogenerate**

```bash
uv run alembic revision --autogenerate -m "v4 asset brand column"
```

期望生成新文件 `src/asset_hub/alembic/versions/<timestamp>_<rev_id>_v4_asset_brand_column.py`。

- [ ] **Step 2：手改 autogenerate 输出，加数据回填**

Open 生成的 v4 migration 文件，确认 `down_revision = "2d589d84e584"`（指向 v3 head）。

期望 autogenerate 已生成 schema upgrade / downgrade。改成：

```python
"""v4 asset brand column

Revision ID: <auto>
Revises: 2d589d84e584
Create Date: <auto>

CL-1：Asset 顶层新增 brand 列（nullable / non-unique），紧贴 name 之后、model 之前。
数据迁移：扫所有 row，将 custom_data.brand（非空字符串、顶层 brand 为 null 时）回填到顶层 brand 列。
custom_data.brand 键保留不动（JSON 弹性，零破坏）；用户应在升级后手动从 AssetType 删 brand custom_field。
"""

from collections.abc import Sequence
import json

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "<auto>"
down_revision: str | Sequence[str] | None = "2d589d84e584"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema + 数据回填 custom_data.brand → 顶层 brand。"""
    with op.batch_alter_table("assets", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("brand", sqlmodel.sql.sqltypes.AutoString(), nullable=True)
        )
        batch_op.create_index(batch_op.f("ix_assets_brand"), ["brand"], unique=False)

    # 数据回填：custom_data.brand → 顶层 brand（仅当顶层 brand 为 null 且 custom_data.brand 非空字符串）
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT id, custom_data FROM assets "
            "WHERE brand IS NULL AND custom_data IS NOT NULL"
        )
    ).all()
    for asset_id, custom_data_str in rows:
        if not custom_data_str:
            continue
        try:
            cd = json.loads(custom_data_str) if isinstance(custom_data_str, str) else custom_data_str
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(cd, dict):
            continue
        brand_val = cd.get("brand")
        if isinstance(brand_val, str) and brand_val.strip():
            bind.execute(
                sa.text("UPDATE assets SET brand = :b WHERE id = :id"),
                {"b": brand_val, "id": asset_id},
            )


def downgrade() -> None:
    """Downgrade schema（数据回填不可逆，已在 spec 风险段 ack）。"""
    with op.batch_alter_table("assets", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_assets_brand"))
        batch_op.drop_column("brand")
```

**说明**：

- `batch_alter_table` 是 SQLite 改表必需（CLAUDE.md 明文）
- 数据回填用裸 `op.get_bind()` 执行原 SQL，不依赖 ORM（migration 应自包含）
- 空字符串视同未填（`brand_val.strip()` 过滤）—— test case 已锁
- downgrade 不还原数据（spec 风险 #1：回滚不可逆）
- `custom_data` 在 SQLite 实际存储是 JSON 字符串还是 dict 取决于 SQLAlchemy driver—— `isinstance(custom_data_str, str)` 兜底两种情况

- [ ] **Step 3：跑 migration test 看 pass**

```bash
uv run pytest tests/migration/test_v4_asset_brand_column.py -v
```

期望 3 个 PASS。

- [ ] **Step 4：跑全 migration test 集合**

```bash
uv run pytest tests/migration/ -v
```

期望全绿（包括 v2/v3 历史 migration test 不被新 head 破坏）。

- [ ] **Step 5：commit**

```bash
git add src/asset_hub/models/asset.py src/asset_hub/alembic/versions/*_v4_asset_brand_column.py tests/migration/test_v4_asset_brand_column.py
git commit -m "feat(model): Asset 顶层加 brand 列 + v4 alembic migration 含数据回填

CL-1 Phase 1：
- Asset.brand: str | None，index=True，位置紧贴 name 之后、model 之前
- alembic v4 migration：add_column + ix_assets_brand 索引 + batch_alter_table
- 数据回填：扫所有 row，custom_data.brand 非空字符串且顶层 brand 为 null 时回填到顶层
- 空字符串视同未填；custom_data.brand 键保留不动（JSON 弹性零破坏）
- downgrade 反向 schema drop；数据回填不可逆（spec 已 ack）"
```

---

## Phase 2：AssetType reserved key 校验

### Task 2.1：写 reserved key 失败测试

**Files:**

- Modify: `D:\CONGHAOYANG\Projects\tools\asset-hub\tests\unit\test_asset_type_service.py`（如不存在则 `Create`；现有应在 `tests/unit/` 下，可 `grep -l "create_type" tests/`）

- [ ] **Step 1：写测试**

```python
def test_create_type_rejects_reserved_custom_field_key(session):
    """create_type 含 reserved key 的 custom_field 应 ValidationError。"""
    from asset_hub.services.asset_type import AssetTypeService
    from asset_hub.errors import ValidationError
    import pytest

    svc = AssetTypeService(session)
    # 测 brand（CL-1 新增）
    with pytest.raises(ValidationError) as exc:
        svc.create_type(
            name="Test",
            code_prefix="TST",
            custom_fields=[{"key": "brand", "label": "品牌", "type": "string"}],
        )
    assert "brand" in str(exc.value)
    assert "reserved" in str(exc.value).lower() or "顶层" in str(exc.value)


@pytest.mark.parametrize(
    "reserved_key",
    [
        "asset_code", "serial_number", "name", "model", "brand",
        "holder", "location", "notes", "acquired_at",
        "sn",
        "type", "type_name", "type_id", "status", "id", "custom_data",
    ],
)
def test_create_type_rejects_all_reserved_keys(session, reserved_key):
    """全集 16 项 reserved 都应被拒。"""
    from asset_hub.services.asset_type import AssetTypeService
    from asset_hub.errors import ValidationError
    import pytest

    svc = AssetTypeService(session)
    with pytest.raises(ValidationError):
        svc.create_type(
            name=f"Test-{reserved_key}",
            code_prefix="TST",
            custom_fields=[{"key": reserved_key, "label": "x", "type": "string"}],
        )


def test_create_type_accepts_non_reserved_key(session):
    """非 reserved key 应通过。"""
    from asset_hub.services.asset_type import AssetTypeService

    svc = AssetTypeService(session)
    result = svc.create_type(
        name="Test-OK",
        code_prefix="TOK",
        custom_fields=[{"key": "warranty_until", "label": "保修截止", "type": "date"}],
    )
    assert result.id is not None


def test_update_type_also_rejects_reserved_key(session):
    """update_type 同样应校验 reserved。"""
    from asset_hub.services.asset_type import AssetTypeService
    from asset_hub.errors import ValidationError
    import pytest

    svc = AssetTypeService(session)
    t = svc.create_type(name="T1", code_prefix="T1A", custom_fields=[])
    with pytest.raises(ValidationError):
        svc.update_type(
            type_id=t.id,
            custom_fields=[{"key": "model", "label": "型号", "type": "string"}],
        )
```

- [ ] **Step 2：跑 test 看 fail**

```bash
uv run pytest tests/unit/test_asset_type_service.py -v -k reserved
```

期望全 FAIL（reserved 校验未实现）。

### Task 2.2：实现 `RESERVED_CUSTOM_FIELD_KEYS` + 校验

**Files:**

- Modify: `D:\CONGHAOYANG\Projects\tools\asset-hub\src\asset_hub\services\asset_type.py`

- [ ] **Step 1：在 `asset_type.py` 顶部加 frozenset**

紧接 import 之后、第一个 class 定义之前：

```python
# CL-1：Asset 顶层 user-writable 字段 + 别名 + 系统字段集合，不允许在 custom_fields[].key 重名
RESERVED_CUSTOM_FIELD_KEYS: frozenset[str] = frozenset({
    # Asset 顶层 user-writable 字段
    "asset_code", "serial_number", "name", "model", "brand",
    "holder", "location", "notes", "acquired_at",
    # CLI / 直觉别名
    "sn",
    # 系统/关系字段（防恶意撞）
    "type", "type_name", "type_id", "status", "id", "custom_data",
})


def _check_reserved_keys(custom_fields: list | None) -> None:
    """校验 custom_fields[].key 不与 Asset 顶层字段 / 别名 / 系统字段重名。

    raise ValidationError + 提示用户用顶层字段或换 key。
    """
    from asset_hub.errors import ValidationError

    if not custom_fields:
        return
    for f in custom_fields:
        if isinstance(f, dict):
            key = f.get("key")
        else:
            key = getattr(f, "key", None)
        if isinstance(key, str) and key in RESERVED_CUSTOM_FIELD_KEYS:
            raise ValidationError(
                f"key '{key}' 是 Asset 顶层公共字段或保留名，请用顶层字段写入或换 key。"
                f" reserved 全集: {sorted(RESERVED_CUSTOM_FIELD_KEYS)}"
            )
```

- [ ] **Step 2：在 `create_type` 和 `update_type` 调用 `_check_reserved_keys`**

修改 `create_type` 函数（行 38-44 签名之后的函数体）—— 找到 `_validate_and_dump_fields(custom_fields)` 调用之前 / 之后插入 `_check_reserved_keys(custom_fields)`。具体：

```python
def create_type(
    self,
    name: str,
    code_prefix: str,
    description: str | None = None,
    custom_fields: list | None = None,
) -> TypeRead:
    _check_reserved_keys(custom_fields)  # CL-1 新增
    # ... 原有逻辑 ...
```

同样改 `update_type`（行 98-104 签名之后）：

```python
def update_type(
    self,
    type_id: uuid.UUID,
    name: str | None = None,
    description: str | None = None,
    custom_fields: list | None = None,
) -> TypeRead:
    if custom_fields is not None:
        _check_reserved_keys(custom_fields)  # CL-1 新增
    # ... 原有逻辑 ...
```

- [ ] **Step 3：跑 test 看 pass**

```bash
uv run pytest tests/unit/test_asset_type_service.py -v
```

期望全 PASS（含 16 项 parametrize 全过）。

- [ ] **Step 4：commit**

```bash
git add src/asset_hub/services/asset_type.py tests/unit/test_asset_type_service.py
git commit -m "feat(asset_type): AssetType custom_fields[].key 加 reserved 全集校验

CL-1 Phase 2：
- RESERVED_CUSTOM_FIELD_KEYS frozenset 16 项：Asset 顶层字段 9 + CLI 别名 sn + 系统/关系字段 6
- create_type / update_type 调 _check_reserved_keys；违规 → ValidationError + hint
- 对现有 AssetType 含 reserved key 重名 custom_field 零破坏（仅 future create/update 拒绝）
- 顺修 v1 / v2.0 PR-3 漏的校验（serial_number / model 当时也没锁）"
```

---

## Phase 3：Asset service + sort + q

### Task 3.1：写 register / update_asset / sort / q 测试

**Files:**

- Modify: `D:\CONGHAOYANG\Projects\tools\asset-hub\tests\unit\test_asset_service.py`（或 `tests/unit/test_asset.py`，看现有命名）

- [ ] **Step 1：写测试**

```python
def test_register_with_brand(session):
    """register 应接受 brand 参数并落库。"""
    from asset_hub.services.asset import AssetService
    from asset_hub.services.asset_type import AssetTypeService

    type_svc = AssetTypeService(session)
    t = type_svc.create_type(name="Laptop", code_prefix="LP", custom_fields=[])
    svc = AssetService(session)
    a = svc.register(
        name="Asset 1",
        type_id=t.id,
        custom_data={},
        brand="Lenovo",
        model="ThinkPad T14",
    )
    assert a.brand == "Lenovo"


def test_update_asset_brand_unset_keeps_current(session):
    """update_asset 不传 brand → keep current。"""
    from asset_hub.services.asset import AssetService
    from asset_hub.services.asset_type import AssetTypeService

    type_svc = AssetTypeService(session)
    t = type_svc.create_type(name="Laptop", code_prefix="LP", custom_fields=[])
    svc = AssetService(session)
    a = svc.register(name="A", type_id=t.id, custom_data={}, brand="Lenovo")
    a2 = svc.update_asset(a.id, name="A-new")  # 不传 brand
    assert a2.brand == "Lenovo"  # 保留


def test_update_asset_brand_explicit_null_clears(session):
    """update_asset 显式传 brand=None → 清空。"""
    from asset_hub.services.asset import AssetService
    from asset_hub.services.asset_type import AssetTypeService

    type_svc = AssetTypeService(session)
    t = type_svc.create_type(name="Laptop", code_prefix="LP", custom_fields=[])
    svc = AssetService(session)
    a = svc.register(name="A", type_id=t.id, custom_data={}, brand="Lenovo")
    a2 = svc.update_asset(a.id, brand=None)
    assert a2.brand is None  # 清空


def test_list_filtered_q_matches_brand(session):
    """list_filtered q 应能搜到 brand。"""
    from asset_hub.services.asset import AssetService
    from asset_hub.services.asset_type import AssetTypeService

    type_svc = AssetTypeService(session)
    t = type_svc.create_type(name="L", code_prefix="LP", custom_fields=[])
    svc = AssetService(session)
    svc.register(name="A1", type_id=t.id, custom_data={}, brand="Lenovo")
    svc.register(name="A2", type_id=t.id, custom_data={}, brand="Apple")

    results = svc.list_filtered(q="Lenovo")
    assert len(results) == 1
    assert results[0].brand == "Lenovo"


def test_sort_by_brand(session):
    """list_filtered sort_by='brand' 应可用。"""
    from asset_hub.services.asset import AssetService
    from asset_hub.services.asset_type import AssetTypeService

    type_svc = AssetTypeService(session)
    t = type_svc.create_type(name="L", code_prefix="LP", custom_fields=[])
    svc = AssetService(session)
    svc.register(name="A1", type_id=t.id, custom_data={}, brand="Lenovo")
    svc.register(name="A2", type_id=t.id, custom_data={}, brand="Apple")

    results = svc.list_filtered(sort_by="brand")
    assert [r.brand for r in results] == ["Apple", "Lenovo"]
```

- [ ] **Step 2：跑 test 看 fail**

```bash
uv run pytest tests/unit/test_asset_service.py -v -k brand
```

期望全 FAIL（service 还没加 brand 参数）。

### Task 3.2：实现 service 层 brand 透传

**Files:**

- Modify: `D:\CONGHAOYANG\Projects\tools\asset-hub\src\asset_hub\services\asset.py`
- Modify: `D:\CONGHAOYANG\Projects\tools\asset-hub\src\asset_hub\repositories\asset.py`

- [ ] **Step 1：改 `register` 加 brand 参数**

`services/asset.py` 行 49-60：

```python
def register(
    self,
    name: str,
    type_id: uuid.UUID,
    custom_data: dict,
    serial_number: str | None = None,
    brand: str | None = None,   # CL-1 新增（位置紧邻 name 后、model 前；CLI 一致 --name → --brand → --model）
    model: str | None = None,
    holder: str | None = None,
    location: str | None = None,
    notes: str | None = None,
    acquired_at: date | None = None,
) -> Asset:
    # ... 函数体内：构造 Asset(...) 时把 brand 也传进去 ...
```

找到函数体内 `Asset(...)` 构造处（行号未知，找含 `name=name, type_id=type_id` 的 Asset 实例化），在 `model=model,` **之前**插入 `brand=brand,`。

- [ ] **Step 2：改 `update_asset` 加 brand 参数（UNSET 哨兵）**

`services/asset.py` 行 195-204：

```python
def update_asset(
    self,
    asset_id: uuid.UUID,
    name: str | None = None,
    serial_number: str | UnsetType = UNSET,
    brand: str | None | UnsetType = UNSET,   # CL-1 新增（顺序紧邻 name 后、model 前）
    model: str | None | UnsetType = UNSET,
    notes: str | UnsetType = UNSET,
    custom_data: dict | UnsetType = UNSET,
    acquired_at: date | None | UnsetType = UNSET,
) -> Asset:
```

在函数体行 213-223 现有 `if not isinstance(serial_number, UnsetType):` 之后、`if not isinstance(model, UnsetType):` **之前**插入：

```python
    if not isinstance(brand, UnsetType):
        a.brand = brand
```

- [ ] **Step 3：改 `SortByField` Literal + WHITELIST**

`services/asset.py` 行 18-27：

```python
SortByField = Literal[
    "name",
    "brand",   # CL-1 新增
    "model",
    "asset_code",
    "serial_number",
    "created_at",
    "updated_at",
    "acquired_at",
    "idle_days",
]
```

行 28-39：

```python
SORT_FIELD_WHITELIST = frozenset(
    {
        "name",
        "brand",   # CL-1 新增
        "model",
        "asset_code",
        "serial_number",
        "created_at",
        "updated_at",
        "acquired_at",
        "idle_days",
    }
)
```

- [ ] **Step 4：改 `repositories/asset.py` 的 `_SORT_COLUMN_MAP` 和 q OR-chain**

`repositories/asset.py` 行 12-20：

```python
_SORT_COLUMN_MAP: dict[str, object] = {
    "name": Asset.name,
    "brand": Asset.brand,   # CL-1 新增
    "model": Asset.model,
    "asset_code": Asset.asset_code,
    "serial_number": Asset.serial_number,
    "created_at": Asset.created_at,
    "updated_at": Asset.updated_at,
    "acquired_at": Asset.acquired_at,
}
```

行 68-75 q OR-chain：

```python
if q is not None:
    stmt = stmt.where(
        Asset.name.contains(q)
        | Asset.brand.contains(q)   # CL-1 新增
        | Asset.serial_number.contains(q)
        | Asset.model.contains(q)
        | Asset.notes.contains(q)
        | Asset.asset_code.contains(q)
    )
```

- [ ] **Step 5：跑 test 看 pass**

```bash
uv run pytest tests/unit/test_asset_service.py -v -k brand
```

期望全 PASS。

- [ ] **Step 6：跑 service 层全测**

```bash
uv run pytest tests/unit/ -v
```

期望全绿（含 phase 2 reserved key 测）。

- [ ] **Step 7：commit**

```bash
git add src/asset_hub/services/asset.py src/asset_hub/repositories/asset.py tests/unit/test_asset_service.py
git commit -m "feat(asset): service 层加 brand 参数 + sort/q 覆盖

CL-1 Phase 3：
- register / update_asset 加 brand 参数（update 用 UNSET 哨兵区分未传 vs null 清空）
- SortByField Literal / SORT_FIELD_WHITELIST / _SORT_COLUMN_MAP 三处加 brand
- list_filtered q OR-chain 加 Asset.brand.contains(q)
- 列序统一 name → brand → model"
```

---

## Phase 4：DTO + Router + API 测试

### Task 4.1：写 API 失败测试

**Files:**

- Modify: `D:\CONGHAOYANG\Projects\tools\asset-hub\tests\api\test_asset_routes.py`

- [ ] **Step 1：写测试**

```python
def test_post_asset_with_brand(client, asset_type_fixture):
    """POST /api/assets body.brand 应落库 + response 含 brand。"""
    resp = client.post(
        "/api/assets",
        json={
            "name": "A1",
            "type_id": str(asset_type_fixture.id),
            "brand": "Lenovo",
            "model": "ThinkPad T14",
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["brand"] == "Lenovo"
    assert data["model"] == "ThinkPad T14"


def test_patch_asset_brand_unset_keeps(client, asset_with_brand):
    """PATCH 不传 brand → 保留 current。"""
    resp = client.patch(
        f"/api/assets/{asset_with_brand.id}",
        json={"name": "renamed"},  # 不传 brand
    )
    assert resp.status_code == 200
    assert resp.json()["brand"] == "Lenovo"  # 保留


def test_patch_asset_brand_explicit_null_clears(client, asset_with_brand):
    """PATCH brand=null → 清空。"""
    resp = client.patch(
        f"/api/assets/{asset_with_brand.id}",
        json={"brand": None},
    )
    assert resp.status_code == 200
    assert resp.json()["brand"] is None


def test_list_assets_q_matches_brand(client, asset_with_brand):
    """GET /api/assets?q=Lenovo 应能搜到。"""
    resp = client.get("/api/assets", params={"q": "Lenovo"})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert any(a["brand"] == "Lenovo" for a in items)


def test_list_assets_sort_by_brand(client, multiple_assets_with_brands):
    """GET /api/assets?sort_by=brand 应可用。"""
    resp = client.get("/api/assets", params={"sort_by": "brand"})
    assert resp.status_code == 200
    brands = [a["brand"] for a in resp.json()["items"] if a["brand"]]
    assert brands == sorted(brands)
```

需要 fixture `asset_with_brand` / `multiple_assets_with_brands` —— 在 conftest.py 加，或本文件内 fixture。具体：

```python
@pytest.fixture
def asset_with_brand(client, asset_type_fixture):
    resp = client.post(
        "/api/assets",
        json={"name": "A1", "type_id": str(asset_type_fixture.id), "brand": "Lenovo"},
    )
    return SimpleNamespace(**resp.json())
```

- [ ] **Step 2：跑 test 看 fail**

```bash
uv run pytest tests/api/test_asset_routes.py -v -k brand
```

期望全 FAIL（DTO 还没加 brand）。

### Task 4.2：实现 DTO + Router

**Files:**

- Modify: `D:\CONGHAOYANG\Projects\tools\asset-hub\src\asset_hub\api\schemas\asset.py`
- Modify: `D:\CONGHAOYANG\Projects\tools\asset-hub\src\asset_hub\api\routers\asset.py`

- [ ] **Step 1：DTO 加 brand**

`api/schemas/asset.py`：

`AssetCreate`（行 10-21）：在 `model: str | None = None` **之前**插入：

```python
class AssetCreate(BaseModel):
    name: str
    type_id: UUID
    serial_number: str | None = None
    brand: str | None = None   # CL-1 新增（位置 name 后、model 前）
    model: str | None = None
    holder: str | None = None
    location: str | None = None
    notes: str | None = None
    custom_data: dict = Field(default_factory=dict)
    acquired_at: date | None = None
```

`AssetUpdate`（行 24-36）：同样在 `model` 前插入 brand：

```python
class AssetUpdate(BaseModel):
    name: str | None = None
    serial_number: str | None = None
    brand: str | None = None   # CL-1 新增
    model: str | None = None
    notes: str | None = None
    custom_data: dict | None = None
    acquired_at: date | None = None
```

`AssetRead`（行 39-57）：在 `model: str | None` 前插入：

```python
class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    asset_code: str
    name: str
    serial_number: str | None
    brand: str | None   # CL-1 新增
    model: str | None
    type_id: UUID
    type_name: str | None
    status: AssetStatus
    holder: str | None
    location: str | None
    notes: str | None
    custom_data: dict
    acquired_at: date | None
    idle_days: int | None = None
    created_at: UtcDatetime
    updated_at: UtcDatetime
```

- [ ] **Step 2：Router `create_asset` 透传 brand**

`api/routers/asset.py` 的 `create_asset` 函数。找到 `service.register(...)` 调用，在 `model=body.model,` 之前插入 `brand=body.brand,`。具体 grep：

```bash
grep -n "def create_asset" src/asset_hub/api/routers/asset.py
```

定位函数后，把 `service.register(name=body.name, ..., model=body.model, ...)` 改成包含 `brand=body.brand,`。

- [ ] **Step 3：跑 API test 看 pass**

```bash
uv run pytest tests/api/test_asset_routes.py -v -k brand
```

期望全 PASS。

- [ ] **Step 4：跑全 API 测**

```bash
uv run pytest tests/api/ -v
```

期望全绿（含历史 model / sn 相关测试不破坏）。

- [ ] **Step 5：commit**

```bash
git add src/asset_hub/api/schemas/asset.py src/asset_hub/api/routers/asset.py tests/api/test_asset_routes.py
git commit -m "feat(api): AssetCreate/Update/Read 加 brand + router 透传

CL-1 Phase 4：
- AssetCreate / AssetUpdate / AssetRead DTO 三件套加 brand 字段，位置紧邻 name 之后、model 之前
- router create_asset 加 brand=body.brand 透传 service.register
- API 测覆盖 POST/PATCH brand 设值/未传 keep/null 清空 + GET q 搜 brand + sort_by=brand"
```

---

## Phase 5：CLI + 导出

### Task 5.1：CLI `asset register --brand`

**Files:**

- Modify: `D:\CONGHAOYANG\Projects\tools\asset-hub\src\asset_hub\cli\asset_cmd.py`
- Modify: `D:\CONGHAOYANG\Projects\tools\asset-hub\tests\cli\test_asset_cmd.py`

- [ ] **Step 1：写 CLI 测试**

```python
def test_register_with_brand_flag(cli_runner, isolated_db_with_type):
    """asset register --brand 应落库。"""
    result = cli_runner.invoke(
        app,
        [
            "asset", "register",
            "--name", "A1",
            "--type-id", str(isolated_db_with_type.id),
            "--brand", "Lenovo",
            "--model", "ThinkPad T14",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.stdout
    import json
    data = json.loads(result.stdout)["data"]
    assert data["brand"] == "Lenovo"
    assert data["model"] == "ThinkPad T14"


def test_list_sort_brand(cli_runner, isolated_db_with_brands):
    """asset list --sort brand 应可用。"""
    result = cli_runner.invoke(
        app, ["asset", "list", "--sort", "brand", "--json"],
    )
    assert result.exit_code == 0
    import json
    items = json.loads(result.stdout)["data"]["items"]
    brands = [a["brand"] for a in items if a["brand"]]
    assert brands == sorted(brands)
```

跑：

```bash
uv run pytest tests/cli/test_asset_cmd.py -v -k brand
```

期望 FAIL。

- [ ] **Step 2：改 `asset register` 命令加 --brand**

`cli/asset_cmd.py` 行 36-41（spec scan §10），在 `model: ...` flag **之前**插入 brand：

```python
@asset_app.command("register")
def asset_register(
    name: Annotated[str, typer.Option(help="资产名称")],
    type_id: Annotated[str, typer.Option("--type-id", help="类型 UUID")],
    serial_number: Annotated[str | None, typer.Option("--sn", help="铭牌编号")] = None,
    brand: Annotated[str | None, typer.Option("--brand", help="品牌")] = None,
    model: Annotated[str | None, typer.Option("--model", help="型号")] = None,
    # ... 其余 flag ...
```

找到函数体内 `service.register(...)` 调用，加 `brand=brand,`。

- [ ] **Step 3：`asset list --sort` help text 加 brand**

grep `--sort` 在 `asset_cmd.py` 的位置：

```bash
grep -n "sort" src/asset_hub/cli/asset_cmd.py
```

找到 `--sort` Option 的 help 字符串（含 `"name"`, `"model"`, `"asset_code"` 等），加入 `"brand"`。

- [ ] **Step 4：跑 CLI test 看 pass**

```bash
uv run pytest tests/cli/test_asset_cmd.py -v -k brand
```

期望 PASS。

### Task 5.2：导出列加品牌

**Files:**

- Modify: `D:\CONGHAOYANG\Projects\tools\asset-hub\src\asset_hub\services\export.py`
- Modify: `D:\CONGHAOYANG\Projects\tools\asset-hub\tests\unit\test_export_service.py`
- Modify: `D:\CONGHAOYANG\Projects\tools\asset-hub\tests\api\test_export_routes.py`

- [ ] **Step 1：写导出测试**

在 `tests/unit/test_export_service.py` 加：

```python
def test_export_csv_header_contains_brand(session, asset_with_brand):
    """CSV header 应含「品牌」，位置在「名称」之后、「型号」之前。"""
    from asset_hub.services.export import ExportService

    svc = ExportService(session)
    content, _filename = svc.render([asset_with_brand], format="csv")
    text = content.decode("utf-8-sig")  # CSV with BOM
    header = text.splitlines()[0]
    columns = header.split(",")
    assert "品牌" in columns
    name_idx = columns.index("名称")
    brand_idx = columns.index("品牌")
    model_idx = columns.index("型号")
    assert name_idx < brand_idx < model_idx


def test_export_csv_row_contains_brand_value(session, asset_with_brand):
    """CSV 数据行 brand 列应有正确值。"""
    from asset_hub.services.export import ExportService

    svc = ExportService(session)
    content, _ = svc.render([asset_with_brand], format="csv")
    text = content.decode("utf-8-sig")
    lines = text.splitlines()
    header = lines[0].split(",")
    brand_idx = header.index("品牌")
    row = lines[1].split(",")
    assert row[brand_idx] == "Lenovo"


def test_export_xlsx_autofilter_range_is_A1_L_n(session, multi_assets):
    """xlsx autofilter 范围应是 A1:L{n}（12 列）。"""
    from asset_hub.services.export import ExportService
    from openpyxl import load_workbook
    from io import BytesIO

    svc = ExportService(session)
    content, _ = svc.render(multi_assets, format="xlsx")
    wb = load_workbook(BytesIO(content))
    ws = wb.active
    expected_n = len(multi_assets) + 1   # +1 for header row
    assert ws.auto_filter.ref == f"A1:L{expected_n}"
```

跑：

```bash
uv run pytest tests/unit/test_export_service.py -v -k brand
```

期望 FAIL。

- [ ] **Step 2：改 `_FIXED_COLUMN_NAMES`**

`services/export.py` 行 63-75：

```python
_FIXED_COLUMN_NAMES: list[str] = [
    "资产编号",
    "名称",
    "品牌",   # CL-1 新增
    "型号",
    "类型",
    "状态",
    "保管人",
    "位置",
    "闲置天数",
    "入账日期",
    "铭牌编号",
    "备注",
]
```

- [ ] **Step 3：改 `_build_rows` 加 brand**

行 93-122：

```python
def _build_rows(
    self,
    assets: list[Asset],
    custom_fields: list[CustomFieldDef],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for a in assets:
        row: dict[str, str] = {
            "资产编号": a.asset_code,
            "名称": a.name,
            "品牌": a.brand or "",   # CL-1 新增（紧贴名称之后、型号之前）
            "型号": a.model or "",
            "类型": a.type_name or "",
            # ... 其余字段不变 ...
        }
        # ... custom_fields 追加不变 ...
        rows.append(row)
    return rows
```

- [ ] **Step 4：找 xlsx autofilter 范围处改 K → L**

grep `A1:K`：

```bash
grep -rn "A1:K" src/asset_hub/services/export.py
```

找到行（应在 `_render_xlsx` 内），改为 `A1:L`（或动态计算的 chr(...) 表达式：如 `chr(ord('A') + len(column_names) - 1)`）。如已是动态计算，则该处无需改。

- [ ] **Step 5：改既有测试中固化的 column 索引 / header startswith / autofilter**

`tests/unit/test_export_service.py` 和 `tests/api/test_export_routes.py` 中可能有：

```bash
grep -rn 'A1:K\|"型号"\|index.*2.*model\|assert.*column.*type' tests/
```

把固化 `"A1:K"` 改 `"A1:L"`；如有 `columns.index("型号")` 之类断言固化值 = 2，改为 3（新插入品牌后型号挪后）。

- [ ] **Step 6：跑 export test 看 pass**

```bash
uv run pytest tests/unit/test_export_service.py tests/api/test_export_routes.py -v
```

期望全 PASS。

- [ ] **Step 7：commit**

```bash
git add src/asset_hub/cli/asset_cmd.py src/asset_hub/services/export.py tests/cli/test_asset_cmd.py tests/unit/test_export_service.py tests/api/test_export_routes.py
git commit -m "feat(cli,export): CLI 加 --brand flag + 导出加品牌列（12 列 A1:L{n}）

CL-1 Phase 5：
- asset register 加 --brand 紧邻 --sn 之后、--model 之前；help='品牌'
- asset list --sort 接受 brand
- _FIXED_COLUMN_NAMES 11 → 12 列，品牌位置紧邻名称之后、型号之前
- _build_rows 注入 a.brand
- xlsx autofilter A1:K{n} → A1:L{n}
- 既有测试 column 索引同步（model 从 index 2 → 3）"
```

---

## Phase 6：前端 + gen:api + 收尾

### Task 6.1：跑 gen:api 同步类型

**Files:** （仅 frontend 生成代码）

- [ ] **Step 1：起后端 dev server**

```bash
uv run uvicorn asset_hub.api.app:app --port 8000 &
# 等 ~2s 起来
```

- [ ] **Step 2：跑 gen:api**

```bash
pnpm --dir frontend gen:api
```

期望 `frontend/src/api/generated/schema.d.ts` 更新，含 `brand: string | null` 在 AssetCreate / AssetUpdate / AssetRead 三处。

- [ ] **Step 3：停后端**

```bash
kill %1
```

- [ ] **Step 4：commit（生成产物单独 commit）**

```bash
git add frontend/src/api/generated/schema.d.ts
git commit -m "chore(api): gen:api 同步 brand 字段到 OpenAPI typed client"
```

### Task 6.2：前端 types + zod + 表单 + 详情 + 列表

**Files:** 较多，按改动面分批做。

**关键约束**：brand 字段所有前端表现形态**必须与现有 model 字段对齐**（命名 / className / placeholder 格式 / disabled prop / cell 样式）。避免自创风格导致 brand 与 model 视觉漂移。

- [ ] **Step 0：grep model 字段在 4 处的现有写法作为对齐基线**

逐处 grep model 字段当前实现，把得到的 className / prop 当 brand 的写法模板：

```bash
# 1. 表单 FormField（含 disabled / placeholder 模式）
grep -B 2 -A 15 'name="model"' frontend/src/features/assets/forms/

# 2. 列表 ColumnDef（含 cell className / accessorKey / sortingFn 模式）
grep -B 2 -A 10 'id: "model"\|accessorKey: "model"' frontend/src/features/assets/list/assets-table.tsx

# 3. 详情 general-fields dt/dd（含 className）
grep -B 2 -A 5 'asset\.model' frontend/src/features/assets/detail/general-fields.tsx
grep -B 2 -A 5 'asset\.model' frontend/src/features/assets/detail/asset-header.tsx

# 4. column-visibility（含 ColumnKey / COLUMN_LABELS / ALL_KEYS / DEFAULT_HIDDEN 是否含 model）
grep -B 1 -A 1 '"model"\|model:' frontend/src/features/assets/list/column-visibility.tsx

# 5. build-asset-schema zod（含 nullable / optional 形态）
grep -B 1 -A 2 'model:' frontend/src/features/assets/forms/build-asset-schema.ts
```

把每处现有的 model 实现作为 brand 实现的模板，**仅替换字面量**（`model` → `brand`，"型号" → "品牌"，placeholder 例子用 `Lenovo / Apple` 而非 `ThinkPad X1 Carbon Gen 9`），不改任何 className / disabled / sortingFn / nullable 等结构性属性。

如发现 model 现有实现本身有 bug（如缺 `disabled={mutation.isPending}`），**不在本 task 修**——记入 followup，本 task 严格对齐 model 现状。

- [ ] **Step 1：`frontend/src/features/assets/types.ts` AssetRow 加 brand**

```bash
grep -n "AssetRow" frontend/src/features/assets/types.ts
```

定位后在 `model: string | null` 前插入 `brand: string | null;`。

- [ ] **Step 2：`build-asset-schema.ts` zod baseShape 加 brand**

```bash
grep -rn "build-asset-schema\|buildAssetSchema" frontend/src/
```

定位文件后，在 zod object 的 model 字段前插入：

```typescript
brand: z.string().nullable().optional(),
```

- [ ] **Step 3：`general-fields-form.tsx` 加 brand FormField**

```bash
grep -rn "general-fields-form" frontend/src/
```

定位文件后，找到 `name` 字段的 FormField **之后**、`model` 字段的 FormField **之前**插入新 FormField（仿 model 字段写法）：

```tsx
<FormField
  control={form.control}
  name="brand"
  render={({ field }) => (
    <FormItem>
      <FormLabel>品牌</FormLabel>
      <FormControl>
        <Input
          {...field}
          value={field.value ?? ""}
          placeholder="如 Lenovo / Apple（可空）"
        />
      </FormControl>
      <FormMessage />
    </FormItem>
  )}
/>
```

- [ ] **Step 4：`asset-create-form.tsx` / `asset-edit-form.tsx` defaultValues / reset / submit payload 加 brand**

```bash
grep -rn "asset-create-form\|asset-edit-form" frontend/src/
```

定位文件后，找到 `defaultValues = { name: ..., model: ... }` 类似结构，在 model 之前加：

```typescript
brand: "",
```

`reset(values)` 和 `submit payload` 处同样加 brand 透传。

- [ ] **Step 5：`asset-header.tsx` 副行加 brand · model**

```bash
grep -rn "asset-header" frontend/src/features/assets/detail/
```

找到 header 副行渲染处（含 `asset.model` 条件渲染）。当前可能是：

```tsx
{asset.model && <span>{asset.model}</span>}
```

改为：

```tsx
{(asset.brand || asset.model) && (
  <span>
    {[asset.brand, asset.model].filter(Boolean).join(" · ")}
  </span>
)}
```

确保「品牌 · 型号」语序（spec 锁定 brand → model）。

- [ ] **Step 6：`general-fields.tsx`（详情页 general-fields 显示）加品牌行**

```bash
grep -rn "general-fields\.tsx\|GeneralFields" frontend/src/features/assets/detail/
```

定位文件后，找到 "名称" 行和 "型号" 行之间。仿 model 行插入"品牌"行：

```tsx
<div>
  <dt className="text-xs text-muted-foreground">品牌</dt>
  <dd>{asset.brand || "—"}</dd>
</div>
```

- [ ] **Step 7：`assets-table.tsx` 加 brand 列**

```bash
grep -n "id: \"name\"\|id: \"model\"" frontend/src/features/assets/list/assets-table.tsx
```

定位 `name` 列和 `model` 列定义。在 `name` 列定义**之后**、`model` 列定义**之前**插入新 brand 列：

```typescript
{
  id: "brand",
  accessorKey: "brand",
  header: COLUMN_LABELS.brand,
  enableSorting: true,
  cell: ({ row }) => (
    <span className="text-sm">{row.original.brand ?? "—"}</span>
  ),
},
```

- [ ] **Step 8：`column-visibility` ColumnKey + COLUMN_LABELS + ALL_KEYS 加 brand**

```bash
grep -rn "COLUMN_LABELS\|ColumnKey" frontend/src/features/assets/list/
```

定位文件后，在 model 之前的 model 位置一一对应加 `brand: "品牌"`。

- [ ] **Step 9：跑 frontend 单测 + 类型检查**

```bash
pnpm --dir frontend lint
pnpm --dir frontend exec tsc -b
pnpm --dir frontend test
```

期望全绿。如类型不一致或 column-visibility 缺 key，按报错修。

- [ ] **Step 10：commit**

```bash
git add frontend/src/
git commit -m "feat(frontend): 前端全栈加 brand 字段（列序 name → brand → model）

CL-1 Phase 6：
- types AssetRow / zod baseShape / general-fields-form / asset-create-form / asset-edit-form
- 详情页 asset-header 副行（品牌 · 型号语序）/ general-fields 加品牌行
- assets-table 加 brand 列（默认显示，可 sort）
- column-visibility ColumnKey / COLUMN_LABELS / ALL_KEYS 加 brand
- DEFAULT_HIDDEN 不变（默认显示，与 model 对齐）"
```

### Task 6.3：删 examples/types 的 brand custom_field

**Files:**

- Modify: `D:\CONGHAOYANG\Projects\tools\asset-hub\examples\types\laptop.json`
- Modify: `D:\CONGHAOYANG\Projects\tools\asset-hub\examples\types\bus_interface.json`
- 检查 `D:\CONGHAOYANG\Projects\tools\asset-hub\examples\types\` 下所有 json 是否含 `key="brand"`

- [ ] **Step 1：列所有 json**

```bash
grep -l '"brand"' examples/types/*.json
```

期望返 laptop.json / bus_interface.json / bus_logger.json 或类似（spec scan §14 列了 4 个 type，其中 3 个含 brand）。

- [ ] **Step 2：逐个 Edit 删 brand 项**

每个 json，找到 `custom_fields` 数组里 `{"key": "brand", ...}` 那一项，删掉（含逗号语法保持合法）。

- [ ] **Step 3：commit**

```bash
git add examples/types/*.json
git commit -m "chore(examples): 从 example types 删冗余 brand custom_field

CL-1 配套：brand 升 Asset 顶层后，example types 不应再定义 key=brand 的 custom_field
（reserved key 校验也会拒绝 future create/update 含 brand custom_field）。"
```

### Task 6.4：SKILL.md 速查表 + Gotcha #8 更新

**Files:**

- Modify: `D:\CONGHAOYANG\Projects\tools\asset-hub\SKILL.md`

- [ ] **Step 1：在 "Asset 顶层公共字段" 速查表加 brand 行**

```bash
grep -n "Asset 顶层公共字段\|顶层字段\|brand\|model" SKILL.md
```

找到现有速查表（含 model / name / sn 等）。在 model 行**之前**插入 brand 行，仿 model 行 schema（label / 是否可空 / 用途）。

- [ ] **Step 2：更新 Gotcha #8（顶层 vs custom 边界）**

找到 SKILL.md 中 Gotcha #8 文字。在描述里追加：

> v2.1+ 起 AssetType custom_fields[].key 已强制校验 reserved 全集 16 项（含 brand / model / serial_number / name / holder / location / notes / acquired_at / asset_code / sn / type / type_name / type_id / status / id / custom_data）；违规 create/update 会直接 ValidationError。**现有 AssetType 含 reserved key 重名 custom_field 不会被破坏**，但建议手动从 type 中删 reserved key 重名 custom_field 避免双输入框 UI 怪状。

- [ ] **Step 3：commit**

```bash
git add SKILL.md
git commit -m "docs(skill): 加 brand 到 Asset 顶层字段速查表 + 更新 Gotcha #8 reserved key 全集

CL-1 配套：
- 顶层字段速查表加 brand 行（位置 name 后、model 前）
- Gotcha #8 列出 reserved 全集 16 项，提示用户手动从 AssetType 删历史 reserved 重名 custom_field"
```

### Task 6.5：草拟 release-notes-v2.1.0

**Files:**

- Create: `D:\CONGHAOYANG\Projects\tools\asset-hub\docs\superpowers\release-notes-v2.1.0.md`（先草稿，最终发版时再 finalize）

- [ ] **Step 1：写草稿框架**

```markdown
# v2.1.0 发版升级指南（草稿）

> ⏳ 状态：CL-1 / CL-2 / CL-3 / CL-4 四 PR 合并后 finalize；当前为 CL-1 落地草稿。

## 概览

v2.1.0 含 4 个独立合并的 polish PR：

| PR | 主题 |
|---|---|
| CL-1 | brand 升 Asset 顶层公共字段 + AssetType reserved key 全集校验 |
| CL-2 | CLI --help-json 暴露 type define 的 valid_field_types |
| CL-3 | e2e workflow playwright browser cache |
| CL-4 | serve doctor 加 check_port_owner 探测外部端口占用 |

## 升级路径

```bash
cp data/asset_hub.db data/asset_hub.db.v2.0.bak
git fetch && git checkout v2.1.0
uv sync && pnpm --dir frontend install
uv run alembic upgrade head
uv run asset-hub serve restart --mode prod
```

## Breaking changes

### Schema（CL-1）

- `Asset` 加 `brand: str | None` 顶层字段（位置紧贴 name 之后、model 之前），加 `ix_assets_brand` 索引
- alembic v4 migration 含数据回填：custom_data.brand（非空字符串，顶层为 null 时）→ 顶层 brand
- custom_data.brand 键保留不动（JSON 弹性零破坏）

### 升级注意（CL-1）

历史 AssetType 含 `key="brand"` 的 custom_field 不会被破坏（read 仍生效），但**强烈建议手动从 AssetType 删除**——否则会出现以下 UI 异常：

**双输入框现象**（清理前）：

```
编辑资产表单：
  名称：[ 工位本-01           ]
  品牌：[ Lenovo              ]   ← 顶层 brand 输入框（CL-1 新增）
  型号：[ ThinkPad T14 Gen 4  ]
  品牌：[ Lenovo              ]   ← custom_data.brand 输入框（历史 custom_field 残留）
```

清理后**收敛为单输入框**：

```
编辑资产表单：
  名称：[ 工位本-01           ]
  品牌：[ Lenovo              ]   ← 仅顶层 brand
  型号：[ ThinkPad T14 Gen 4  ]
```

**清理流程**：

1. 在前端 type 管理页编辑对应 AssetType
2. 删除 `custom_fields` 中 `key=brand` 的项
3. 保存
4. 已录入资产的 `custom_data.brand` 键自动失效（顶层 brand 已是真实数据源，导出 / 搜索 / 聚合 / 详情页显示都从顶层走）；JSON 弹性，键残留不影响

**视觉变化清单**（清理生效）：

- 编辑表单：双"品牌"输入框 → 单顶层"品牌"输入框
- 详情页 general-fields：原"品牌"行（来自 custom_data）+ 新"品牌"行（来自顶层）→ 单"品牌"行
- 详情页 header 副行：原可能含 custom_data.brand 渲染 → 仅顶层 brand 渲染（自然语序 brand · model）
- 列表表格：原可能 brand custom column → 仅顶层 brand 固定列

同理建议清理已有 AssetType 中 `key in {model, serial_number, sn, name, holder, location, notes, acquired_at}` 等 reserved key 重名 custom_field —— CL-1 起 future create/update 这些 key 会被拒绝。

### CLI（CL-1）

- `asset register` 加 `--brand <txt>` flag（位置紧邻 `--sn` 之后、`--model` 之前）
- `asset update --set '{"brand": ...}'` 复用 JSON 模式自然支持
- `asset list --sort brand` 可用

### API（CL-1）

- `POST /api/assets` body 接受可选 `brand`
- `PATCH /api/assets/{id}` body 接受 `brand`（exclude_unset 模式：未传 → keep，传 null → 清空）
- `GET /api/assets` response 含 `brand` 字段
- `GET /api/assets?q=foo` 搜索范围扩到 brand
- `GET /api/assets?sort_by=brand` 可用

### UI（CL-1）

- 列表表格新增 "品牌" 列（位于 "名称" 列右侧、"型号" 列左侧，默认显示）
- 详情页 header 副行：「品牌 · 型号」（任一非空时渲染）
- 详情页 general-fields 加 "品牌" 行
- 编辑表单加 "品牌" 输入（紧邻 name 之后、model 之前）
- CSV/XLSX 导出新增 "品牌" 列（11 列 → 12 列，autofilter A1:L{n}）

### CLI（CL-2）

- `asset-hub type define --help-json` 输出 `--fields` 参数下嵌套 `valid_field_types` 数组（9 值）

### 服务端（CL-4）

- `asset-hub serve doctor` 输出新增 `port_owner:5173` / `port_owner:8000` 检测项
- 外部进程占用端口时 `ok=false` + `fix_hint` 含 OS-specific 指令

### CI（CL-3）

- `.github/workflows/e2e.yml` 加 playwright browser cache，e2e job 冷启动时间从 14m+ 降到 ~2 min

## 回滚

```bash
git checkout v2.0.2
cp data/asset_hub.db.v2.0.bak data/asset_hub.db
uv sync && pnpm --dir frontend install
uv run asset-hub serve restart --mode prod
```

不可回滚的数据：

- v2.1 期间通过顶层 brand 字段写入的数据（custom_data.brand 仍有原值，但回退后只能用 v2.0 的 custom_field 路径）

## SemVer

含 user-visible 新字段（brand） + CLI 新 flag（--brand）+ AssetType 校验新增（拒新建包含 reserved key），但**对存量行为零破坏**。新增功能 + 严格校验 → MINOR → `v2.1.0`。
```

- [ ] **Step 2：commit**

```bash
git add docs/superpowers/release-notes-v2.1.0.md
git commit -m "docs(release): 草拟 v2.1.0 升级指南（CL-1 段，其余 CL-2/3/4 段待 PR 合并后补充）"
```

---

## Phase 7：本地 smoke + PR

### Task 7.1：本地 smoke

- [ ] **Step 1：跑全测 + lint**

```bash
uv run ruff check . && uv run ruff format --check . && uv run pytest
pnpm --dir frontend lint && pnpm --dir frontend exec tsc -b && pnpm --dir frontend test
```

期望全绿。

- [ ] **Step 2：起 serve dev**

```bash
uv run asset-hub serve start --mode dev
```

- [ ] **Step 3：CLI smoke**

```bash
# 创建一个新 type（不含 brand custom_field）
uv run asset-hub type define --name "Test-LP" --prefix "TLP" --json

# 注册资产含 brand
uv run asset-hub asset register --name "Test-A1" --type-id <id> --brand "Lenovo" --model "ThinkPad" --json
# 期望 data.brand = "Lenovo", data.model = "ThinkPad"

# 列表 sort brand
uv run asset-hub asset list --sort brand --json

# 搜 brand
uv run asset-hub asset list --q Lenovo --json

# update brand → null（清空）
uv run asset-hub asset update <id> --set '{"brand": null}' --json
# 期望 data.brand = null

# 反向 reserved key 校验
uv run asset-hub type define --name "Bad" --prefix "BAD" --fields '[{"key":"brand","label":"x","type":"string"}]' --json
# 期望 exit_code=1, error.code=validation, message 提示 reserved
```

- [ ] **Step 4：UI smoke（用 Playwright MCP）**

跑（如有 Playwright MCP 可用）：

- 打开 `http://localhost:5173`
- 列表表格应显示「品牌」列在「名称」和「型号」之间
- 详情页 header 副行应显示「品牌 · 型号」
- 编辑表单应有「品牌」输入框
- 导出 CSV / XLSX 应含「品牌」列

- [ ] **Step 5：导出 smoke**

```bash
uv run asset-hub stats export --format csv --out /tmp/test.csv
head -1 /tmp/test.csv
# 期望表头：资产编号,名称,品牌,型号,类型,...
```

### Task 7.2：开 PR

- [ ] **Step 1：push + 开 PR**

```bash
git push -u origin <branch-name>
gh pr create --title "feat: brand 升 Asset 顶层公共字段 + AssetType reserved key 全集校验" --body "$(cat <<'EOF'
## Summary

闭环 issue #16。沿用 v2.0 PR-3 model 拆列模式：

- Asset 加 brand 顶层字段（紧贴 name 之后、model 之前），alembic v4 含数据回填
- AssetType custom_fields[].key 加 RESERVED_CUSTOM_FIELD_KEYS 全集校验（16 项），顺修 v1 / v2.0 PR-3 漏的校验
- 全栈列序统一 name → brand → model（与日常语序「Lenovo ThinkPad T14」一致）
- 导出 11 列 → 12 列（A1:K{n} → A1:L{n}）
- SKILL.md 速查表 + Gotcha #8 同步

## Test plan

- [x] migration 3 case：upgrade 加列 / 数据回填 / downgrade drop
- [x] AssetType reserved key 全集 16 parametrize PASS + 通过 case PASS
- [x] service register/update_asset/sort/q 5 case
- [x] API POST/PATCH/GET/sort 5 case
- [x] CLI register/list sort 2 case
- [x] 导出 3 case：header 含品牌 + 数据行 + autofilter A1:L{n}
- [x] frontend gen:api 同步、lint、tsc -b、vitest 全绿
- [x] 本地 smoke：CLI 路径 6 步全通过；UI 4 处显示对齐；导出 CSV 表头校对

## 阻塞 M4

合并后才能开 M4 主 PR（前端 general-fields-form / asset-header / general-fields / assets-table / 导出 5 文件改动面冲突）。

spec：docs/superpowers/specs/2026-05-17-m4-batch-plan-design.md CL-1 段。
EOF
)"
```

- [ ] **Step 2：等 CI + merge**

```bash
gh pr checks <pr-number>
# 期望 backend + frontend + e2e 全绿
gh pr merge --squash --delete-branch
```

---

## Self-Review Checklist

- [x] Spec coverage：
  - 数据模型 brand 字段位置（name 后、model 前）✓ Phase 1
  - alembic migration + 数据回填 ✓ Phase 1
  - AssetType reserved key 全集 16 项 ✓ Phase 2
  - service register/update_asset/SortByField/WHITELIST/_SORT_COLUMN_MAP/q OR-chain ✓ Phase 3
  - DTO 三件套 + router 透传 ✓ Phase 4
  - CLI register --brand + list --sort brand ✓ Phase 5
  - 导出 _FIXED_COLUMN_NAMES 含 12 列 + _build_rows + autofilter A1:L{n} ✓ Phase 5
  - 前端 8 处（types/zod/form/header/general-fields/table/column-visibility/forms defaults）✓ Phase 6
  - examples/types 删 brand ✓ Phase 6
  - SKILL.md 速查表 + Gotcha #8 ✓ Phase 6
  - release-notes-v2.1.0 ✓ Phase 6
- [x] 类型一致：brand 在 model / register / update / DTO / CLI flag / sort / 导出列序全部一致
- [x] 无 placeholder：每 task 含完整代码 + 测试 + commit msg
- [x] TDD：每 phase 先测后实现

## 风险

- **alembic 数据回填**：本 plan 用 raw SQL 扫所有 row 回填，万一 custom_data 列含非法 JSON 会被 try/except 跳过——但**不会终止 migration**。如 prod 库有损坏 JSON 会有少量 row 失去回填，可接受
- **`custom_data` 在 SQLAlchemy/SQLite 的实际类型**：可能是 str 或 dict，Task 1.3 已加 isinstance 兜底
- **frontend `column-visibility` ColumnKey 类型推断**：tsc -b 若失败说明 ColumnKey 类型推断 entity 不全，按报错把 brand 也加入 ALL_KEYS / DEFAULT_VISIBLE / COLUMN_LABELS
- **`gen:api` 漏跑**：Task 6.1 显式列为 phase 收尾 task，且单独 commit 让 reviewer 看得见
- **导出测试 column 索引**：第三方测试可能含固化 index 2 = "型号"，新插 brand 后挪到 index 3 —— Task 5.2 Step 5 显式 grep 处理
- **本地 smoke 漏掉 visual**：M4 主 PR 即将动这套视觉，CL-1 只需保证字段渲染存在，不强求精致排版
