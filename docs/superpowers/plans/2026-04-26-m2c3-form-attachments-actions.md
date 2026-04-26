# M2c-3 · 表单 + 附件上传 + 删除 + 状态切换 + 后端字段补齐 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 基于 [`docs/superpowers/specs/2026-04-26-m2c3-form-attachments-actions-design.md`](../specs/2026-04-26-m2c3-form-attachments-actions-design.md)，把 M2c 子里程碑的最后一块（表单 + 上传 + 删除 + §14.5 状态切换 + acquired_at + 简化 asset_code 反向纠偏 + Vitest/RHF/Zod 引入）落地。

**Architecture:** 后端先把字段、状态机、cascade、迁移落到位（前端依赖 schema），再分两路并进——表单组件链（CreateForm / EditForm / DynamicFieldRenderer）+ 详情页扩展（4 状态 CTA 矩阵 / 状态切换 AlertDialog / 附件 add slot）。M2c-2 的两个 Dialog 在最后一段迁 RHF（独立 Task），保证 UX 行为前后一致。

**Tech Stack:** Python 3.12 + SQLModel + Alembic（首次引入）+ FastAPI + Typer · React 19 + Vite + TanStack Router/Query/Table + shadcn/ui + Tailwind 4 + react-hook-form + zod + Vitest + Testing Library + msw

---

## 阶段划分（Task 顺序硬依赖）

```
Phase 0 · 后端字段 + 状态机 + 迁移      (Task 1-9)
   ↓                                       前端表单依赖此 schema
Phase 1 · 前端基础设施 (Vitest/shadcn/RHF) (Task 10-12)
   ↓
Phase 2 · 列表页接通 asset_code            (Task 13-14)
   ↓
Phase 3 · 表单组件层                       (Task 15-20)
   ↓
Phase 4 · 详情页扩展（§14.5 + 删除 + 上传） (Task 21-26)
   ↓
Phase 5 · M2c-2 Dialog 迁 RHF              (Task 27-28)
   ↓
Phase 6 · 测试 + frontend-design 闸门      (Task 29-30)
```

---

## 文件结构（新增 + 修改清单）

参见 spec §4.2。本 plan 在每个 Task 的 "Files" 段中给出该 Task 的具体路径与是新增 / 修改 / 测试。

---

## Phase 0 · 后端字段 + 状态机 + 迁移（Task 1-9）

> **TDD 节奏**：先写 service / state_machine 的 pytest，再写实现；migration 脚本不直接测试（用集成测验证），但 backfill SQL 模板要在 plan 里给出可复制的形式。

### Task 1: 引入 Alembic + 初始化迁移

**Files:**
- Create: `alembic.ini`
- Create: `src/asset_hub/alembic/env.py`
- Create: `src/asset_hub/alembic/script.py.mako`
- Create: `src/asset_hub/alembic/versions/.gitkeep`
- Modify: `pyproject.toml`（加 alembic dep）
- Modify: `src/asset_hub/db.py`（保留 `create_all` 兜底，新部署仍可用；alembic 接管已有 DB 的迁移）

- [ ] **Step 1: 加 alembic 依赖**

```bash
uv add alembic
```

- [ ] **Step 2: 初始化 alembic 目录到 src/asset_hub/alembic（不是项目根 alembic/，便于 import 模型）**

Run:
```bash
uv run alembic init -t async src/asset_hub/alembic
```

> 生成后 `alembic.ini` 在项目根；删除自动生成的 `[loggers]/[handlers]` 等无用块（保留 `[alembic]` + `script_location` 即可）。

- [ ] **Step 3: 改 alembic.ini 让它与项目同步**

`alembic.ini`（替换为以下内容）：

```ini
[alembic]
script_location = src/asset_hub/alembic
prepend_sys_path = src
file_template = %%(year)d%%(month).2d%%(day).2d_%%(hour).2d%%(minute).2d_%%(rev)s_%%(slug)s
sqlalchemy.url = sqlite:///./data/asset_hub.db

[post_write_hooks]
hooks = ruff_format
ruff_format.type = console_scripts
ruff_format.entrypoint = ruff
ruff_format.options = format REVISION_SCRIPT_FILENAME
```

- [ ] **Step 4: 改 env.py 接通 SQLModel metadata + Settings**

`src/asset_hub/alembic/env.py`：

```python
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from asset_hub.config import Settings
# 显式导入所有模型，让 metadata 包含
from asset_hub.models import asset, asset_type, attachment, checkout  # noqa: F401
from sqlmodel import SQLModel

config = context.config

# 用 Settings 覆盖 alembic.ini 里的 sqlalchemy.url
settings = Settings()
config.set_main_option("sqlalchemy.url", settings.db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # SQLite 必需，让 alembic 用 batch_alter_table
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """同步模式：v1 单线程 SQLite 不需要 async；保留同步入口。"""
    from sqlalchemy import create_engine
    connectable = create_engine(config.get_main_option("sqlalchemy.url"), poolclass=pool.NullPool)
    with connectable.connect() as connection:
        do_run_migrations(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 5: 用 alembic stamp 把现有 DB 标记为"已应用初始 schema"**

```bash
# 对已有 v0.5 数据库执行；新部署不需要这一步
uv run alembic revision --autogenerate -m "m1_initial_schema_baseline"
```

> 观察生成的 versions/*.py。该 revision 的 `upgrade()` 应该是空（或仅 placeholder pass），因为 metadata 与 DB 当前 schema 一致——这只是一条 baseline，标记 DB "已经应用了 M1 那一波 SQLModel.metadata.create_all 的 schema"。
> 必要时手动把 `upgrade()`/`downgrade()` 清空为 `pass`。

- [ ] **Step 6: stamp baseline 到现有数据库**

```bash
uv run alembic stamp <baseline_revision_id>
```

- [ ] **Step 7: 改 db.py 保留 create_all 兜底（新部署用），但加注释说明 alembic 接管**

`src/asset_hub/db.py`（修改）：

```python
"""Engine + create_all 兜底。

M2c-3 起引入 alembic 管理已有 DB 的 schema 演进。新部署仍可用 create_all 直接拉起最新 schema；
已有 DB 必须用 `alembic upgrade head` 应用迁移。两条路径产生相同最终 schema。
"""
from sqlalchemy import Engine
from sqlmodel import SQLModel, create_engine

from asset_hub.config import Settings

_engine: Engine | None = None


def get_engine(settings: Settings | None = None) -> Engine:
    global _engine
    if _engine is None:
        if settings is None:
            settings = Settings()
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(settings.db_url)
        SQLModel.metadata.create_all(_engine)
    return _engine


def reset_engine() -> None:
    global _engine
    _engine = None
```

- [ ] **Step 8: 验证 + commit**

```bash
uv run alembic current   # 应显示 baseline_revision_id (head)
uv run pytest             # 现有测试不应被破坏
git add alembic.ini src/asset_hub/alembic/ src/asset_hub/db.py pyproject.toml uv.lock
git commit -m "feat(alembic): 引入 alembic 管理 schema 演进 + baseline stamp"
```

---

### Task 2: AssetType.code_prefix 字段 + DTO + service 校验

**Files:**
- Modify: `src/asset_hub/models/asset_type.py`
- Modify: `src/asset_hub/api/schemas/asset_type.py`
- Modify: `src/asset_hub/services/asset_type.py`
- Test: `tests/unit/test_type_service.py`（扩展）
- Test: `tests/api/test_type_routes.py`（扩展）

- [ ] **Step 1: 写 service 层失败测**

`tests/unit/test_type_service.py`（追加）：

```python
def test_create_type_requires_code_prefix(session):
    svc = TypeService(session)
    with pytest.raises(ValidationError, match="code_prefix"):
        svc.create_type(name="笔记本电脑", code_prefix="")  # 空值

def test_create_type_validates_prefix_format(session):
    svc = TypeService(session)
    with pytest.raises(ValidationError, match="code_prefix.*格式"):
        svc.create_type(name="笔记本电脑", code_prefix="nb")  # 小写
    with pytest.raises(ValidationError, match="code_prefix.*格式"):
        svc.create_type(name="笔记本电脑", code_prefix="N")   # 仅 1 字符
    with pytest.raises(ValidationError, match="code_prefix.*格式"):
        svc.create_type(name="笔记本电脑", code_prefix="LAPTOP")  # 5+ 字符

def test_create_type_normalizes_prefix_to_upper(session):
    svc = TypeService(session)
    t = svc.create_type(name="笔记本电脑", code_prefix="nb")  # 用户输入小写
    assert t.code_prefix == "NB"

def test_create_type_unique_prefix(session):
    svc = TypeService(session)
    svc.create_type(name="笔记本", code_prefix="NB")
    with pytest.raises(DuplicateError, match="code_prefix"):
        svc.create_type(name="笔记本电脑", code_prefix="NB")
```

> 注意：现有 `test_create_type_*` 测试调用 `svc.create_type(name=..., custom_fields=...)` 不带 code_prefix，需要在 conftest 或既有测试里加 `code_prefix="XX"`。本 step 列出新增测，既有测试在 step 4 一并改。

- [ ] **Step 2: 跑测验证失败**

```bash
uv run pytest tests/unit/test_type_service.py -v
```

Expected: 4 个新 case 全部 FAIL（`AssetType` 没有 `code_prefix` 属性）。

- [ ] **Step 3: 加字段 + 校验**

`src/asset_hub/models/asset_type.py`（替换为）：

```python
import uuid
from datetime import UTC, datetime

from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel


class AssetType(SQLModel, table=True):
    __tablename__ = "asset_types"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(unique=True, index=True)
    code_prefix: str = Field(unique=True, index=True)  # 新；^[A-Z]{2,4}$；service 层 enforce 格式
    description: str | None = None
    custom_fields: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
```

`src/asset_hub/api/schemas/asset_type.py`（替换为）：

```python
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CustomFieldDef(BaseModel):
    """v1 schema：name + label + type + required + options + 扩展属性。

    M2c-3 spec D2 定义的完整 12 字段结构（向后兼容旧的 key/label/type/required/options）。
    """
    name: str = Field(alias="key")  # 兼容 M1/M2 旧字段名 "key"
    label: str | None = None
    type: str
    required: bool = False
    default: str | int | float | bool | None = None
    placeholder: str | None = None
    help: str | None = None
    unit: str | None = None
    min: float | None = None
    max: float | None = None
    options: list[str] | None = None
    displayAs: str | None = None  # 'radio' | 'select'

    model_config = ConfigDict(populate_by_name=True)


class TypeCreate(BaseModel):
    name: str
    code_prefix: str  # 新；必填；^[A-Z]{2,4}$ 由 service 校验
    description: str | None = None
    custom_fields: list[CustomFieldDef] = []

    @field_validator("code_prefix", mode="before")
    @classmethod
    def normalize_prefix(cls, v):
        if isinstance(v, str):
            return v.upper().strip()
        return v


class TypeUpdate(BaseModel):
    """注意：code_prefix immutable，update DTO 不暴露此字段（D5）。"""
    name: str | None = None
    description: str | None = None
    custom_fields: list[CustomFieldDef] | None = None


class TypeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    code_prefix: str  # 新
    description: str | None
    custom_fields: list[CustomFieldDef]
    created_at: datetime
    updated_at: datetime
```

`src/asset_hub/services/asset_type.py`（修改 `create_type` 方法）：

```python
import re
import uuid

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from asset_hub.api.schemas.asset_type import CustomFieldDef
from asset_hub.errors import DuplicateError, NotFoundError, ValidationError
from asset_hub.models.asset_type import AssetType
from asset_hub.repositories.asset_type import TypeRepository

_PREFIX_RE = re.compile(r"^[A-Z]{2,4}$")


class TypeService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = TypeRepository(session)

    def create_type(
        self,
        name: str,
        code_prefix: str,
        description: str | None = None,
        custom_fields: list | None = None,
    ) -> AssetType:
        normalized_prefix = (code_prefix or "").upper().strip()
        if not _PREFIX_RE.fullmatch(normalized_prefix):
            raise ValidationError(
                f"code_prefix 格式不合法：'{code_prefix}'，需要 2-4 个大写字母（^[A-Z]{{2,4}}$）"
            )

        fields = custom_fields or []
        try:
            [CustomFieldDef.model_validate(f) for f in fields]
        except Exception as e:
            raise ValidationError(f"custom_fields 结构无效: {e}") from e

        asset_type = AssetType(
            name=name,
            code_prefix=normalized_prefix,
            description=description,
            custom_fields=fields,
        )
        try:
            self.repo.add(asset_type)
            self.session.commit()
        except IntegrityError as e:
            self.session.rollback()
            msg = str(e).lower()
            if "code_prefix" in msg:
                raise DuplicateError(f"code_prefix 已存在: {normalized_prefix}") from None
            raise DuplicateError(f"类型名称已存在: {name}") from None
        self.session.refresh(asset_type)
        return asset_type

    def get_type(self, type_id: uuid.UUID) -> AssetType:
        t = self.repo.get(type_id)
        if t is None:
            raise NotFoundError(f"类型不存在: {type_id}")
        return t

    def list_types(self) -> list[AssetType]:
        return self.repo.list_all()
```

- [ ] **Step 4: 把现有所有测试里的 `create_type(...)` 调用补上 `code_prefix`**

Run:
```bash
grep -rn "create_type(" tests/ src/asset_hub/
```

每个调用点加 `code_prefix="XX"`（按 type 取一个独特前缀，如 NB / TST / EXM）。conftest 的 fixture 也要加。

- [ ] **Step 5: 跑全部测验证（注意此时 DB 模型变了，已有 SQLite 文件需要重置或走 migration——本 Task 还未写 migration，单测用 tmp_path 隔离 DB，pytest 不受影响；CLI 集成测如有也走临时 DB）**

```bash
uv run pytest -v
```

Expected: 所有 PASS。

- [ ] **Step 6: lint + commit**

```bash
uv run ruff check .
git add src/asset_hub/models/asset_type.py src/asset_hub/api/schemas/asset_type.py src/asset_hub/services/asset_type.py tests/
git commit -m "feat(type): AssetType 加 code_prefix 必填字段（^[A-Z]{2,4}$、unique、immutable）+ service 校验"
```

---

### Task 3: Asset 表加 asset_code / acquired_at / current_checkout_id 三字段

**Files:**
- Modify: `src/asset_hub/models/asset.py`
- Modify: `src/asset_hub/api/schemas/asset.py`
- Modify: `src/asset_hub/services/asset.py`（register 自动生成 asset_code）
- Modify: `src/asset_hub/repositories/asset.py`（list_filtered 排序键）
- Test: `tests/unit/test_asset_service.py`（扩展）

- [ ] **Step 1: 写 service.register 自动生成 asset_code 的失败测**

`tests/unit/test_asset_service.py`（追加）：

```python
def test_register_auto_generates_asset_code(session, sample_type_nb):
    """同 type 多次 register，asset_code 按 prefix-001 / prefix-002 递增"""
    svc = AssetService(session)
    a1 = svc.register(name="X1", type_id=sample_type_nb.id, custom_data={})
    a2 = svc.register(name="X1 Carbon", type_id=sample_type_nb.id, custom_data={})
    a3 = svc.register(name="MacBook", type_id=sample_type_nb.id, custom_data={})
    assert a1.asset_code == "NB-001"
    assert a2.asset_code == "NB-002"
    assert a3.asset_code == "NB-003"

def test_register_per_type_seq_independent(session, sample_type_nb, sample_type_pj):
    """不同 type 的 seq 独立"""
    svc = AssetService(session)
    a_nb1 = svc.register(name="X1", type_id=sample_type_nb.id, custom_data={})
    a_pj1 = svc.register(name="投影仪", type_id=sample_type_pj.id, custom_data={})
    a_nb2 = svc.register(name="X1 Carbon", type_id=sample_type_nb.id, custom_data={})
    assert a_nb1.asset_code == "NB-001"
    assert a_pj1.asset_code == "PJ-001"
    assert a_nb2.asset_code == "NB-002"

def test_register_with_acquired_at(session, sample_type_nb):
    from datetime import date
    svc = AssetService(session)
    a = svc.register(
        name="X1", type_id=sample_type_nb.id, custom_data={},
        acquired_at=date(2025, 1, 15),
    )
    assert a.acquired_at == date(2025, 1, 15)

def test_register_acquired_at_optional(session, sample_type_nb):
    svc = AssetService(session)
    a = svc.register(name="X1", type_id=sample_type_nb.id, custom_data={})
    assert a.acquired_at is None
```

并在 conftest 加两个 fixture：

```python
# tests/unit/conftest.py 追加
@pytest.fixture
def sample_type_nb(session):
    from asset_hub.services.asset_type import TypeService
    svc = TypeService(session)
    return svc.create_type(name="笔记本电脑", code_prefix="NB", custom_fields=[])

@pytest.fixture
def sample_type_pj(session):
    from asset_hub.services.asset_type import TypeService
    svc = TypeService(session)
    return svc.create_type(name="投影仪", code_prefix="PJ", custom_fields=[])
```

- [ ] **Step 2: 跑测验证失败**

```bash
uv run pytest tests/unit/test_asset_service.py::test_register_auto_generates_asset_code -v
```

Expected: FAIL（`Asset` 没有 asset_code 属性）。

- [ ] **Step 3: 改 Asset 模型加三字段 + asset_type relationship**

`src/asset_hub/models/asset.py`（替换为）：

```python
import uuid
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from asset_hub.models.asset_type import AssetType


class AssetStatus(StrEnum):
    IN_USE = "IN_USE"
    IDLE = "IDLE"
    MAINTENANCE = "MAINTENANCE"
    RETIRED = "RETIRED"


class Asset(SQLModel, table=True):
    __tablename__ = "assets"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    asset_code: str = Field(unique=True, index=True)  # 新；{prefix}-{seq:03d}，service 层生成
    serial_number: str | None = Field(default=None, unique=True, index=True)
    name: str = Field(index=True)
    type_id: uuid.UUID = Field(foreign_key="asset_types.id", index=True)
    status: AssetStatus = Field(default=AssetStatus.IDLE)
    holder: str | None = None
    location: str | None = None
    notes: str | None = None
    custom_data: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    acquired_at: date | None = Field(default=None)  # 新；业务入账日期
    current_checkout_id: uuid.UUID | None = Field(  # 新；§K 反规范化
        default=None, foreign_key="checkout_records.id", index=True
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # type_name 反规范化（plan 决议：SQLModel Relationship + service 层 selectinload + Asset.type_name property）
    asset_type: "AssetType" = Relationship(sa_relationship_kwargs={"lazy": "joined"})

    @property
    def type_name(self) -> str | None:
        """Pydantic AssetRead 通过 from_attributes 自动读取此 property。

        N+1 防护：service 层用 selectinload；本 property 仅在已 load 的 relationship 上读字段。
        Relationship 的 lazy="joined" 兜底，对单一 asset query 无 N+1 风险。
        """
        return self.asset_type.name if self.asset_type else None
```

> 注意：`lazy="joined"` 让 `Asset.asset_type` 在 query 时自动 JOIN 拉出，单 SELECT 完成；list_assets 走 `select(Asset)` 时也会自动 JOIN，无 N+1。详见 SQLAlchemy `Relationship` lazy 选项文档。

- [ ] **Step 4: 改 service.register 生成 asset_code**

`src/asset_hub/services/asset.py`（修改 register 方法）：

```python
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from asset_hub.errors import DuplicateError, NotFoundError, ValidationError
from asset_hub.models.asset import Asset, AssetStatus
from asset_hub.repositories.asset import AssetRepository
from asset_hub.repositories.asset_type import TypeRepository
from asset_hub.services.validation import validate_custom_data


class _Unset: pass
_UNSET = _Unset()


class AssetService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = AssetRepository(session)
        self.type_repo = TypeRepository(session)

    def register(
        self,
        name: str,
        type_id: uuid.UUID,
        custom_data: dict,
        serial_number: str | None = None,
        holder: str | None = None,
        location: str | None = None,
        notes: str | None = None,
        acquired_at: date | None = None,
    ) -> Asset:
        asset_type = self.type_repo.get(type_id)
        if asset_type is None:
            raise NotFoundError(f"类型不存在: {type_id}")

        validated_data = validate_custom_data(asset_type.custom_fields, custom_data)
        asset_code = self._generate_asset_code(asset_type.code_prefix, type_id)

        asset = Asset(
            asset_code=asset_code,
            name=name,
            type_id=type_id,
            serial_number=serial_number,
            holder=holder,
            location=location,
            notes=notes,
            custom_data=validated_data,
            acquired_at=acquired_at,
        )
        try:
            self.repo.add(asset)
            self.session.commit()
        except IntegrityError as e:
            self.session.rollback()
            msg = str(e).lower()
            if "asset_code" in msg:
                # 极小概率：同 type 极高并发，两个 register 各自 max+1 算到同一值
                raise DuplicateError(f"asset_code 撞车（请重试）: {asset_code}") from None
            raise DuplicateError(f"序列号重复: {serial_number}") from None
        self.session.refresh(asset)
        return asset

    def _generate_asset_code(self, prefix: str, type_id: uuid.UUID) -> str:
        """{prefix}-{per_type_max+1:03d}。

        注意：v1 单用户场景，并发风险近零；如需强一致可在 SELECT MAX 外加 SELECT FOR UPDATE
        或 INSERT 失败重试一次。本里程碑选择最简：失败 → DuplicateError → 调用方重试。
        """
        # 用 SQL MAX 取序号；substr 提取数字部分
        stmt = (
            select(func.max(Asset.asset_code))
            .where(Asset.type_id == type_id)
        )
        max_code = self.session.exec(stmt).first()
        if max_code is None:
            seq = 1
        else:
            # max_code 形如 "NB-007"；取 dash 后数字
            try:
                seq = int(max_code.split("-")[-1]) + 1
            except (ValueError, AttributeError):
                seq = 1
        return f"{prefix}-{seq:03d}"

    def get_asset(self, asset_id: uuid.UUID) -> Asset:
        # 用 selectinload 让 asset_type relationship 一次拉出（双保险，relationship 已 lazy="joined"）
        a = self.repo.get(asset_id)
        if a is None:
            raise NotFoundError(f"资产不存在: {asset_id}")
        return a

    def list_assets(
        self,
        type_id: uuid.UUID | None = None,
        status: AssetStatus | None = None,
        holder: str | None = None,
        q: str | None = None,
    ) -> list[Asset]:
        return self.repo.list_filtered(type_id=type_id, status=status, holder=holder, q=q)

    def update_asset(
        self,
        asset_id: uuid.UUID,
        name: str | None = None,
        serial_number: str | _Unset = _UNSET,
        status: AssetStatus | None = None,
        holder: str | _Unset = _UNSET,
        location: str | _Unset = _UNSET,
        notes: str | _Unset = _UNSET,
        custom_data: dict | _Unset = _UNSET,
        acquired_at: date | None | _Unset = _UNSET,
    ) -> Asset:
        a = self.get_asset(asset_id)
        if name is not None:
            a.name = name
        if not isinstance(serial_number, _Unset):
            a.serial_number = serial_number
        if status is not None:
            from asset_hub.services.state_machine import assert_transition_allowed
            assert_transition_allowed(a.status, status)  # Task 5 引入
            a.status = status
        if not isinstance(holder, _Unset):
            a.holder = holder
        if not isinstance(location, _Unset):
            a.location = location
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

    def delete_asset(self, asset_id: uuid.UUID) -> None:
        # cascade 在 Task 6 接通；本 step 占位仅删 asset
        a = self.get_asset(asset_id)
        self.repo.delete(a)
        self.session.commit()
```

> `update_asset` 引用了 `state_machine.assert_transition_allowed` —— 该模块在 Task 5 创建。本 step 暂时把 `from ...` import 改为函数局部 import（如代码所示），避免顺序耦合。

- [ ] **Step 5: 改 AssetCreate / AssetUpdate / AssetRead DTO**

`src/asset_hub/api/schemas/asset.py`（替换为）：

```python
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from asset_hub.models.asset import AssetStatus


class AssetCreate(BaseModel):
    name: str
    type_id: UUID
    serial_number: str | None = None
    holder: str | None = None
    location: str | None = None
    notes: str | None = None
    custom_data: dict = Field(default_factory=dict)
    acquired_at: date | None = None  # 新

    # 注意：asset_code 不在 Create body 中——系统自动生成


class AssetUpdate(BaseModel):
    """注意：type_id 不暴露——D9 编辑表单禁改 type；asset_code 也不暴露（系统生成、不允许手改）。"""
    name: str | None = None
    serial_number: str | None = None
    status: AssetStatus | None = None
    holder: str | None = None
    location: str | None = None
    notes: str | None = None
    custom_data: dict | None = None
    acquired_at: date | None = None  # 新


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    asset_code: str  # 新
    name: str
    serial_number: str | None
    type_id: UUID
    type_name: str | None  # 新；从 Asset.type_name @property 自动读取
    status: AssetStatus
    holder: str | None
    location: str | None
    notes: str | None
    custom_data: dict
    acquired_at: date | None  # 新
    current_checkout_id: UUID | None  # 新；§K 反规范化
    created_at: datetime
    updated_at: datetime
```

- [ ] **Step 6: 改 repository.list_filtered 加 sort 参数（按 asset_code 排序为 list 默认）**

`src/asset_hub/repositories/asset.py`（替换 `list_filtered` 方法）：

```python
def list_filtered(
    self,
    type_id: uuid.UUID | None = None,
    status: AssetStatus | None = None,
    holder: str | None = None,
    q: str | None = None,
) -> list[Asset]:
    stmt = select(Asset)
    if type_id is not None:
        stmt = stmt.where(Asset.type_id == type_id)
    if status is not None:
        stmt = stmt.where(Asset.status == status)
    if holder is not None:
        stmt = stmt.where(Asset.holder == holder)
    if q is not None:
        stmt = stmt.where(
            Asset.name.contains(q)
            | Asset.serial_number.contains(q)
            | Asset.notes.contains(q)
            | Asset.asset_code.contains(q)  # 新：编号也参与全文搜索
        )
    # 默认按 asset_code 升序——配合前端列表默认 sort
    stmt = stmt.order_by(Asset.asset_code.asc())
    return list(self.session.exec(stmt).all())
```

- [ ] **Step 7: 跑测验证 register / acquired_at 测试 PASS**

```bash
uv run pytest tests/unit/test_asset_service.py -v
```

Expected: 4 个新 case 全 PASS（其余既有测试也应该 PASS——既有的 `register(...)` 调用不带 code_prefix 是因为 type fixture 自带；需在 conftest 检查所有 sample_type fixture 已加 prefix）。

> 此时 `update_asset` 测试可能因 `state_machine` 不存在而 ImportError 失败。Task 5 创建 state_machine 后会修复。如有阻塞，临时把 `update_asset` 中 status 判断行注释掉，Task 5 再恢复。

- [ ] **Step 8: lint + commit**

```bash
uv run ruff check .
git add src/asset_hub/models/asset.py src/asset_hub/api/schemas/asset.py src/asset_hub/services/asset.py src/asset_hub/repositories/asset.py tests/
git commit -m "feat(asset): Asset 加 asset_code/acquired_at/current_checkout_id 三字段 + register 自动生成 asset_code + type_name relationship"
```

---

### Task 4: AssetType ↔ Asset 双向 relationship + AssetRead.type_name 自动填充验证

**Files:**
- Modify: `src/asset_hub/models/asset_type.py`（加 assets relationship 反向声明，可选）
- Test: `tests/unit/test_asset_service.py`（验证 type_name 自动填充）
- Test: `tests/api/test_asset_routes.py`（GET /assets 返回 type_name）

> Task 3 已经在 `Asset` 端定义了 `asset_type: "AssetType" = Relationship(...)` 并加了 `@property type_name`。本 Task 验证 AssetRead DTO 通过 `from_attributes=True` 能正确读出 type_name。

- [ ] **Step 1: 写测试验证 AssetRead 通过 service 取出后 type_name 已填充**

`tests/unit/test_asset_service.py`（追加）：

```python
def test_asset_read_includes_type_name(session, sample_type_nb):
    from asset_hub.api.schemas.asset import AssetRead
    svc = AssetService(session)
    a = svc.register(name="X1", type_id=sample_type_nb.id, custom_data={})
    a_read = AssetRead.model_validate(a)
    assert a_read.type_name == "笔记本电脑"
    assert a_read.asset_code == "NB-001"

def test_list_assets_each_has_type_name(session, sample_type_nb, sample_type_pj):
    from asset_hub.api.schemas.asset import AssetRead
    svc = AssetService(session)
    svc.register(name="X1", type_id=sample_type_nb.id, custom_data={})
    svc.register(name="投影仪", type_id=sample_type_pj.id, custom_data={})

    assets = svc.list_assets()
    reads = [AssetRead.model_validate(a) for a in assets]
    type_names = {r.type_name for r in reads}
    assert type_names == {"笔记本电脑", "投影仪"}
```

- [ ] **Step 2: 跑测验证（应 PASS，因为 Task 3 已经设了 `lazy="joined"`）**

```bash
uv run pytest tests/unit/test_asset_service.py::test_asset_read_includes_type_name -v
uv run pytest tests/unit/test_asset_service.py::test_list_assets_each_has_type_name -v
```

Expected: PASS。如果 list 测有 N+1 警告，可以加 `-W error::sqlalchemy.exc.SAWarning` 严格模式验证（但 lazy="joined" 应当无 N+1）。

- [ ] **Step 3: 在 API 集成测里也加一条**

`tests/api/test_asset_routes.py`（追加）：

```python
def test_get_asset_returns_type_name(client, sample_type_nb_via_api):
    """通过 API POST 创建 asset，GET 详情 → 响应里 type_name 已填"""
    create_resp = client.post("/api/assets", json={
        "name": "X1", "type_id": str(sample_type_nb_via_api), "custom_data": {},
    })
    assert create_resp.status_code == 201
    asset_id = create_resp.json()["id"]

    get_resp = client.get(f"/api/assets/{asset_id}")
    body = get_resp.json()
    assert body["type_name"] == "笔记本电脑"
    assert body["asset_code"].startswith("NB-")
```

API conftest 需加 `sample_type_nb_via_api` fixture：

```python
# tests/api/conftest.py 追加
@pytest.fixture
def sample_type_nb_via_api(client):
    resp = client.post("/api/types", json={
        "name": "笔记本电脑", "code_prefix": "NB", "custom_fields": [],
    })
    assert resp.status_code == 201
    return resp.json()["id"]
```

- [ ] **Step 4: 跑 API 测验证**

```bash
uv run pytest tests/api/test_asset_routes.py -v
```

Expected: PASS。

- [ ] **Step 5: commit**

```bash
git add tests/
git commit -m "test(asset): AssetRead 通过 from_attributes 自动填充 type_name 验证"
```

---

### Task 5: state_machine.py 模块 + 4×4 转换矩阵全测

**Files:**
- Create: `src/asset_hub/services/state_machine.py`
- Test: `tests/unit/test_state_machine.py`（新）

- [ ] **Step 1: 写状态机模块测试**

`tests/unit/test_state_machine.py`（新建）：

```python
"""state_machine 4 状态 × 转换合法性矩阵全测。"""
import pytest

from asset_hub.errors import ValidationError
from asset_hub.models.asset import AssetStatus
from asset_hub.services.state_machine import (
    ALLOWED_TRANSITIONS,
    assert_transition_allowed,
    is_transition_allowed,
)


# 7 条合法转换（spec D14）
LEGAL = [
    (AssetStatus.IDLE, AssetStatus.IN_USE),       # 派发
    (AssetStatus.IN_USE, AssetStatus.IDLE),       # 归还
    (AssetStatus.IDLE, AssetStatus.MAINTENANCE),  # 送修
    (AssetStatus.MAINTENANCE, AssetStatus.IDLE),  # 修好回库
    (AssetStatus.IDLE, AssetStatus.RETIRED),      # 退役
    (AssetStatus.MAINTENANCE, AssetStatus.RETIRED),  # 维修中退役
    (AssetStatus.RETIRED, AssetStatus.IDLE),      # 重新启用
]

# 9 条非法转换（spec D14 列举的不允许）
ILLEGAL = [
    (AssetStatus.IN_USE, AssetStatus.MAINTENANCE),  # 派发中送修
    (AssetStatus.IN_USE, AssetStatus.RETIRED),      # 派发中退役
    (AssetStatus.MAINTENANCE, AssetStatus.IN_USE),  # 维修中派发（不可）
    (AssetStatus.RETIRED, AssetStatus.IN_USE),      # 退役后派发
    (AssetStatus.RETIRED, AssetStatus.MAINTENANCE), # 退役后送修
    (AssetStatus.RETIRED, AssetStatus.RETIRED),     # 自循环
    (AssetStatus.IDLE, AssetStatus.IDLE),
    (AssetStatus.IN_USE, AssetStatus.IN_USE),
    (AssetStatus.MAINTENANCE, AssetStatus.MAINTENANCE),
]


@pytest.mark.parametrize("from_s, to_s", LEGAL)
def test_legal_transitions(from_s, to_s):
    assert is_transition_allowed(from_s, to_s) is True
    assert_transition_allowed(from_s, to_s)  # 不抛


@pytest.mark.parametrize("from_s, to_s", ILLEGAL)
def test_illegal_transitions_raise(from_s, to_s):
    assert is_transition_allowed(from_s, to_s) is False
    with pytest.raises(ValidationError, match=r"不允许从.*转到"):
        assert_transition_allowed(from_s, to_s)


def test_allowed_transitions_matrix_complete():
    """白盒检查：4 个状态都在矩阵中作为 key 存在。"""
    for status in AssetStatus:
        assert status in ALLOWED_TRANSITIONS
```

- [ ] **Step 2: 跑测验证 ImportError**

```bash
uv run pytest tests/unit/test_state_machine.py -v
```

Expected: FAIL with `ModuleNotFoundError: asset_hub.services.state_machine`。

- [ ] **Step 3: 实现状态机模块**

`src/asset_hub/services/state_machine.py`（新建）：

```python
"""资产状态转换合法性矩阵（M2c-3 spec §5.5 / D14）。

简化路径：
- MAINTENANCE 仅从 IDLE 进入
- RETIRED 仅从 IDLE / MAINTENANCE 进入
- IN_USE 状态下要任何状态切换必须先归还
- RETIRED 唯一出口"重新启用"回 IDLE

M3 §14.6 audit 化时，把 assert_transition_allowed 升级为同时写
StateTransitionRecord（不影响 ALLOWED_TRANSITIONS 形态）。
M3 §14.7 状态枚举完善（加 ARCHIVED）时，扩展 ALLOWED_TRANSITIONS dict。
"""
from asset_hub.errors import ValidationError
from asset_hub.models.asset import AssetStatus

ALLOWED_TRANSITIONS: dict[AssetStatus, set[AssetStatus]] = {
    AssetStatus.IDLE: {
        AssetStatus.IN_USE,        # 派发
        AssetStatus.MAINTENANCE,   # 送修
        AssetStatus.RETIRED,       # 退役
    },
    AssetStatus.IN_USE: {
        AssetStatus.IDLE,          # 归还
    },
    AssetStatus.MAINTENANCE: {
        AssetStatus.IDLE,          # 修好回库
        AssetStatus.RETIRED,       # 退役
    },
    AssetStatus.RETIRED: {
        AssetStatus.IDLE,          # 重新启用
    },
}


def is_transition_allowed(from_status: AssetStatus, to_status: AssetStatus) -> bool:
    return to_status in ALLOWED_TRANSITIONS[from_status]


def assert_transition_allowed(from_status: AssetStatus, to_status: AssetStatus) -> None:
    if to_status not in ALLOWED_TRANSITIONS[from_status]:
        raise ValidationError(
            f"不允许从 {from_status.value} 转到 {to_status.value}"
        )
```

- [ ] **Step 4: 跑测验证 PASS**

```bash
uv run pytest tests/unit/test_state_machine.py -v
```

Expected: 16+ case 全 PASS（7 LEGAL + 9 ILLEGAL parametrize + 1 matrix complete）。

- [ ] **Step 5: lint + commit**

```bash
uv run ruff check .
git add src/asset_hub/services/state_machine.py tests/unit/test_state_machine.py
git commit -m "feat(state-machine): 4×4 转换合法性矩阵 + assert_transition_allowed"
```

---

### Task 6: AssetService.change_status + delete_asset cascade + CheckoutService 接 state_machine

**Files:**
- Modify: `src/asset_hub/services/asset.py`（新 `change_status` 方法、cascade delete）
- Modify: `src/asset_hub/services/checkout.py`（接 state_machine、维护 current_checkout_id）
- Modify: `src/asset_hub/services/attachment.py`（暴露 cascade_for_asset 钩子，被 delete_asset 调用）
- Test: `tests/unit/test_asset_service.py`（change_status / delete cascade）
- Test: `tests/unit/test_checkout_service.py`（验证 current_checkout_id 维护）

- [ ] **Step 1: 写 change_status 测试**

`tests/unit/test_asset_service.py`（追加）：

```python
def test_change_status_idle_to_maintenance(session, sample_type_nb):
    svc = AssetService(session)
    a = svc.register(name="X1", type_id=sample_type_nb.id, custom_data={})
    a2 = svc.change_status(a.id, AssetStatus.MAINTENANCE)
    assert a2.status == AssetStatus.MAINTENANCE

def test_change_status_in_use_to_maintenance_raises(session, sample_type_nb):
    """spec D14: IN_USE 状态下要任何状态切换必须先归还"""
    from asset_hub.errors import ValidationError
    svc = AssetService(session)
    a = svc.register(name="X1", type_id=sample_type_nb.id, custom_data={})
    a.status = AssetStatus.IN_USE
    session.commit()
    with pytest.raises(ValidationError, match="IN_USE.*MAINTENANCE"):
        svc.change_status(a.id, AssetStatus.MAINTENANCE)

def test_delete_asset_cascade_checkout_records(session, sample_type_nb):
    """删除 asset 时同事务删 CheckoutRecord"""
    from asset_hub.services.checkout import CheckoutService
    from asset_hub.repositories.checkout import CheckoutRepository
    svc = AssetService(session)
    cs = CheckoutService(session)
    a = svc.register(name="X1", type_id=sample_type_nb.id, custom_data={})
    cs.checkout(asset_id=a.id, holder="张三")
    cs.return_(asset_id=a.id)
    cs.checkout(asset_id=a.id, holder="李四")
    cs.return_(asset_id=a.id)
    repo = CheckoutRepository(session)
    assert len(repo.list_by_asset(a.id)) == 2

    svc.delete_asset(a.id)
    assert len(repo.list_by_asset(a.id)) == 0
```

`tests/unit/test_checkout_service.py`（追加）：

```python
def test_checkout_maintains_current_checkout_id(session, sample_type_nb):
    from asset_hub.services.checkout import CheckoutService
    asvc = AssetService(session)
    csvc = CheckoutService(session)
    a = asvc.register(name="X1", type_id=sample_type_nb.id, custom_data={})

    rec = csvc.checkout(asset_id=a.id, holder="张三")
    a_refresh = asvc.get_asset(a.id)
    assert a_refresh.current_checkout_id == rec.id

    csvc.return_(asset_id=a.id)
    a_refresh = asvc.get_asset(a.id)
    assert a_refresh.current_checkout_id is None
```

- [ ] **Step 2: 跑测验证 FAIL**

```bash
uv run pytest tests/unit/test_asset_service.py::test_change_status_idle_to_maintenance tests/unit/test_checkout_service.py::test_checkout_maintains_current_checkout_id -v
```

Expected: FAIL（`AssetService.change_status` 未实现 + `current_checkout_id` 未维护）。

- [ ] **Step 3: 实现 change_status 与 cascade delete**

`src/asset_hub/services/asset.py`（追加方法）：

```python
def change_status(self, asset_id: uuid.UUID, to_status: AssetStatus) -> Asset:
    """状态切换。state_machine 兜底转换合法性。

    本方法不写 CheckoutRecord——只用于 §14.5 的 4 个轻量状态切换：
    送修 / 修好回库 / 退役 / 重新启用。派发/归还仍走 CheckoutService。
    """
    from asset_hub.services.state_machine import assert_transition_allowed
    a = self.get_asset(asset_id)
    assert_transition_allowed(a.status, to_status)
    a.status = to_status
    a.updated_at = datetime.now(UTC)
    self.session.commit()
    self.session.refresh(a)
    return a

def delete_asset(self, asset_id: uuid.UUID) -> None:
    """硬删除：cascade 清掉 CheckoutRecord + Attachment（FS 文件 + DB 元数据）。

    spec D17：service 层显式 cascade。CheckoutRecord 业务上仅对 asset 有意义；
    Attachment 已和 asset 绑定。

    Note: 派发中（IN_USE）资产删除前端 disable + tooltip "需先归还"；
    本方法不再做 status 检查，由 router 层防护（D16）。前端如绕过，
    走到这里仍会成功——cascade 删除当前 CheckoutRecord 也是合理行为。
    """
    a = self.get_asset(asset_id)

    # 先删附件（外部资源 FS 文件需要）
    from asset_hub.services.attachment import AttachmentService
    from asset_hub.api.deps import _get_storage  # 复用 dep 工厂
    storage = _get_storage()
    att_svc = AttachmentService(self.session, storage)
    for att in att_svc.list(asset_id=asset_id):
        att_svc.delete(att.id)  # 内部已处理 FS 删除 + DB 元数据

    # 再删 CheckoutRecord（仍在同 session 事务）
    from asset_hub.models.checkout import CheckoutRecord
    from sqlalchemy import delete as sa_delete
    self.session.exec(sa_delete(CheckoutRecord).where(CheckoutRecord.asset_id == asset_id))

    # 解绑 current_checkout_id 防外键阻塞
    a.current_checkout_id = None
    self.session.flush()

    self.repo.delete(a)
    self.session.commit()
```

> `_get_storage()` 实际位置在 `api/deps.py`；如未暴露为模块级函数，本 step 在 `api/deps.py` 拆出 module-level helper：

`src/asset_hub/api/deps.py`（修改/确认有此 helper）：

```python
from pathlib import Path
from asset_hub.config import Settings
from asset_hub.storage.local_fs import LocalFSStorage
from asset_hub.storage.base import StorageAdapter

def _get_storage() -> StorageAdapter:
    settings = Settings()
    return LocalFSStorage(Path(settings.attachment_root))
```

- [ ] **Step 4: 改 CheckoutService 接 state_machine + 维护 current_checkout_id**

`src/asset_hub/services/checkout.py`（替换 checkout / return_ 方法）：

```python
import uuid
from datetime import UTC, datetime

from sqlmodel import Session

from asset_hub.errors import StateError
from asset_hub.models.asset import AssetStatus
from asset_hub.models.checkout import CheckoutRecord
from asset_hub.repositories.checkout import CheckoutRepository
from asset_hub.services.asset import AssetService
from asset_hub.services.state_machine import assert_transition_allowed


class CheckoutService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = CheckoutRepository(session)
        self.asset_svc = AssetService(session)

    def checkout(
        self,
        asset_id: uuid.UUID,
        holder: str,
        location: str | None = None,
        note: str | None = None,
    ) -> CheckoutRecord:
        asset = self.asset_svc.get_asset(asset_id)
        # 用 state_machine 替换原有 if 链
        try:
            assert_transition_allowed(asset.status, AssetStatus.IN_USE)
        except Exception as e:
            raise StateError(str(e)) from e

        now = datetime.now(UTC)
        record = CheckoutRecord(
            asset_id=asset_id,
            holder=holder,
            location=location,
            checkout_note=note,
        )
        self.repo.add(record)
        self.session.flush()  # 让 record.id 可用，便于设 current_checkout_id

        asset.status = AssetStatus.IN_USE
        asset.holder = holder
        asset.location = location
        asset.current_checkout_id = record.id  # 新：维护反规范化字段
        asset.updated_at = now

        self.session.commit()
        self.session.refresh(record)
        return record

    def return_(
        self,
        asset_id: uuid.UUID,
        note: str | None = None,
    ) -> CheckoutRecord:
        asset = self.asset_svc.get_asset(asset_id)
        try:
            assert_transition_allowed(asset.status, AssetStatus.IDLE)
        except Exception as e:
            raise StateError(str(e)) from e

        record = self.repo.find_open_by_asset(asset_id)
        if record is None:
            raise StateError(f"资产无未归还记录: {asset_id}")

        now = datetime.now(UTC)
        record.returned_at = now
        record.return_note = note

        asset.status = AssetStatus.IDLE
        asset.holder = None
        asset.location = None
        asset.current_checkout_id = None  # 清空
        asset.updated_at = now

        self.session.commit()
        self.session.refresh(record)
        return record

    def history(self, asset_id: uuid.UUID) -> list[CheckoutRecord]:
        self.asset_svc.get_asset(asset_id)
        return self.repo.list_by_asset(asset_id)
```

- [ ] **Step 5: 跑全部测**

```bash
uv run pytest -v
```

Expected: 全 PASS。如果 `test_checkout_*` 既有测试因 `current_checkout_id` 字段不存在而 crash，回到 Task 3 验证 model 已加；如果 cascade 测因 attachment service 找不到 storage，确认 `api/deps.py` 暴露了 `_get_storage`。

- [ ] **Step 6: lint + commit**

```bash
uv run ruff check .
git add src/asset_hub/services/asset.py src/asset_hub/services/checkout.py src/asset_hub/api/deps.py tests/
git commit -m "feat(state): AssetService.change_status + delete cascade + CheckoutService 接 state_machine + 维护 current_checkout_id"
```

---

### Task 7: API 端点：PATCH 加 status + DELETE cascade + types 端点改

**Files:**
- Modify: `src/asset_hub/api/routers/assets.py`（PATCH body 加 status；DELETE 已有但确保 cascade）
- Modify: `src/asset_hub/api/routers/types.py`（POST body 含 code_prefix；PATCH body 不含）
- Test: `tests/api/test_asset_routes.py`（PATCH status / DELETE cascade）
- Test: `tests/api/test_state_change_endpoint.py`（新；PATCH 状态非法 → 422）

- [ ] **Step 1: 写 PATCH status 测试**

`tests/api/test_state_change_endpoint.py`（新建）：

```python
"""§14.5 PATCH /api/assets/{id} body { status } 端点测试。"""
import pytest


def test_patch_status_idle_to_maintenance(client, sample_type_nb_via_api):
    create = client.post("/api/assets", json={
        "name": "X1", "type_id": sample_type_nb_via_api, "custom_data": {},
    })
    asset_id = create.json()["id"]
    resp = client.patch(f"/api/assets/{asset_id}", json={"status": "MAINTENANCE"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "MAINTENANCE"


def test_patch_status_illegal_transition_returns_422(client, sample_type_nb_via_api):
    """直接 RETIRED → IN_USE 是非法转换"""
    create = client.post("/api/assets", json={
        "name": "X1", "type_id": sample_type_nb_via_api, "custom_data": {},
    })
    asset_id = create.json()["id"]
    client.patch(f"/api/assets/{asset_id}", json={"status": "RETIRED"})
    resp = client.patch(f"/api/assets/{asset_id}", json={"status": "IN_USE"})
    assert resp.status_code == 422
    assert "不允许" in resp.json()["detail"]


def test_patch_status_with_other_fields(client, sample_type_nb_via_api):
    """PATCH 同时改 status + holder 等字段也合法"""
    create = client.post("/api/assets", json={
        "name": "X1", "type_id": sample_type_nb_via_api, "custom_data": {},
    })
    asset_id = create.json()["id"]
    resp = client.patch(f"/api/assets/{asset_id}", json={
        "status": "MAINTENANCE",
        "notes": "屏幕进灰",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "MAINTENANCE"
    assert resp.json()["notes"] == "屏幕进灰"
```

`tests/api/test_asset_routes.py`（追加）：

```python
def test_delete_asset_cascade(client, sample_type_nb_via_api):
    create = client.post("/api/assets", json={
        "name": "X1", "type_id": sample_type_nb_via_api, "custom_data": {},
    })
    asset_id = create.json()["id"]
    client.post(f"/api/assets/{asset_id}/checkout", json={"holder": "张三"})
    client.post(f"/api/assets/{asset_id}/return", json={})

    resp = client.delete(f"/api/assets/{asset_id}")
    assert resp.status_code == 204

    # 二次 DELETE → 404
    resp2 = client.delete(f"/api/assets/{asset_id}")
    assert resp2.status_code == 404


def test_post_asset_with_acquired_at(client, sample_type_nb_via_api):
    resp = client.post("/api/assets", json={
        "name": "X1", "type_id": sample_type_nb_via_api,
        "custom_data": {}, "acquired_at": "2025-01-15",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["acquired_at"] == "2025-01-15"
    assert body["asset_code"].startswith("NB-")
```

- [ ] **Step 2: 跑测验证 FAIL（PATCH body 不接受 status；asset_code/acquired_at 字段不存在等）**

```bash
uv run pytest tests/api/test_state_change_endpoint.py tests/api/test_asset_routes.py::test_delete_asset_cascade tests/api/test_asset_routes.py::test_post_asset_with_acquired_at -v
```

Expected: FAIL（PATCH body schema 不接受 status；既有 router create_asset 不接 acquired_at）。

- [ ] **Step 3: 改 routers/assets.py**

`src/asset_hub/api/routers/assets.py`（替换为）：

```python
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlmodel import Session

from asset_hub.api.deps import get_session
from asset_hub.api.schemas.asset import AssetCreate, AssetRead, AssetUpdate
from asset_hub.models.asset import AssetStatus
from asset_hub.services.asset import AssetService

router = APIRouter()


def _get_svc(session: Annotated[Session, Depends(get_session)]) -> AssetService:
    return AssetService(session)


@router.post("", status_code=201, response_model=AssetRead)
def create_asset(
    body: AssetCreate,
    svc: Annotated[AssetService, Depends(_get_svc)],
):
    return svc.register(
        name=body.name,
        type_id=body.type_id,
        serial_number=body.serial_number,
        holder=body.holder,
        location=body.location,
        notes=body.notes,
        custom_data=body.custom_data,
        acquired_at=body.acquired_at,
    )


@router.get("", response_model=list[AssetRead])
def list_assets(
    svc: Annotated[AssetService, Depends(_get_svc)],
    type_id: uuid.UUID | None = None,
    status: AssetStatus | None = None,
    holder: str | None = None,
    q: str | None = None,
):
    return svc.list_assets(type_id=type_id, status=status, holder=holder, q=q)


@router.get("/{asset_id}", response_model=AssetRead)
def get_asset(
    asset_id: uuid.UUID,
    svc: Annotated[AssetService, Depends(_get_svc)],
):
    return svc.get_asset(asset_id)


@router.patch("/{asset_id}", response_model=AssetRead)
def update_asset(
    asset_id: uuid.UUID,
    body: AssetUpdate,
    svc: Annotated[AssetService, Depends(_get_svc)],
):
    """整合编辑 + 状态切换。

    state 字段由 service 层 state_machine 校验合法性，非法转换抛 ValidationError → 422。
    """
    return svc.update_asset(asset_id, **body.model_dump(exclude_unset=True))


@router.delete("/{asset_id}", status_code=204)
def delete_asset(
    asset_id: uuid.UUID,
    svc: Annotated[AssetService, Depends(_get_svc)],
):
    """删除资产 cascade（CheckoutRecord + Attachment FS+DB）。

    Note: 派发中（IN_USE）资产删除前端按钮 disable（D16）；后端不强制（D17 cascade
    会清当前 CheckoutRecord）。如需后端硬阻拦，未来可加 status 检查。
    """
    svc.delete_asset(asset_id)
    return Response(status_code=204)
```

- [ ] **Step 4: 改 routers/types.py 让 POST 接受 code_prefix、PATCH 不接受**

`src/asset_hub/api/routers/types.py`（替换为）：

```python
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session

from asset_hub.api.deps import get_session
from asset_hub.api.schemas.asset_type import TypeCreate, TypeRead, TypeUpdate
from asset_hub.services.asset_type import TypeService

router = APIRouter()


def _get_svc(session: Annotated[Session, Depends(get_session)]) -> TypeService:
    return TypeService(session)


@router.post("", status_code=201, response_model=TypeRead)
def create_type(body: TypeCreate, svc: Annotated[TypeService, Depends(_get_svc)]):
    return svc.create_type(
        name=body.name,
        code_prefix=body.code_prefix,
        description=body.description,
        custom_fields=[f.model_dump(by_alias=False) for f in body.custom_fields],
    )


@router.get("", response_model=list[TypeRead])
def list_types(svc: Annotated[TypeService, Depends(_get_svc)]):
    return svc.list_types()


@router.get("/{type_id}", response_model=TypeRead)
def get_type(type_id: uuid.UUID, svc: Annotated[TypeService, Depends(_get_svc)]):
    return svc.get_type(type_id)


# PATCH 暂不实现（M2c-3 不做 type 编辑 UI），M2c-4 加。本里程碑保留 endpoint 占位但仅接受
# 不含 code_prefix 的 body——避免有人通过 API 改 prefix。
@router.patch("/{type_id}", response_model=TypeRead)
def update_type(
    type_id: uuid.UUID,
    body: TypeUpdate,
    svc: Annotated[TypeService, Depends(_get_svc)],
):
    """注意：TypeUpdate DTO 不含 code_prefix，从 schema 层 enforce immutable。"""
    raise NotImplementedError("type 编辑 UI 在 M2c-4")  # 等 M2c-4 加 service 方法
```

- [ ] **Step 5: 跑全部 API 测**

```bash
uv run pytest tests/api -v
```

Expected: PASS。

- [ ] **Step 6: lint + commit**

```bash
uv run ruff check .
git add src/asset_hub/api/routers/ tests/api/
git commit -m "feat(api): PATCH /api/assets/{id} 接受 status + DELETE cascade + POST /api/types 含 code_prefix"
```

---

### Task 8: Migration 001 · 字段补齐 + 旧数据回填

**Files:**
- Create: `src/asset_hub/alembic/versions/<timestamp>_001_m2c3_field_backfill.py`
- Create: `scripts/seed_examples.py`（修改/确认包含 type prefix）
- Test: 手工跑 migration on dump dataset（spec §11 DoD）

> 该 migration 要在 Task 1-7 全部完成后写——因为生成的 schema diff 依赖最新 model 状态。

- [ ] **Step 1: autogenerate 迁移文件**

```bash
uv run alembic revision --autogenerate -m "m2c3_field_backfill"
```

> 生成的 versions/<ts>_m2c3_field_backfill.py 会有 `op.add_column(...)` 等。**必须手工审查 + 修改**：autogen 会用 not null + unique 直接加列，但已有数据没值会失败；需改为分步：先 nullable 加 + 回填 + 改 not null。

- [ ] **Step 2: 替换为以下手写 migration**

`src/asset_hub/alembic/versions/<timestamp>_m2c3_field_backfill.py`（替换 `upgrade` 函数）：

```python
"""m2c3_field_backfill

Revision ID: <auto>
Revises: <baseline_revision_id>
Create Date: 2026-04-26

四字段补齐 + 旧数据回填：
1. AssetType.code_prefix（必填、unique；旧数据要手工补 prefix）
2. Asset.asset_code（必填、unique；按 type + created_at 顺序回填）
3. Asset.acquired_at（nullable；不回填）
4. Asset.current_checkout_id（nullable FK；扫描 status=IN_USE 的回填）
"""
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "<auto>"
down_revision = "<baseline_id>"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ===== Step 1: AssetType.code_prefix =====
    # 1a. 加 nullable 列
    with op.batch_alter_table("asset_types", schema=None) as batch:
        batch.add_column(sa.Column("code_prefix", sa.String(), nullable=True))

    # 1b. 旧数据回填——按 name 派生默认 prefix（取首字母大写，1 字符不够则补 X）
    #     ⚠ v1 数据量小（< 10 个 type），强烈建议停服后手工 SQL 直填精确 prefix；
    #        本 migration 仅为 fallback。生产部署时应在跑 alembic upgrade 前手动 INSERT 实际 prefix。
    bind = op.get_bind()
    types = bind.execute(sa.text("SELECT id, name FROM asset_types ORDER BY created_at")).fetchall()
    used_prefixes = set()
    for t in types:
        # 派生：name 第一个字符大写 + "X"，即"笔记本" → "BX"。
        # 实际部署应被人工覆盖前已经 SQL 直填。
        first = t.name[0].upper() if t.name else "X"
        candidate = (first + "X")[:2]  # 至少 2 位
        suffix_idx = 0
        while candidate in used_prefixes:
            suffix_idx += 1
            candidate = f"{first}{suffix_idx}"  # X1 / X2 / ...
        used_prefixes.add(candidate)
        bind.execute(
            sa.text("UPDATE asset_types SET code_prefix = :p WHERE id = :i"),
            {"p": candidate, "i": str(t.id)},
        )

    # 1c. 改为 not null + unique
    with op.batch_alter_table("asset_types", schema=None) as batch:
        batch.alter_column("code_prefix", nullable=False)
        batch.create_unique_constraint("uq_asset_types_code_prefix", ["code_prefix"])
        batch.create_index("ix_asset_types_code_prefix", ["code_prefix"], unique=True)

    # ===== Step 2: Asset.asset_code =====
    # 2a. 加 nullable 列
    with op.batch_alter_table("assets", schema=None) as batch:
        batch.add_column(sa.Column("asset_code", sa.String(), nullable=True))

    # 2b. 按 type_id + created_at 顺序回填 {prefix}-{seq:03d}
    rows = bind.execute(sa.text(
        "SELECT a.id, a.type_id, t.code_prefix "
        "FROM assets a JOIN asset_types t ON t.id = a.type_id "
        "ORDER BY a.type_id, a.created_at"
    )).fetchall()
    seq_by_type: dict[str, int] = {}
    for r in rows:
        type_key = str(r.type_id)
        seq_by_type[type_key] = seq_by_type.get(type_key, 0) + 1
        code = f"{r.code_prefix}-{seq_by_type[type_key]:03d}"
        bind.execute(
            sa.text("UPDATE assets SET asset_code = :c WHERE id = :i"),
            {"c": code, "i": str(r.id)},
        )

    # 2c. 改 not null + unique
    with op.batch_alter_table("assets", schema=None) as batch:
        batch.alter_column("asset_code", nullable=False)
        batch.create_unique_constraint("uq_assets_asset_code", ["asset_code"])
        batch.create_index("ix_assets_asset_code", ["asset_code"], unique=True)

    # ===== Step 3: Asset.acquired_at =====
    with op.batch_alter_table("assets", schema=None) as batch:
        batch.add_column(sa.Column("acquired_at", sa.Date(), nullable=True))
    # 不回填——保持 null，"不知道时不填"

    # ===== Step 4: Asset.current_checkout_id =====
    with op.batch_alter_table("assets", schema=None) as batch:
        batch.add_column(sa.Column(
            "current_checkout_id", sa.Uuid(),
            sa.ForeignKey("checkout_records.id"),
            nullable=True,
        ))
        batch.create_index("ix_assets_current_checkout_id", ["current_checkout_id"])

    # 4b. 扫描 IN_USE 资产，回填最近一条未归还的 CheckoutRecord.id
    in_use = bind.execute(sa.text(
        "SELECT a.id, "
        "  (SELECT cr.id FROM checkout_records cr "
        "   WHERE cr.asset_id = a.id AND cr.returned_at IS NULL "
        "   ORDER BY cr.checked_out_at DESC LIMIT 1) AS rec_id "
        "FROM assets a WHERE a.status = 'IN_USE'"
    )).fetchall()
    for r in in_use:
        if r.rec_id is not None:
            bind.execute(
                sa.text("UPDATE assets SET current_checkout_id = :rid WHERE id = :aid"),
                {"rid": str(r.rec_id), "aid": str(r.id)},
            )


def downgrade() -> None:
    """允许回滚到 baseline（删除新列）。"""
    with op.batch_alter_table("assets", schema=None) as batch:
        batch.drop_index("ix_assets_current_checkout_id")
        batch.drop_column("current_checkout_id")
        batch.drop_column("acquired_at")
        batch.drop_index("ix_assets_asset_code")
        batch.drop_constraint("uq_assets_asset_code", type_="unique")
        batch.drop_column("asset_code")
    with op.batch_alter_table("asset_types", schema=None) as batch:
        batch.drop_index("ix_asset_types_code_prefix")
        batch.drop_constraint("uq_asset_types_code_prefix", type_="unique")
        batch.drop_column("code_prefix")
```

> ⚠ **生产部署手工干预清单**（写入 release-notes-m2c3.md）：
>
> 1. 跑 `alembic upgrade head` 之前，**先停服**
> 2. 把所有 AssetType 用 SQL 显式补 code_prefix（避免 fallback 派生丑陋）：
>
>    ```sql
>    UPDATE asset_types SET code_prefix = 'NB' WHERE name = '笔记本电脑';
>    UPDATE asset_types SET code_prefix = 'PJ' WHERE name = '投影仪';
>    -- ... 每个 type 一行
>    ```
>
> 3. 跑 `alembic upgrade head`（migration 会跳过已有 prefix 的 type）
> 4. 检查 `SELECT name, code_prefix FROM asset_types`、`SELECT name, asset_code FROM assets` 是否符合预期

> Note: 上面的 migration 假设 step 1b 的 UPDATE 是无条件的，会覆盖手工填的值——需改为：

```python
# 修正：改为只回填 NULL 的（已 SQL 直填的不动）
types = bind.execute(sa.text(
    "SELECT id, name FROM asset_types WHERE code_prefix IS NULL ORDER BY created_at"
)).fetchall()
```

- [ ] **Step 3: 跑 migration（dev 数据库）**

```bash
# 备份现有 dev DB
cp data/asset_hub.db data/asset_hub.db.bak

# 在 dev DB 上跑（如果 type 没手工补 prefix，会用派生）
uv run alembic upgrade head

# 检查
uv run python -c "from asset_hub.db import get_engine; from sqlmodel import Session, select; from asset_hub.models.asset_type import AssetType; from asset_hub.models.asset import Asset; e = get_engine(); s = Session(e); print('TYPES:'); [print(t.name, t.code_prefix) for t in s.exec(select(AssetType)).all()]; print('ASSETS:'); [print(a.asset_code, a.name) for a in s.exec(select(Asset)).all()]"
```

Expected: 所有 type 都有 code_prefix；所有 asset 都有 asset_code（按 type 分桶 001 起）。

- [ ] **Step 4: 跑全套测试 + 集成测**

```bash
uv run pytest -v
```

Expected: 全 PASS。

- [ ] **Step 5: 写 release-notes-m2c3.md（部署手工干预清单）**

`docs/superpowers/release-notes-m2c3.md`（新建）：

```markdown
# M2c-3 部署手工干预清单

## 升级前（停服）

1. 备份数据库：`cp data/asset_hub.db data/asset_hub.db.<日期>.bak`
2. 用 SQL 给每个 AssetType 显式补 code_prefix（避免 fallback 派生丑陋）：

   ```sql
   sqlite3 data/asset_hub.db
   UPDATE asset_types SET code_prefix = 'NB' WHERE name = '笔记本电脑';
   UPDATE asset_types SET code_prefix = 'PJ' WHERE name = '投影仪';
   UPDATE asset_types SET code_prefix = 'MS' WHERE name = '鼠标';
   -- 按实际数据补全
   ```

## 升级

```bash
uv run alembic upgrade head
```

## 升级后验证

```bash
uv run python -c "from asset_hub.db import get_engine; ..."  # 见 plan Task 8 step 3
```

## 回滚（如需）

```bash
uv run alembic downgrade -1
cp data/asset_hub.db.<日期>.bak data/asset_hub.db
```
```

- [ ] **Step 6: commit**

```bash
git add src/asset_hub/alembic/versions/ docs/superpowers/release-notes-m2c3.md
git commit -m "feat(migration): 001 · asset_code/code_prefix/acquired_at/current_checkout_id 字段补齐 + 旧数据回填脚本"
```

---

### Task 9: CLI 扩展 · `asset register --acquired-at` / `change-status` / `type define --prefix`

**Files:**
- Modify: `src/asset_hub/cli/asset_cmd.py`（register 加 --acquired-at；新 change-status）
- Modify: `src/asset_hub/cli/type_cmd.py`（define 加 --prefix 必填）
- Test: `tests/cli/test_asset_cli.py`（扩展）
- Test: `tests/cli/test_type_cli.py`（扩展）

> `asset delete` 已有（Task 8 之前的 asset_cmd.py），不需要新增；只需确认 cascade 行为。`asset upload` 已通过 `attachment_cmd.py` 处理，本 plan 不动 attachment CLI。

- [ ] **Step 1: 写 CLI 测试**

`tests/cli/test_asset_cli.py`（追加）：

```python
def test_asset_register_with_acquired_at(runner, isolated_db, sample_type_nb_id):
    result = runner.invoke(app, [
        "asset", "register",
        "--name", "X1",
        "--type-id", str(sample_type_nb_id),
        "--acquired-at", "2025-01-15",
        "--json",
    ])
    assert result.exit_code == 0
    body = json.loads(result.stdout)
    assert body["success"] is True
    assert body["data"]["acquired_at"] == "2025-01-15"
    assert body["data"]["asset_code"].startswith("NB-")


def test_asset_change_status(runner, isolated_db, sample_type_nb_id):
    create = runner.invoke(app, [
        "asset", "register",
        "--name", "X1", "--type-id", str(sample_type_nb_id),
        "--json",
    ])
    asset_id = json.loads(create.stdout)["data"]["id"]

    resp = runner.invoke(app, [
        "asset", "change-status", asset_id,
        "--to", "MAINTENANCE",
        "--json",
    ])
    assert resp.exit_code == 0
    assert json.loads(resp.stdout)["data"]["status"] == "MAINTENANCE"


def test_asset_change_status_illegal_returns_exit_1(runner, isolated_db, sample_type_nb_id):
    create = runner.invoke(app, [
        "asset", "register",
        "--name", "X1", "--type-id", str(sample_type_nb_id),
        "--json",
    ])
    asset_id = json.loads(create.stdout)["data"]["id"]
    runner.invoke(app, ["asset", "change-status", asset_id, "--to", "RETIRED", "--json"])
    resp = runner.invoke(app, ["asset", "change-status", asset_id, "--to", "IN_USE", "--json"])
    assert resp.exit_code == 1  # ValidationError → exit_code 1
    assert json.loads(resp.stdout)["success"] is False
    assert "不允许" in json.loads(resp.stdout)["error"]
```

`tests/cli/test_type_cli.py`（追加）：

```python
def test_type_define_requires_prefix(runner, isolated_db):
    resp = runner.invoke(app, [
        "type", "define",
        "--name", "笔记本电脑",
        "--json",
    ])
    # 缺 --prefix → exit_code=2（用法错）
    assert resp.exit_code == 2

def test_type_define_with_prefix(runner, isolated_db):
    resp = runner.invoke(app, [
        "type", "define",
        "--name", "笔记本电脑",
        "--prefix", "NB",
        "--json",
    ])
    assert resp.exit_code == 0
    body = json.loads(resp.stdout)
    assert body["data"]["code_prefix"] == "NB"

def test_type_define_invalid_prefix(runner, isolated_db):
    resp = runner.invoke(app, [
        "type", "define",
        "--name", "笔记本电脑",
        "--prefix", "nb",  # 小写 - service 会归一化为 "NB"
        "--json",
    ])
    assert resp.exit_code == 0
    assert json.loads(resp.stdout)["data"]["code_prefix"] == "NB"

    resp = runner.invoke(app, [
        "type", "define",
        "--name", "另一个",
        "--prefix", "x",  # 仅 1 字符
        "--json",
    ])
    assert resp.exit_code == 1  # ValidationError
    assert "code_prefix" in json.loads(resp.stdout)["error"]
```

- [ ] **Step 2: 跑测验证 FAIL**

```bash
uv run pytest tests/cli/ -v
```

Expected: 多个 FAIL（CLI 还没实现新参数）。

- [ ] **Step 3: 改 asset_cmd.py**

`src/asset_hub/cli/asset_cmd.py`（修改）—— 给 `asset_register` 加 `--acquired-at`；新增 `asset_change_status`：

```python
# 顶部加 import
from datetime import date
from asset_hub.models.asset import AssetStatus

# asset_register 修改签名 + body 传 acquired_at
@asset_app.command("register")
def asset_register(
    name: Annotated[str, typer.Option(help="资产名称")],
    type_id: Annotated[str, typer.Option("--type-id", help="类型 UUID")],
    serial_number: Annotated[str | None, typer.Option("--sn", help="铭牌编号")] = None,
    holder: Annotated[str | None, typer.Option(help="保管人")] = None,
    location: Annotated[str | None, typer.Option(help="位置")] = None,
    notes: Annotated[str | None, typer.Option(help="备注")] = None,
    custom: Annotated[str | None, typer.Option(help="自定义字段 JSON")] = None,
    acquired_at: Annotated[str | None, typer.Option("--acquired-at", help="入账日期 YYYY-MM-DD")] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """登记新资产。"""
    uid = parse_uuid(type_id, json_output)
    custom_data = json.loads(custom) if custom else {}
    parsed_date = date.fromisoformat(acquired_at) if acquired_at else None

    with cli_session() as session, handle_domain_errors(json_output):
        svc = AssetService(session)
        a = svc.register(
            name=name, type_id=uid,
            serial_number=serial_number,
            holder=holder, location=location, notes=notes,
            custom_data=custom_data,
            acquired_at=parsed_date,
        )
    print_result(to_json_dict(AssetRead, a), json_output)


# 新命令
@asset_app.command("change-status")
def asset_change_status(
    asset_id: Annotated[str, typer.Argument(help="资产 UUID")],
    to: Annotated[str, typer.Option("--to", help="目标状态：IDLE/IN_USE/MAINTENANCE/RETIRED")],
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """切换资产状态（送修/修好回库/退役/重新启用）。

    派发/归还请用 `asset checkout` / `asset return`——它们会写流转记录；
    本命令仅适合 §14.5 的 4 个轻量切换。
    """
    uid = parse_uuid(asset_id, json_output)
    parsed_status = parse_enum(AssetStatus, to, json_output)

    with cli_session() as session, handle_domain_errors(json_output):
        svc = AssetService(session)
        a = svc.change_status(uid, parsed_status)
    print_result(to_json_dict(AssetRead, a), json_output)
```

- [ ] **Step 4: 改 type_cmd.py**

`src/asset_hub/cli/type_cmd.py`（修改 `type_define`）：

```python
@type_app.command("define")
def type_define(
    name: Annotated[str | None, typer.Option(help="类型名称")] = None,
    prefix: Annotated[str | None, typer.Option("--prefix", help="编号前缀（2-4 大写字母，如 NB）")] = None,
    description: Annotated[str | None, typer.Option(help="类型描述")] = None,
    fields: Annotated[str | None, typer.Option(help="自定义字段 JSON 数组")] = None,
    from_file: Annotated[Path | None, typer.Option("--from", help="JSON schema 文件路径")] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """定义新的资产类型。"""
    if from_file is not None:
        schema = json.loads(from_file.read_text(encoding="utf-8"))
        name = schema["name"]
        prefix = schema.get("code_prefix") or schema.get("prefix")
        description = schema.get("description")
        custom_fields = schema.get("custom_fields", [])
    elif name is not None:
        custom_fields = json.loads(fields) if fields else []
    else:
        print_error("必须提供 --name 或 --from", json_output, exit_code=2)

    if not prefix:
        print_error("必须提供 --prefix（2-4 大写字母）", json_output, exit_code=2)

    with cli_session() as session, handle_domain_errors(json_output):
        svc = TypeService(session)
        t = svc.create_type(
            name=name, code_prefix=prefix,
            description=description, custom_fields=custom_fields,
        )
    print_result(to_json_dict(TypeRead, t), json_output)
```

- [ ] **Step 5: 跑全部 CLI 测**

```bash
uv run pytest tests/cli -v
```

Expected: 全 PASS。注意 conftest 里 `sample_type_nb_id` fixture 也要走 `--prefix NB` 创建。

- [ ] **Step 6: lint + commit**

```bash
uv run ruff check .
git add src/asset_hub/cli/ tests/cli/
git commit -m "feat(cli): asset register --acquired-at + asset change-status + type define --prefix（必填）"
```

---

## ✅ Phase 0 完成判定

跑一遍：
```bash
uv run pytest -v
uv run ruff check .
uv run alembic current  # 显示 m2c3_field_backfill (head)
```

Expected: 全绿。后端字段补齐 + state_machine + cascade + Alembic + CLI 全部就位。前端可以开始消费。

---

## Phase 1 · 前端基础设施（Task 10-12）

### Task 10: 引入 Vitest + Testing Library + msw + 配置

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/vitest.config.ts`
- Create: `frontend/tests/setup.ts`
- Create: `frontend/tests/msw-handlers.ts`
- Create: `frontend/tests/unit/.gitkeep`
- Create: `frontend/tests/hooks/.gitkeep`

- [ ] **Step 1: 装依赖**

```bash
pnpm --dir frontend add -D vitest @vitest/ui @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom msw
```

- [ ] **Step 2: 加 npm script**

`frontend/package.json` 的 `scripts` 段加：

```json
"test": "vitest run",
"test:watch": "vitest",
"test:ui": "vitest --ui"
```

- [ ] **Step 3: 写 vitest config**

`frontend/vitest.config.ts`（新建）：

```ts
/// <reference types="vitest" />
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'node:path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/setup.ts'],
    css: false,
    include: ['tests/**/*.{test,spec}.{ts,tsx}'],
  },
});
```

- [ ] **Step 4: 写 test setup**

`frontend/tests/setup.ts`（新建）：

```ts
import '@testing-library/jest-dom';
import { afterAll, afterEach, beforeAll } from 'vitest';
import { setupServer } from 'msw/node';
import { handlers } from './msw-handlers';

const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// 暴露给单测直接覆盖 handler
(globalThis as any).__mswServer = server;
```

- [ ] **Step 5: 写 msw handlers 骨架（hook 测试用）**

`frontend/tests/msw-handlers.ts`（新建）：

```ts
import { http, HttpResponse } from 'msw';

/**
 * 默认空 handlers——hook 测试用 server.use(...) 覆盖具体端点。
 */
export const handlers = [
  // 占位：默认捕获，让单测显式 stub
  http.all('*', () => HttpResponse.json({ detail: 'unhandled (override in test)' }, { status: 501 })),
];
```

- [ ] **Step 6: 写一个最小烟测验证基础设施**

`frontend/tests/unit/smoke.test.ts`（新建）：

```ts
import { describe, expect, it } from 'vitest';

describe('vitest smoke', () => {
  it('should run', () => {
    expect(1 + 1).toBe(2);
  });
});
```

- [ ] **Step 7: 跑测验证 PASS**

```bash
pnpm --dir frontend test
```

Expected: 1 passed。

- [ ] **Step 8: commit**

```bash
git add frontend/package.json frontend/pnpm-lock.yaml frontend/vitest.config.ts frontend/tests/
git commit -m "feat(test): 引入 Vitest + Testing Library + msw（首次）+ 烟测验证基础设施"
```

---

### Task 11: shadcn 加 Form / Input(已有) / Textarea(已有) / Checkbox / RadioGroup / Select / Popover / Calendar / Command(Combobox)

**Files:**
- Modify (via shadcn cli): `frontend/src/components/ui/form.tsx`
- Modify (via shadcn cli): `frontend/src/components/ui/checkbox.tsx`
- Modify (via shadcn cli): `frontend/src/components/ui/radio-group.tsx`
- Modify (via shadcn cli): `frontend/src/components/ui/select.tsx`
- Modify (via shadcn cli): `frontend/src/components/ui/popover.tsx`
- Modify (via shadcn cli): `frontend/src/components/ui/calendar.tsx`
- Modify (via shadcn cli): `frontend/src/components/ui/command.tsx`

> 注意：`input.tsx` / `textarea.tsx` / `dialog.tsx` / `alert-dialog.tsx` / `dropdown-menu.tsx` 已在 M2c-1/M2c-2 引入。

- [ ] **Step 1: shadcn add（一次性安装本里程碑要用到的所有组件）**

```bash
cd frontend
pnpm dlx shadcn@latest add form checkbox radio-group select popover calendar command
```

> calendar 依赖 `react-day-picker`；command 依赖 `cmdk`。`pnpm dlx` 会自动装。

- [ ] **Step 2: 移除每个新组件文件首行的 `"use client"`（Next 残留，与 Vite 项目无关）**

```bash
grep -l '^"use client"' frontend/src/components/ui/*.tsx
# 对每个命中的文件用 sed 或编辑器删首行
```

或单条命令（Unix shell）：

```bash
sed -i '' '/^"use client"$/d' frontend/src/components/ui/form.tsx frontend/src/components/ui/checkbox.tsx frontend/src/components/ui/radio-group.tsx frontend/src/components/ui/select.tsx frontend/src/components/ui/popover.tsx frontend/src/components/ui/calendar.tsx frontend/src/components/ui/command.tsx
```

- [ ] **Step 3: variant 审查（§3.5.7 红线）**

每个组件检查清单：

| 组件 | 检查 | 期望 |
| --- | --- | --- |
| `form.tsx` | 仅 RHF 上下文胶水，无视觉 | OK |
| `checkbox.tsx` | data-[state=checked] 颜色 | 用 `bg-primary` / `text-primary-foreground`（不是硬编码蓝） |
| `radio-group.tsx` | RadioGroupItem 的 indicator | 用 `bg-primary` |
| `select.tsx` | SelectContent 背景 + SelectItem hover | `bg-popover` / `bg-accent`（自适应主题） |
| `popover.tsx` | PopoverContent 背景 | `bg-popover`（不要 `bg-white`） |
| `calendar.tsx` | day_selected 颜色 | 用 `bg-primary` token |
| `command.tsx` | CommandInput 边框 + CommandItem hover | 跟 token |

逐个文件 grep `bg-(white|black|gray)` / `text-(white|black|gray)` 等硬编码：

```bash
grep -nE 'bg-(white|black|gray-)|text-(white|black|gray-)|border-(white|black|gray-)' frontend/src/components/ui/{form,checkbox,radio-group,select,popover,calendar,command}.tsx
```

发现硬编码 → 替换成 token。

- [ ] **Step 4: 中文 locale for Calendar**

`frontend/src/components/ui/calendar.tsx`（顶部加 import；DayPicker props 加 `locale={zhCN}`）：

```tsx
import { zhCN } from 'date-fns/locale';

// 在 DayPicker 组件用法处加 props：
<DayPicker locale={zhCN} ... />
```

- [ ] **Step 5: 跑 build 验证 import 链路**

```bash
pnpm --dir frontend build
```

Expected: 通过。如有 lib/utils.ts 缺失（shadcn add 自动生成）则补上。

- [ ] **Step 6: commit**

```bash
git add frontend/src/components/ui/ frontend/package.json frontend/pnpm-lock.yaml
git commit -m "feat(shadcn): 加 form/checkbox/radio-group/select/popover/calendar/command + variant 审查 + 移除 Next 残留 + Calendar zhCN"
```

---

### Task 12: 引入 react-hook-form + @hookform/resolvers

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: 装依赖**

```bash
pnpm --dir frontend add react-hook-form @hookform/resolvers
```

- [ ] **Step 2: 跑 build 验证 dependency 安装正确**

```bash
pnpm --dir frontend build
```

Expected: PASS。

- [ ] **Step 3: commit**

```bash
git add frontend/package.json frontend/pnpm-lock.yaml
git commit -m "feat(deps): 引入 react-hook-form + @hookform/resolvers（M2c-3 表单基础）"
```

---

## ✅ Phase 1 完成判定

```bash
pnpm --dir frontend build && pnpm --dir frontend lint && pnpm --dir frontend test
```

Expected: 全绿；smoke.test 跑通。

---

## Phase 2 · 列表页接通 asset_code（Task 13-14）

### Task 13: openapi 重新生成 + AssetsTable 列改造

**Files:**
- Run: `pnpm --dir frontend gen:api`
- Modify: `frontend/src/features/assets/list/assets-table.tsx`
- Modify: `frontend/src/features/assets/list/column-visibility.tsx`
- Modify: `frontend/src/features/assets/list/search-schema.ts`
- Modify: `frontend/src/routes/index.tsx`（去掉客户端 join，因为 type_name 后端给）

- [ ] **Step 1: 后端 dev server 起来 + 重新生成前端类型**

```bash
# 后端先启起来
uv run uvicorn asset_hub.api.app:app --reload &

# 等几秒后再生
sleep 3
pnpm --dir frontend gen:api
```

> 重新生成的 `frontend/src/api/generated/schema.ts` 会包含 `asset_code` / `acquired_at` / `current_checkout_id` / `type_name` / `code_prefix` 字段。

- [ ] **Step 2: 改 column-visibility.tsx**

`frontend/src/features/assets/list/column-visibility.tsx`（替换为）：

```tsx
import { useEffect, useState } from "react";
import { Settings2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export type ColumnKey =
  | "asset_code"
  | "name"
  | "serial_number"
  | "type"
  | "status"
  | "holder"
  | "location"
  | "updated_at"
  | "acquired_at";

export const COLUMN_LABELS: Record<ColumnKey, string> = {
  asset_code: "编号",
  name: "名称",
  serial_number: "SN",
  type: "类型",
  status: "状态",
  holder: "持有人",
  location: "位置",
  updated_at: "更新时间",
  acquired_at: "入账日期",
};

const STORAGE_KEY = "asset-hub.list.columns.v2"; // bump version 因为 keys 变了
const ALL_KEYS: ColumnKey[] = [
  "asset_code", "name", "serial_number", "type", "status",
  "holder", "location", "updated_at", "acquired_at",
];

const DEFAULT_HIDDEN: Set<ColumnKey> = new Set(["acquired_at"]);

export function useColumnVisibility() {
  const [visible, setVisible] = useState<Record<ColumnKey, boolean>>(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as Partial<Record<ColumnKey, boolean>>;
        return Object.fromEntries(
          ALL_KEYS.map((k) => [k, parsed[k] !== undefined
            ? parsed[k]
            : !DEFAULT_HIDDEN.has(k)]),
        ) as Record<ColumnKey, boolean>;
      }
    } catch { /* fall through */ }
    return Object.fromEntries(
      ALL_KEYS.map((k) => [k, !DEFAULT_HIDDEN.has(k)])
    ) as Record<ColumnKey, boolean>;
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(visible));
  }, [visible]);

  const toggle = (key: ColumnKey) =>
    setVisible((v) => ({ ...v, [key]: !v[key] }));

  return { visible, toggle };
}

interface ColumnVisibilityMenuProps {
  visible: Record<ColumnKey, boolean>;
  onToggle: (key: ColumnKey) => void;
}

export function ColumnVisibilityMenu({ visible, onToggle }: ColumnVisibilityMenuProps) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" aria-label="列显隐">
          <Settings2 className="mr-2 h-4 w-4" />
          <span>列显隐</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuLabel>显示列</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {ALL_KEYS.map((key) => (
          <DropdownMenuCheckboxItem
            key={key}
            checked={visible[key]}
            onCheckedChange={() => onToggle(key)}
            onSelect={(e) => e.preventDefault()}
          >
            {COLUMN_LABELS[key]}
          </DropdownMenuCheckboxItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
```

- [ ] **Step 3: 改 search-schema.ts**

`frontend/src/features/assets/list/search-schema.ts`：

```ts
import { z } from "zod";

export const ASSET_STATUS_VALUES = ["IN_USE", "IDLE", "MAINTENANCE", "RETIRED"] as const;

export const assetsSearchSchema = z.object({
  type: z.string().uuid().optional(),
  status: z.enum(ASSET_STATUS_VALUES).optional(),
  holder: z.string().optional(),
  q: z.string().optional(),
  sort: z.string().optional().default("asset_code"),  // 改：默认 asset_code 升序
  page: z.coerce.number().int().min(1).default(1),
  pageSize: z.coerce.number().int().min(10).max(200).default(50),
});

export type AssetsSearch = z.infer<typeof assetsSearchSchema>;
```

- [ ] **Step 4: 改 assets-table.tsx**

`frontend/src/features/assets/list/assets-table.tsx`（替换 `AssetRow` interface 和 columns 定义）：

```tsx
// AssetRow interface 改为：
export interface AssetRow {
  id: string;
  asset_code: string;
  serial_number?: string | null;
  name: string;
  type_id?: string | null;
  type_name?: string | null;
  status: AssetStatus;
  holder?: string | null;
  location?: string | null;
  updated_at: string;
  acquired_at?: string | null;
}

// columns 定义改为（替换 useMemo 内）：
const columns = useMemo<ColumnDef<AssetRow>[]>(
  () => [
    {
      id: "asset_code",
      accessorKey: "asset_code",
      header: COLUMN_LABELS.asset_code,
      cell: ({ row }) => (
        <span className="font-code text-xs">{row.original.asset_code}</span>
      ),
    },
    {
      id: "name",
      accessorKey: "name",
      header: COLUMN_LABELS.name,
      cell: ({ row }) => (
        <span className="font-medium">{row.original.name}</span>
      ),
    },
    {
      id: "serial_number",
      accessorKey: "serial_number",
      header: COLUMN_LABELS.serial_number,
      cell: ({ row }) =>
        row.original.serial_number ? (
          <span className="font-code text-xs">{row.original.serial_number}</span>
        ) : (
          <span className="text-muted-foreground">—</span>
        ),
    },
    {
      id: "type",
      accessorFn: (r) => r.type_name ?? "",
      header: COLUMN_LABELS.type,
      enableSorting: false,
      cell: ({ row }) => (
        <span className="text-sm text-muted-foreground">
          {row.original.type_name ?? "—"}
        </span>
      ),
    },
    {
      id: "status",
      accessorKey: "status",
      header: COLUMN_LABELS.status,
      enableSorting: false,
      cell: ({ row }) => <StatusBadge status={row.original.status} />,
    },
    {
      id: "holder",
      accessorKey: "holder",
      header: COLUMN_LABELS.holder,
      cell: ({ row }) => row.original.holder ?? "—",
    },
    {
      id: "location",
      accessorKey: "location",
      header: COLUMN_LABELS.location,
      cell: ({ row }) => row.original.location ?? "—",
    },
    {
      id: "updated_at",
      accessorKey: "updated_at",
      header: COLUMN_LABELS.updated_at,
      cell: ({ row }) => formatDateTime(row.original.updated_at),
    },
    {
      id: "acquired_at",
      accessorKey: "acquired_at",
      header: COLUMN_LABELS.acquired_at,
      cell: ({ row }) =>
        row.original.acquired_at ? (
          <span className="font-code text-xs">{row.original.acquired_at}</span>
        ) : (
          <span className="text-muted-foreground">—</span>
        ),
    },
    {
      id: "actions",
      header: "",
      enableSorting: false,
      cell: ({ row }) => (
        <RowActions row={row.original} onCheckout={onCheckout} onReturn={onReturn} onDelete={onDelete} />
      ),
    },
  ],
  [onCheckout, onReturn, onDelete],  // typeNameById 不再需要——type_name 由后端提供
);
```

> `RowActions` 签名要加 `onDelete: (row) => void` —— Task 22 接通 DeleteAssetAlert。本 step 先把 prop 传到位，菜单项保留 disabled，Task 22 解开。

`AssetsTableProps` 加：

```tsx
interface AssetsTableProps {
  rows: AssetRow[];
  search: AssetsSearch;
  visible: Record<ColumnKey, boolean>;
  bodyKey: string;
  onCheckout: (row: AssetRow) => void;
  onReturn: (row: AssetRow) => void;
  onDelete: (row: AssetRow) => void;  // 新
}
```

`RowActions` 修改：

```tsx
function RowActions({
  row,
  onCheckout,
  onReturn,
  onDelete,
}: {
  row: AssetRow;
  onCheckout: (row: AssetRow) => void;
  onReturn: (row: AssetRow) => void;
  onDelete: (row: AssetRow) => void;
}) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" aria-label="更多操作" data-asset-id={row.id}>
          <MoreHorizontal className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem asChild>
          <Link to="/assets/$id/edit" params={{ id: row.id }}>编辑</Link>
        </DropdownMenuItem>
        <DropdownMenuItem
          onSelect={() => onCheckout(row)}
          disabled={row.status !== "IDLE"}
        >
          {CHECKOUT_VERB}
        </DropdownMenuItem>
        <DropdownMenuItem
          onSelect={() => onReturn(row)}
          disabled={row.status !== "IN_USE"}
        >
          {RETURN_VERB}
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onSelect={() => onDelete(row)}
          disabled={row.status === "IN_USE"}
          className="text-destructive focus:text-destructive"
        >
          删除…
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
```

> 顶部需补 `import { Link } from "@tanstack/react-router"` 和 `import { DropdownMenuSeparator } from "@/components/ui/dropdown-menu"`。

- [ ] **Step 5: 改 routes/index.tsx 去掉客户端 type_name join**

`frontend/src/routes/index.tsx` 中 AssetsTable 的 `typeNameById` prop 删除（type_name 来自后端）。同时把 onCheckout / onReturn / onDelete 接通到 Dialog state（onDelete 暂时空函数 + console.log，Task 22 接通真正 Alert）。

> 具体改动以现状代码为准；本 step 不展开完整 routes/index.tsx 内容，遵循"删 typeNameById 相关代码 + 加 onDelete prop"两条主线。

- [ ] **Step 6: 跑 build + lint**

```bash
pnpm --dir frontend build && pnpm --dir frontend lint
```

Expected: 全绿。

- [ ] **Step 7: 浏览器手工烟测**

```bash
./scripts/dev.sh
```

打开 `http://localhost:5173/`，验证：
- 第一列显示 asset_code（mono）
- SN 列独立、缺失显 — muted
- 默认排序 asset_code 升序
- 列显隐菜单中"入账日期"默认未勾选；勾选后列出现
- 行 ⋯ 菜单"删除…" 派发中资产 disabled

- [ ] **Step 8: commit**

```bash
git add frontend/src/api/generated/schema.ts frontend/src/features/assets/list/ frontend/src/routes/index.tsx
git commit -m "feat(list): 列改造 · 第一列 asset_code + SN 独立列 + acquired_at 默认隐藏 + 默认 sort asset_code"
```

---

### Task 14: 列表页右上角 "+ 登记资产" 按钮

**Files:**
- Modify: `frontend/src/routes/index.tsx`（顶部 toolbar 区加按钮）

- [ ] **Step 1: 改 routes/index.tsx 工具栏**

在列表页顶部 toolbar（搜索框 + 列显隐菜单同行）右侧加：

```tsx
import { Plus } from "lucide-react";
// ...

<Link to="/assets/new">
  <Button>
    <Plus className="mr-2 h-4 w-4" />
    登记资产
  </Button>
</Link>
```

> 注意：`/assets/new` 路由在 Task 18 创建。本 step 先放跳转链接（Link 编译期不报错），实际可用要等 Task 18。

- [ ] **Step 2: 验证 build（路由不存在不会编译错，但 Link 可能 typed-routes 校验失败）**

```bash
pnpm --dir frontend build
```

如果 typed-routes 报 `/assets/new` 不存在，临时改为 `<Link to="/" search={...}>` 占位 + TODO 注释，Task 18 切回。

实际更稳妥的做法：本 step 先用 `<a href="/assets/new">` 普通链接，等 Task 18 创建路由后改回 `<Link>`。

- [ ] **Step 3: commit**

```bash
git add frontend/src/routes/index.tsx
git commit -m "feat(list): 列表页右上角加 + 登记资产 跳转 /assets/new（占位 a href，路由 Task 18 接通）"
```

---

## ✅ Phase 2 完成判定

```bash
pnpm --dir frontend build && pnpm --dir frontend lint
```

Expected: 全绿。浏览器列表页 asset_code + SN 独立列正常显示。

---

## Phase 3 · 表单组件层（Task 15-20）

### Task 15: FieldDef → Zod schema 纯函数 + Vitest（核心 + 高 ROI）

**Files:**
- Create: `frontend/src/features/assets/form/field-def-to-zod.ts`
- Create: `frontend/src/features/assets/form/types.ts`（FieldDef 类型）
- Test: `frontend/tests/unit/field-def-to-zod.test.ts`

- [ ] **Step 1: 写 FieldDef 类型**

`frontend/src/features/assets/form/types.ts`（新建）：

```ts
/**
 * AssetType.custom_fields 的元素结构（spec D2 / 12 字段）。
 *
 * 与后端 `CustomFieldDef` Pydantic schema 1:1 对齐。
 */
export type FieldDef = {
  /** 字段名（schema 标识符），不含单位后缀 */
  name: string;
  /** 显示名（用户看到），缺省 = name */
  label?: string;
  type: 'string' | 'text' | 'int' | 'float' | 'bool' | 'date' | 'enum' | 'multi-enum' | 'url';
  required?: boolean;
  default?: string | number | boolean | null;
  placeholder?: string;
  help?: string;
  /** 仅 int/float 用，input 内右侧 muted 显示，不参与校验 */
  unit?: string;
  /** 仅 int/float */
  min?: number;
  /** 仅 int/float */
  max?: number;
  /** 仅 enum / multi-enum */
  options?: string[];
  /** 仅 enum / multi-enum override 默认阈值（≤4 RadioGroup / ≥5 Select） */
  displayAs?: 'radio' | 'select';
};
```

- [ ] **Step 2: 写 field-def-to-zod 测试（10+ case 覆盖关键路径）**

`frontend/tests/unit/field-def-to-zod.test.ts`（新建）：

```ts
import { describe, expect, it } from 'vitest';
import { fieldDefsToZodSchema } from '@/features/assets/form/field-def-to-zod';
import type { FieldDef } from '@/features/assets/form/types';

describe('fieldDefsToZodSchema', () => {
  it('string required: rejects empty, accepts non-empty', () => {
    const schema = fieldDefsToZodSchema([{ name: 'cpu', type: 'string', required: true }]);
    expect(schema.safeParse({ cpu: '' }).success).toBe(false);
    expect(schema.safeParse({ cpu: 'i7' }).success).toBe(true);
  });

  it('string optional: accepts empty/undefined', () => {
    const schema = fieldDefsToZodSchema([{ name: 'cpu', type: 'string' }]);
    expect(schema.safeParse({}).success).toBe(true);
    expect(schema.safeParse({ cpu: '' }).success).toBe(true);
  });

  it('int: coerces string to number, rejects float', () => {
    const schema = fieldDefsToZodSchema([{ name: 'ram', type: 'int', required: true }]);
    const r = schema.safeParse({ ram: '32' });
    expect(r.success).toBe(true);
    if (r.success) expect(r.data.ram).toBe(32);

    expect(schema.safeParse({ ram: '32.5' }).success).toBe(false);
    expect(schema.safeParse({ ram: 'not-a-number' }).success).toBe(false);
  });

  it('int with min/max', () => {
    const schema = fieldDefsToZodSchema([
      { name: 'ram', type: 'int', required: true, min: 1, max: 128 },
    ]);
    expect(schema.safeParse({ ram: '0' }).success).toBe(false);
    expect(schema.safeParse({ ram: '256' }).success).toBe(false);
    expect(schema.safeParse({ ram: '32' }).success).toBe(true);
  });

  it('float: accepts decimal', () => {
    const schema = fieldDefsToZodSchema([{ name: 'weight', type: 'float', required: true }]);
    const r = schema.safeParse({ weight: '1.13' });
    expect(r.success).toBe(true);
    if (r.success) expect(r.data.weight).toBeCloseTo(1.13);
  });

  it('bool: accepts true/false', () => {
    const schema = fieldDefsToZodSchema([{ name: 'is_new', type: 'bool' }]);
    expect(schema.safeParse({ is_new: true }).success).toBe(true);
    expect(schema.safeParse({ is_new: false }).success).toBe(true);
    expect(schema.safeParse({}).success).toBe(true); // optional
  });

  it('date: ISO format', () => {
    const schema = fieldDefsToZodSchema([{ name: 'warranty', type: 'date', required: true }]);
    expect(schema.safeParse({ warranty: '2026-04-26' }).success).toBe(true);
    expect(schema.safeParse({ warranty: '2026/04/26' }).success).toBe(false);
    expect(schema.safeParse({ warranty: '' }).success).toBe(false);
  });

  it('enum: only accepts options', () => {
    const schema = fieldDefsToZodSchema([
      { name: 'color', type: 'enum', required: true, options: ['银色', '黑色', '深空灰'] },
    ]);
    expect(schema.safeParse({ color: '银色' }).success).toBe(true);
    expect(schema.safeParse({ color: '红色' }).success).toBe(false);
  });

  it('multi-enum: array of options', () => {
    const schema = fieldDefsToZodSchema([
      { name: 'ports', type: 'multi-enum', options: ['Type-C', 'HDMI', 'USB-A'] },
    ]);
    expect(schema.safeParse({ ports: ['Type-C', 'HDMI'] }).success).toBe(true);
    expect(schema.safeParse({ ports: ['Type-C', 'XYZ'] }).success).toBe(false);
    expect(schema.safeParse({ ports: [] }).success).toBe(true); // optional
  });

  it('url: rejects non-url', () => {
    const schema = fieldDefsToZodSchema([{ name: 'site', type: 'url', required: true }]);
    expect(schema.safeParse({ site: 'https://example.com' }).success).toBe(true);
    expect(schema.safeParse({ site: 'not-a-url' }).success).toBe(false);
  });

  it('combined: multi-field schema', () => {
    const schema = fieldDefsToZodSchema([
      { name: 'cpu', type: 'string', required: true },
      { name: 'ram', type: 'int', required: true },
      { name: 'has_lid', type: 'bool' },
    ]);
    expect(schema.safeParse({ cpu: 'i7', ram: '32' }).success).toBe(true);
    expect(schema.safeParse({ cpu: 'i7' }).success).toBe(false); // ram required
  });
});
```

- [ ] **Step 3: 跑测验证 FAIL**

```bash
pnpm --dir frontend test -- field-def-to-zod
```

Expected: FAIL（模块不存在）。

- [ ] **Step 4: 实现 field-def-to-zod**

`frontend/src/features/assets/form/field-def-to-zod.ts`（新建）：

```ts
import { z } from 'zod';
import type { FieldDef } from './types';

/**
 * 把 FieldDef[] 编译成一个 ZodObject，作为 RHF 表单的 schema。
 *
 * 规则（spec §5.6 / D7）：
 * - string/text: z.string()，required → .min(1)
 * - int: z.coerce.number().int()，可选 min/max
 * - float: z.coerce.number()，可选 min/max
 * - bool: z.boolean()，默认 false
 * - date: z.string().regex(YYYY-MM-DD) —— 因为 RHF Calendar 输出 ISO 字符串
 * - enum: z.enum(options as [string, ...string[]])
 * - multi-enum: z.array(z.enum(options))，可选 → 默认空数组
 * - url: z.string().url()，required → 必须满足 url
 *
 * unit 字段不参与校验（仅显示）。
 */
export function fieldDefsToZodSchema(defs: FieldDef[]): z.ZodObject<z.ZodRawShape> {
  const shape: z.ZodRawShape = {};
  for (const def of defs) {
    shape[def.name] = buildFieldSchema(def);
  }
  return z.object(shape);
}

function buildFieldSchema(def: FieldDef): z.ZodTypeAny {
  switch (def.type) {
    case 'string':
    case 'text': {
      let s: z.ZodTypeAny = z.string();
      if (def.required) {
        s = (s as z.ZodString).min(1, `${def.label ?? def.name} 必填`);
      } else {
        s = s.optional().or(z.literal(''));
      }
      return s;
    }
    case 'int': {
      let s = z.coerce.number().int(`${def.label ?? def.name} 必须是整数`);
      if (def.min != null) s = s.min(def.min);
      if (def.max != null) s = s.max(def.max);
      return def.required ? s : s.optional();
    }
    case 'float': {
      let s = z.coerce.number();
      if (def.min != null) s = s.min(def.min);
      if (def.max != null) s = s.max(def.max);
      return def.required ? s : s.optional();
    }
    case 'bool': {
      return z.boolean().optional().default(false);
    }
    case 'date': {
      const s = z.string().regex(
        /^\d{4}-\d{2}-\d{2}$/,
        `${def.label ?? def.name} 必须是 YYYY-MM-DD 格式`,
      );
      return def.required ? s : s.optional().or(z.literal(''));
    }
    case 'enum': {
      const opts = def.options ?? [];
      if (opts.length === 0) {
        // 没有 options 退化为 string
        return def.required ? z.string().min(1) : z.string().optional();
      }
      const e = z.enum(opts as [string, ...string[]]);
      return def.required ? e : e.optional();
    }
    case 'multi-enum': {
      const opts = def.options ?? [];
      if (opts.length === 0) {
        return z.array(z.string()).optional().default([]);
      }
      const arr = z.array(z.enum(opts as [string, ...string[]]));
      return def.required ? arr.min(1) : arr.optional().default([]);
    }
    case 'url': {
      const s = z.string().url(`${def.label ?? def.name} 必须是合法 URL`);
      return def.required ? s : s.optional().or(z.literal(''));
    }
  }
}
```

- [ ] **Step 5: 跑测验证 PASS**

```bash
pnpm --dir frontend test -- field-def-to-zod
```

Expected: 11+ case 全 PASS。

- [ ] **Step 6: lint + commit**

```bash
pnpm --dir frontend lint
git add frontend/src/features/assets/form/ frontend/tests/unit/field-def-to-zod.test.ts
git commit -m "feat(form): FieldDef → Zod schema 生成器（纯函数）+ 11 case Vitest 覆盖"
```

---

### Task 16: field-controls/ 9 个子组件 + DynamicFieldRenderer

**Files:**
- Create: `frontend/src/features/assets/form/field-controls/string-field.tsx`
- Create: `frontend/src/features/assets/form/field-controls/text-field.tsx`
- Create: `frontend/src/features/assets/form/field-controls/number-field.tsx`（int/float 共用）
- Create: `frontend/src/features/assets/form/field-controls/bool-field.tsx`
- Create: `frontend/src/features/assets/form/field-controls/date-field.tsx`
- Create: `frontend/src/features/assets/form/field-controls/enum-field.tsx`
- Create: `frontend/src/features/assets/form/field-controls/multi-enum-field.tsx`
- Create: `frontend/src/features/assets/form/field-controls/url-field.tsx`
- Create: `frontend/src/features/assets/form/dynamic-field-renderer.tsx`

> 这是个体积大但机械的 Task。每个 field 组件都是 RHF Controller + shadcn 组件 + FieldDef 元数据消费的简单组合。我把范式列一次，剩下重复。

- [ ] **Step 1: 写 StringField 作为范式**

`frontend/src/features/assets/form/field-controls/string-field.tsx`：

```tsx
import { Controller, type Control } from 'react-hook-form';
import { Input } from '@/components/ui/input';
import { FormField, FormItem, FormLabel, FormControl, FormDescription, FormMessage } from '@/components/ui/form';
import type { FieldDef } from '../types';

export function StringField({ def, control }: { def: FieldDef; control: Control }) {
  return (
    <FormField
      control={control}
      name={def.name}
      render={({ field }) => (
        <FormItem>
          <FormLabel>
            {def.label ?? def.name}
            {def.required && <span className="ml-1 text-destructive">*</span>}
          </FormLabel>
          <FormControl>
            <Input
              {...field}
              placeholder={def.placeholder}
              value={field.value ?? ''}
            />
          </FormControl>
          {def.help && <FormDescription>{def.help}</FormDescription>}
          <FormMessage />
        </FormItem>
      )}
    />
  );
}
```

> 后续 8 个组件按相同结构，差异在 FormControl 内的 shadcn 组件类型 + 数据流。

- [ ] **Step 2: 写 TextField**

`frontend/src/features/assets/form/field-controls/text-field.tsx`：

```tsx
import { Controller, type Control } from 'react-hook-form';
import { Textarea } from '@/components/ui/textarea';
import { FormField, FormItem, FormLabel, FormControl, FormDescription, FormMessage } from '@/components/ui/form';
import type { FieldDef } from '../types';

export function TextField({ def, control }: { def: FieldDef; control: Control }) {
  return (
    <FormField
      control={control}
      name={def.name}
      render={({ field }) => (
        <FormItem>
          <FormLabel>
            {def.label ?? def.name}
            {def.required && <span className="ml-1 text-destructive">*</span>}
          </FormLabel>
          <FormControl>
            <Textarea {...field} placeholder={def.placeholder} value={field.value ?? ''} rows={3} />
          </FormControl>
          {def.help && <FormDescription>{def.help}</FormDescription>}
          <FormMessage />
        </FormItem>
      )}
    />
  );
}
```

- [ ] **Step 3: 写 NumberField（int/float 共用）**

`frontend/src/features/assets/form/field-controls/number-field.tsx`：

```tsx
import { type Control } from 'react-hook-form';
import { Input } from '@/components/ui/input';
import { FormField, FormItem, FormLabel, FormControl, FormDescription, FormMessage } from '@/components/ui/form';
import type { FieldDef } from '../types';

export function NumberField({ def, control }: { def: FieldDef; control: Control }) {
  const inputMode = def.type === 'float' ? 'decimal' : 'numeric';
  return (
    <FormField
      control={control}
      name={def.name}
      render={({ field }) => (
        <FormItem>
          <FormLabel>
            {def.label ?? def.name}
            {def.required && <span className="ml-1 text-destructive">*</span>}
          </FormLabel>
          <FormControl>
            <div className="relative">
              <Input
                type="text"
                inputMode={inputMode}
                {...field}
                placeholder={def.placeholder}
                value={field.value ?? ''}
                className={def.unit ? 'pr-12' : undefined}
              />
              {def.unit && (
                <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">
                  {def.unit}
                </span>
              )}
            </div>
          </FormControl>
          {def.help && <FormDescription>{def.help}</FormDescription>}
          <FormMessage />
        </FormItem>
      )}
    />
  );
}
```

- [ ] **Step 4: 写 BoolField**

`frontend/src/features/assets/form/field-controls/bool-field.tsx`：

```tsx
import { type Control } from 'react-hook-form';
import { Checkbox } from '@/components/ui/checkbox';
import { FormField, FormItem, FormLabel, FormControl, FormDescription, FormMessage } from '@/components/ui/form';
import type { FieldDef } from '../types';

export function BoolField({ def, control }: { def: FieldDef; control: Control }) {
  return (
    <FormField
      control={control}
      name={def.name}
      render={({ field }) => (
        <FormItem className="flex flex-row items-start gap-3 space-y-0">
          <FormControl>
            <Checkbox
              checked={!!field.value}
              onCheckedChange={field.onChange}
              id={`bool-${def.name}`}
            />
          </FormControl>
          <div className="space-y-1 leading-none">
            <FormLabel htmlFor={`bool-${def.name}`}>
              {def.label ?? def.name}
              {def.required && <span className="ml-1 text-destructive">*</span>}
            </FormLabel>
            {def.help && <FormDescription>{def.help}</FormDescription>}
            <FormMessage />
          </div>
        </FormItem>
      )}
    />
  );
}
```

- [ ] **Step 5: 写 DateField**

`frontend/src/features/assets/form/field-controls/date-field.tsx`：

```tsx
import { CalendarIcon } from 'lucide-react';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { type Control } from 'react-hook-form';
import { Button } from '@/components/ui/button';
import { Calendar } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { FormField, FormItem, FormLabel, FormControl, FormDescription, FormMessage } from '@/components/ui/form';
import { cn } from '@/lib/utils';
import type { FieldDef } from '../types';

export function DateField({ def, control }: { def: FieldDef; control: Control }) {
  return (
    <FormField
      control={control}
      name={def.name}
      render={({ field }) => (
        <FormItem className="flex flex-col">
          <FormLabel>
            {def.label ?? def.name}
            {def.required && <span className="ml-1 text-destructive">*</span>}
          </FormLabel>
          <Popover>
            <PopoverTrigger asChild>
              <FormControl>
                <Button
                  variant="outline"
                  className={cn(
                    'w-full justify-start text-left font-normal',
                    !field.value && 'text-muted-foreground',
                  )}
                >
                  <CalendarIcon className="mr-2 h-4 w-4" />
                  {field.value
                    ? format(new Date(field.value), 'yyyy-MM-dd', { locale: zhCN })
                    : (def.placeholder ?? '选择日期')}
                </Button>
              </FormControl>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="start">
              <Calendar
                mode="single"
                selected={field.value ? new Date(field.value) : undefined}
                onSelect={(d) => field.onChange(d ? format(d, 'yyyy-MM-dd') : '')}
                initialFocus
              />
            </PopoverContent>
          </Popover>
          {def.help && <FormDescription>{def.help}</FormDescription>}
          <FormMessage />
        </FormItem>
      )}
    />
  );
}
```

- [ ] **Step 6: 写 EnumField（≤4 RadioGroup / ≥5 Select）**

`frontend/src/features/assets/form/field-controls/enum-field.tsx`：

```tsx
import { type Control } from 'react-hook-form';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { FormField, FormItem, FormLabel, FormControl, FormDescription, FormMessage } from '@/components/ui/form';
import { Label } from '@/components/ui/label';
import type { FieldDef } from '../types';

const RADIO_THRESHOLD = 4;

export function EnumField({ def, control }: { def: FieldDef; control: Control }) {
  const options = def.options ?? [];
  const useRadio = def.displayAs === 'radio' || (def.displayAs !== 'select' && options.length <= RADIO_THRESHOLD);

  return (
    <FormField
      control={control}
      name={def.name}
      render={({ field }) => (
        <FormItem>
          <FormLabel>
            {def.label ?? def.name}
            {def.required && <span className="ml-1 text-destructive">*</span>}
          </FormLabel>
          <FormControl>
            {useRadio ? (
              <RadioGroup value={field.value ?? ''} onValueChange={field.onChange} className="flex flex-col gap-2">
                {options.map((opt) => (
                  <div key={opt} className="flex items-center gap-2">
                    <RadioGroupItem value={opt} id={`${def.name}-${opt}`} />
                    <Label htmlFor={`${def.name}-${opt}`} className="font-normal">{opt}</Label>
                  </div>
                ))}
              </RadioGroup>
            ) : (
              <Select value={field.value ?? ''} onValueChange={field.onChange}>
                <SelectTrigger>
                  <SelectValue placeholder={def.placeholder ?? '请选择'} />
                </SelectTrigger>
                <SelectContent>
                  {options.map((opt) => (
                    <SelectItem key={opt} value={opt}>{opt}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </FormControl>
          {def.help && <FormDescription>{def.help}</FormDescription>}
          <FormMessage />
        </FormItem>
      )}
    />
  );
}
```

> shadcn `<Label>` 组件如未引入，需 `pnpm dlx shadcn@latest add label`（添加到 Task 11）。

- [ ] **Step 7: 写 MultiEnumField（≤4 多 Checkbox / ≥5 Combobox）**

`frontend/src/features/assets/form/field-controls/multi-enum-field.tsx`：

```tsx
import { useState } from 'react';
import { type Control } from 'react-hook-form';
import { Check, ChevronsUpDown, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem } from '@/components/ui/command';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { FormField, FormItem, FormLabel, FormControl, FormDescription, FormMessage } from '@/components/ui/form';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';
import type { FieldDef } from '../types';

const CHECKBOX_THRESHOLD = 4;

export function MultiEnumField({ def, control }: { def: FieldDef; control: Control }) {
  const options = def.options ?? [];
  const useCheckboxes = def.displayAs === 'radio' || (def.displayAs !== 'select' && options.length <= CHECKBOX_THRESHOLD);

  return (
    <FormField
      control={control}
      name={def.name}
      render={({ field }) => {
        const value: string[] = field.value ?? [];
        const toggle = (opt: string) =>
          field.onChange(value.includes(opt) ? value.filter((v) => v !== opt) : [...value, opt]);

        return (
          <FormItem>
            <FormLabel>
              {def.label ?? def.name}
              {def.required && <span className="ml-1 text-destructive">*</span>}
            </FormLabel>
            <FormControl>
              {useCheckboxes ? (
                <div className="flex flex-col gap-2">
                  {options.map((opt) => (
                    <div key={opt} className="flex items-center gap-2">
                      <Checkbox
                        id={`${def.name}-${opt}`}
                        checked={value.includes(opt)}
                        onCheckedChange={() => toggle(opt)}
                      />
                      <Label htmlFor={`${def.name}-${opt}`} className="font-normal">{opt}</Label>
                    </div>
                  ))}
                </div>
              ) : (
                <ComboboxMulti options={options} value={value} onChange={field.onChange} placeholder={def.placeholder ?? '请选择'} />
              )}
            </FormControl>
            {def.help && <FormDescription>{def.help}</FormDescription>}
            <FormMessage />
          </FormItem>
        );
      }}
    />
  );
}

function ComboboxMulti({
  options, value, onChange, placeholder,
}: {
  options: string[]; value: string[]; onChange: (v: string[]) => void; placeholder: string;
}) {
  const [open, setOpen] = useState(false);
  const toggle = (opt: string) =>
    onChange(value.includes(opt) ? value.filter((v) => v !== opt) : [...value, opt]);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline" role="combobox" className="w-full justify-between">
          <span className="flex flex-wrap gap-1">
            {value.length === 0 ? <span className="text-muted-foreground">{placeholder}</span>
              : value.map((v) => (
                <span key={v} className="rounded-sm bg-secondary px-1.5 text-xs">
                  {v}
                  <X className="ml-1 inline h-3 w-3 cursor-pointer" onClick={(e) => { e.stopPropagation(); toggle(v); }} />
                </span>
              ))}
          </span>
          <ChevronsUpDown className="ml-2 h-4 w-4 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[--radix-popover-trigger-width] p-0">
        <Command>
          <CommandInput placeholder="搜索…" />
          <CommandEmpty>无匹配项</CommandEmpty>
          <CommandGroup>
            {options.map((opt) => (
              <CommandItem key={opt} onSelect={() => toggle(opt)}>
                <Check className={cn('mr-2 h-4 w-4', value.includes(opt) ? 'opacity-100' : 'opacity-0')} />
                {opt}
              </CommandItem>
            ))}
          </CommandGroup>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
```

- [ ] **Step 8: 写 UrlField（基于 StringField 改 type="url"）**

`frontend/src/features/assets/form/field-controls/url-field.tsx`：

```tsx
import { type Control } from 'react-hook-form';
import { Input } from '@/components/ui/input';
import { FormField, FormItem, FormLabel, FormControl, FormDescription, FormMessage } from '@/components/ui/form';
import type { FieldDef } from '../types';

export function UrlField({ def, control }: { def: FieldDef; control: Control }) {
  return (
    <FormField
      control={control}
      name={def.name}
      render={({ field }) => (
        <FormItem>
          <FormLabel>
            {def.label ?? def.name}
            {def.required && <span className="ml-1 text-destructive">*</span>}
          </FormLabel>
          <FormControl>
            <Input type="url" {...field} placeholder={def.placeholder ?? 'https://…'} value={field.value ?? ''} />
          </FormControl>
          {def.help && <FormDescription>{def.help}</FormDescription>}
          <FormMessage />
        </FormItem>
      )}
    />
  );
}
```

- [ ] **Step 9: 写 DynamicFieldRenderer**

`frontend/src/features/assets/form/dynamic-field-renderer.tsx`：

```tsx
import { type Control } from 'react-hook-form';
import { StringField } from './field-controls/string-field';
import { TextField } from './field-controls/text-field';
import { NumberField } from './field-controls/number-field';
import { BoolField } from './field-controls/bool-field';
import { DateField } from './field-controls/date-field';
import { EnumField } from './field-controls/enum-field';
import { MultiEnumField } from './field-controls/multi-enum-field';
import { UrlField } from './field-controls/url-field';
import type { FieldDef } from './types';

export function DynamicFieldRenderer({ def, control }: { def: FieldDef; control: Control }) {
  switch (def.type) {
    case 'string': return <StringField def={def} control={control} />;
    case 'text': return <TextField def={def} control={control} />;
    case 'int': case 'float': return <NumberField def={def} control={control} />;
    case 'bool': return <BoolField def={def} control={control} />;
    case 'date': return <DateField def={def} control={control} />;
    case 'enum': return <EnumField def={def} control={control} />;
    case 'multi-enum': return <MultiEnumField def={def} control={control} />;
    case 'url': return <UrlField def={def} control={control} />;
  }
}
```

- [ ] **Step 10: 跑 build 验证**

```bash
pnpm --dir frontend build
```

Expected: PASS。

- [ ] **Step 11: §3.5 红线扫描**

```bash
grep -rnE 'scale-|animate-spin|backdrop-blur|bg-gradient' frontend/src/features/assets/form/
```

Expected: 0 命中。

- [ ] **Step 12: lint + commit**

```bash
pnpm --dir frontend lint
git add frontend/src/features/assets/form/
git commit -m "feat(form): 9 个 field-control 子组件 + DynamicFieldRenderer（schema-driven 渲染）"
```

**§3.5 约束引用：** §3.5.4（radius token via shadcn）；§3.5.5（无 transition 入场动效，瞬间挂载）；§3.5.6（红线 0 命中）；§3.5.7（首次引入 Form/Checkbox/RadioGroup/Select/Popover/Calendar/Command 已审 variant）。

---

### Task 17: AssetFormFields 共享底层（通用字段 + custom_fields 渲染）

**Files:**
- Create: `frontend/src/features/assets/form/asset-form-fields.tsx`
- Create: `frontend/src/features/assets/form/general-fields-form.tsx`
- Create: `frontend/src/features/assets/form/custom-fields-form.tsx`

- [ ] **Step 1: 写 GeneralFieldsForm**

`frontend/src/features/assets/form/general-fields-form.tsx`：

```tsx
import { type Control } from 'react-hook-form';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { FormField, FormItem, FormLabel, FormControl, FormDescription, FormMessage } from '@/components/ui/form';
import { DateField } from './field-controls/date-field';
import type { components } from '@/api/generated/schema';

type AssetTypeRead = components['schemas']['TypeRead'];

interface GeneralFieldsFormProps {
  control: Control;
  types: AssetTypeRead[];
  /** 编辑模式下 type 字段 disabled */
  typeReadonly: boolean;
  /** 编辑模式下显示只读 asset_code */
  assetCode?: string;
}

export function GeneralFieldsForm({ control, types, typeReadonly, assetCode }: GeneralFieldsFormProps) {
  return (
    <div className="space-y-4">
      {assetCode && (
        <FormItem>
          <FormLabel>编号</FormLabel>
          <FormControl>
            <Input value={assetCode} readOnly disabled className="font-code bg-muted" />
          </FormControl>
          <FormDescription>系统自动生成，创建后不可改</FormDescription>
        </FormItem>
      )}

      <FormField
        control={control}
        name="name"
        render={({ field }) => (
          <FormItem>
            <FormLabel>资产名 <span className="text-destructive">*</span></FormLabel>
            <FormControl><Input {...field} placeholder="如 ThinkPad X1 Carbon" /></FormControl>
            <FormMessage />
          </FormItem>
        )}
      />

      <FormField
        control={control}
        name="type_id"
        render={({ field }) => (
          <FormItem>
            <FormLabel>
              资产类型 <span className="text-destructive">*</span>
              {typeReadonly && <span className="ml-2 text-xs text-muted-foreground">创建后不可改</span>}
            </FormLabel>
            <Select value={field.value ?? ''} onValueChange={field.onChange} disabled={typeReadonly}>
              <FormControl>
                <SelectTrigger><SelectValue placeholder="请选择类型" /></SelectTrigger>
              </FormControl>
              <SelectContent>
                {types.map((t) => (
                  <SelectItem key={t.id} value={t.id}>
                    {t.name} <span className="ml-2 font-code text-xs text-muted-foreground">{t.code_prefix}</span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <FormMessage />
          </FormItem>
        )}
      />

      <FormField
        control={control}
        name="serial_number"
        render={({ field }) => (
          <FormItem>
            <FormLabel>SN</FormLabel>
            <FormControl><Input {...field} value={field.value ?? ''} placeholder="厂家铭牌编号（可空）" className="font-code" /></FormControl>
            <FormMessage />
          </FormItem>
        )}
      />

      <DateField
        control={control}
        def={{
          name: 'acquired_at', label: '入账日期', type: 'date',
          help: '业务意义的入账日期；不知道时不填',
        }}
      />

      <FormField
        control={control}
        name="holder"
        render={({ field }) => (
          <FormItem>
            <FormLabel>持有人</FormLabel>
            <FormControl><Input {...field} value={field.value ?? ''} placeholder="可空" /></FormControl>
            <FormMessage />
          </FormItem>
        )}
      />

      <FormField
        control={control}
        name="location"
        render={({ field }) => (
          <FormItem>
            <FormLabel>位置</FormLabel>
            <FormControl><Input {...field} value={field.value ?? ''} placeholder="可空" /></FormControl>
            <FormMessage />
          </FormItem>
        )}
      />

      <FormField
        control={control}
        name="notes"
        render={({ field }) => (
          <FormItem>
            <FormLabel>备注</FormLabel>
            <FormControl><Textarea {...field} value={field.value ?? ''} rows={3} placeholder="可空" /></FormControl>
            <FormMessage />
          </FormItem>
        )}
      />
    </div>
  );
}
```

- [ ] **Step 2: 写 CustomFieldsForm**

`frontend/src/features/assets/form/custom-fields-form.tsx`：

```tsx
import { type Control } from 'react-hook-form';
import { DynamicFieldRenderer } from './dynamic-field-renderer';
import type { FieldDef } from './types';

interface CustomFieldsFormProps {
  control: Control;
  fieldDefs: FieldDef[];
  typeName: string;
}

export function CustomFieldsForm({ control, fieldDefs, typeName }: CustomFieldsFormProps) {
  if (fieldDefs.length === 0) {
    return null;
  }
  return (
    <section className="space-y-4">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-foreground border-b pb-1.5">
        {typeName}
        <span className="ml-2 rounded-full bg-secondary px-2 text-xs font-normal">
          {fieldDefs.length} 个字段
        </span>
      </h2>
      <div className="space-y-4">
        {fieldDefs.map((def) => (
          <DynamicFieldRenderer key={def.name} def={def} control={control} />
        ))}
      </div>
    </section>
  );
}
```

- [ ] **Step 3: 写 AssetFormFields 整合**

`frontend/src/features/assets/form/asset-form-fields.tsx`：

```tsx
import { useMemo } from 'react';
import { type Control, useWatch } from 'react-hook-form';
import { GeneralFieldsForm } from './general-fields-form';
import { CustomFieldsForm } from './custom-fields-form';
import type { FieldDef } from './types';
import type { components } from '@/api/generated/schema';

type AssetTypeRead = components['schemas']['TypeRead'];

interface AssetFormFieldsProps {
  control: Control;
  types: AssetTypeRead[];
  mode: 'create' | 'edit';
  assetCode?: string;
}

export function AssetFormFields({ control, types, mode, assetCode }: AssetFormFieldsProps) {
  // 监听 type_id 切换，重新渲染 custom_fields 区块
  const selectedTypeId = useWatch({ control, name: 'type_id' });

  const selectedType = useMemo(
    () => types.find((t) => t.id === selectedTypeId),
    [types, selectedTypeId],
  );
  const fieldDefs = (selectedType?.custom_fields ?? []) as FieldDef[];

  return (
    <div className="space-y-10">
      <section className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-foreground border-b pb-1.5">
          基础信息
        </h2>
        <GeneralFieldsForm
          control={control}
          types={types}
          typeReadonly={mode === 'edit'}
          assetCode={assetCode}
        />
      </section>

      {selectedType && (
        <CustomFieldsForm
          control={control}
          fieldDefs={fieldDefs}
          typeName={selectedType.name}
        />
      )}
    </div>
  );
}
```

- [ ] **Step 4: 跑 build 验证**

```bash
pnpm --dir frontend build
```

Expected: PASS。注意 TypeRead 类型 `code_prefix` / `custom_fields` 字段必须在 generated schema 中存在（Task 13 已 regen）。

- [ ] **Step 5: 红线扫描**

```bash
grep -rnE 'scale-|animate-spin|backdrop-blur|bg-gradient' frontend/src/features/assets/form/
```

Expected: 0 命中。

- [ ] **Step 6: commit**

```bash
git add frontend/src/features/assets/form/
git commit -m "feat(form): AssetFormFields 共享底层 + GeneralFieldsForm + CustomFieldsForm（H2 分区）"
```

**§3.5 约束引用：** §3.5.1（H2 分区，无 Card 装饰）；§3.5.2（asset_code 只读用 font-code）；§3.5.5（type 切换瞬间 useWatch 触发，无 transition）。

---

### Task 18: AssetCreateForm + /assets/new 路由

**Files:**
- Create: `frontend/src/features/assets/form/asset-create-form.tsx`
- Create: `frontend/src/features/assets/form/form-toast.ts`
- Create: `frontend/src/features/assets/form/build-create-schema.ts`
- Create: `frontend/src/routes/assets.new.tsx`

- [ ] **Step 1: 写 form-toast 文案常量**

`frontend/src/features/assets/form/form-toast.ts`：

```ts
export const TOAST = {
  CREATE_SUCCESS: '登记成功',
  UPDATE_SUCCESS: '更新成功',
  DELETE_SUCCESS: '删除成功',
  STATUS_CHANGE_SUCCESS: '状态已切换',
  UPLOAD_SUCCESS: '附件上传成功',
  GENERIC_FAILURE: '操作失败，请重试',
  FILE_TOO_LARGE: '文件超过 10MB 限制',
  UNSUPPORTED_TYPE: '不支持的文件类型',
} as const;

export const PENDING_TEXT = {
  CREATE: '登记中…',
  UPDATE: '保存中…',
  DELETE: '删除中…',
} as const;
```

- [ ] **Step 2: 写 build-create-schema（合并通用字段 + custom_fields）**

`frontend/src/features/assets/form/build-create-schema.ts`：

```ts
import { z } from 'zod';
import { fieldDefsToZodSchema } from './field-def-to-zod';
import type { FieldDef } from './types';

const baseSchema = z.object({
  name: z.string().min(1, '资产名必填'),
  type_id: z.string().uuid('请选择资产类型'),
  serial_number: z.string().optional(),
  acquired_at: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, '日期格式 YYYY-MM-DD').optional().or(z.literal('')),
  holder: z.string().optional(),
  location: z.string().optional(),
  notes: z.string().optional(),
});

/**
 * 把通用字段 schema 与该 type 的 custom_fields schema 合并。
 * custom_data 嵌套在 'custom_data' key 下，前端对它单独 schema-driven，提交时 spread 出去。
 */
export function buildCreateSchema(fieldDefs: FieldDef[]) {
  return baseSchema.extend({
    custom_data: fieldDefsToZodSchema(fieldDefs),
  });
}

export type CreateFormValues = z.infer<ReturnType<typeof buildCreateSchema>>;
```

- [ ] **Step 3: 写 AssetCreateForm**

`frontend/src/features/assets/form/asset-create-form.tsx`：

```tsx
import { useEffect, useMemo } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useNavigate } from '@tanstack/react-router';
import { Button } from '@/components/ui/button';
import { Form } from '@/components/ui/form';
import { InlineErrorBanner } from '@/components/feedback/inline-error-banner';
import { useAssetTypesQuery } from '@/api/hooks/types';
import { useCreateAsset } from '@/api/hooks/assets';
import { toFriendlyMessage } from '@/lib/error';
import { AssetFormFields } from './asset-form-fields';
import { buildCreateSchema, type CreateFormValues } from './build-create-schema';
import { TOAST, PENDING_TEXT } from './form-toast';
import type { FieldDef } from './types';

export function AssetCreateForm() {
  const navigate = useNavigate({ from: '/assets/new' });
  const typesQuery = useAssetTypesQuery();
  const types = typesQuery.data ?? [];
  const mutation = useCreateAsset();

  const form = useForm<CreateFormValues>({
    resolver: zodResolver(buildCreateSchema([])),
    defaultValues: {
      name: '', type_id: '', serial_number: '', acquired_at: '',
      holder: '', location: '', notes: '', custom_data: {},
    },
    mode: 'onSubmit',
  });

  const selectedTypeId = useWatch({ control: form.control, name: 'type_id' });
  const selectedType = useMemo(() => types.find((t) => t.id === selectedTypeId), [types, selectedTypeId]);

  // type 切换时重置 custom_data 为该 type 的 default 值
  useEffect(() => {
    if (selectedType) {
      const defs = (selectedType.custom_fields ?? []) as FieldDef[];
      const defaults: Record<string, unknown> = {};
      for (const d of defs) {
        if (d.default !== undefined && d.default !== null) defaults[d.name] = d.default;
      }
      form.setValue('custom_data', defaults as never, { shouldValidate: false });
    } else {
      form.setValue('custom_data', {} as never, { shouldValidate: false });
    }
  }, [selectedType, form]);

  // 重建 resolver 让 custom_fields schema 跟上
  useEffect(() => {
    const fieldDefs = (selectedType?.custom_fields ?? []) as FieldDef[];
    // RHF 不直接支持运行时换 resolver；通过手动 `form.clearErrors` + 在 submit 时手工跑 schema 来 cover
    form.clearErrors();
    void fieldDefs;  // 保留引用，trigger effect
  }, [selectedType, form]);

  async function onSubmit(values: CreateFormValues) {
    const fieldDefs = (selectedType?.custom_fields ?? []) as FieldDef[];
    const schema = buildCreateSchema(fieldDefs);
    const parsed = schema.safeParse(values);
    if (!parsed.success) {
      // 把 custom_data.* 错误回填到对应字段
      for (const issue of parsed.error.issues) {
        const path = issue.path.join('.');
        form.setError(path as never, { message: issue.message });
      }
      return;
    }
    try {
      const created = await mutation.mutateAsync({
        name: parsed.data.name,
        type_id: parsed.data.type_id,
        serial_number: parsed.data.serial_number || null,
        acquired_at: parsed.data.acquired_at || null,
        holder: parsed.data.holder || null,
        location: parsed.data.location || null,
        notes: parsed.data.notes || null,
        custom_data: parsed.data.custom_data ?? {},
      });
      navigate({ to: '/assets/$id', params: { id: created.id } });
    } catch (err) {
      form.setError('root', { message: toFriendlyMessage(err) });
    }
  }

  if (typesQuery.isLoading) return <div className="text-muted-foreground">加载类型…</div>;
  if (typesQuery.isError) return <InlineErrorBanner message={toFriendlyMessage(typesQuery.error)} />;

  if (types.length === 0) {
    return (
      <div className="mx-auto max-w-2xl space-y-4">
        <h1 className="text-2xl font-semibold">登记新资产</h1>
        <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm dark:border-amber-900 dark:bg-amber-950">
          <p className="font-medium">尚未创建任何类型</p>
          <p className="mt-2 text-muted-foreground">请用 CLI 创建一个类型：</p>
          <pre className="mt-2 overflow-x-auto rounded bg-background p-2 font-code text-xs">
{`asset-hub type define \\
  --name "笔记本电脑" \\
  --prefix NB \\
  --fields '[{"name":"cpu","type":"string","required":true}]'`}
          </pre>
          <p className="mt-2 text-muted-foreground">或让 Agent 帮你建（"创建一个笔记本电脑类型，前缀 NB"）。</p>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h1 className="text-2xl font-semibold">登记新资产</h1>

      {form.formState.errors.root && <InlineErrorBanner message={String(form.formState.errors.root.message)} />}

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-10">
          <AssetFormFields control={form.control} types={types} mode="create" />

          <div className="flex justify-end gap-3 border-t pt-6">
            <Button type="button" variant="ghost" onClick={() => navigate({ to: '/' })}>
              取消
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? PENDING_TEXT.CREATE : '登记'}
            </Button>
          </div>
        </form>
      </Form>
    </div>
  );
}
```

- [ ] **Step 4: 写路由**

`frontend/src/routes/assets.new.tsx`（新建）：

```tsx
import { createFileRoute } from '@tanstack/react-router';
import { AssetCreateForm } from '@/features/assets/form/asset-create-form';

export const Route = createFileRoute('/assets/new')({
  component: AssetCreateForm,
});
```

- [ ] **Step 5: 让 Task 14 的 `<a href>` 改回 `<Link to="/assets/new">`**

如果 Task 14 用了 `<a href>` 占位，回 `routes/index.tsx` 改回 `<Link to="/assets/new">`。

- [ ] **Step 6: 跑 build + lint**

```bash
pnpm --dir frontend build && pnpm --dir frontend lint
```

Expected: PASS。

- [ ] **Step 7: 浏览器手工烟测**

- 没创建过 type → 进 `/assets/new` 显示 inline 引导文案
- CLI 跑 `uv run asset-hub type define --name "笔记本" --prefix NB --fields '[{"name":"cpu","type":"string","required":true},{"name":"ram","type":"int","required":true,"unit":"GB"}]'`
- 刷新页面 → type select 出现
- 选 NB → "笔记本"区块出现 cpu / ram 两个字段
- 必填留空提交 → field-level error
- 全填提交 → 跳详情页 + Toast "登记成功"
- 详情页验证 asset_code = NB-001（per-type 第 1 个）

- [ ] **Step 8: commit**

```bash
git add frontend/src/features/assets/form/asset-create-form.tsx frontend/src/features/assets/form/build-create-schema.ts frontend/src/features/assets/form/form-toast.ts frontend/src/routes/assets.new.tsx frontend/src/routes/index.tsx
git commit -m "feat(form): AssetCreateForm + /assets/new 路由 + type select 空状态 inline 引导"
```

**§3.5 约束引用：** §3.5.1（单列布局，无装饰）；§3.5.3（提交按钮 primary 蓝，pending 文字"登记中…"）；§3.5.5（form 入场无 stagger）；§3.5.6（mutation pending 不显式 spinner）；§3.5.7（首次使用所有 form-* shadcn 组件）。

---

### Task 19: AssetEditForm + /assets/$id/edit 路由

**Files:**
- Create: `frontend/src/features/assets/form/asset-edit-form.tsx`
- Create: `frontend/src/features/assets/form/build-edit-schema.ts`
- Create: `frontend/src/routes/assets.$id.edit.tsx`

- [ ] **Step 1: 写 build-edit-schema**

`frontend/src/features/assets/form/build-edit-schema.ts`：

```ts
import { z } from 'zod';
import { fieldDefsToZodSchema } from './field-def-to-zod';
import type { FieldDef } from './types';

const baseEditSchema = z.object({
  name: z.string().min(1),
  // type_id 不在 EditSchema 中——D9 不允许改
  serial_number: z.string().optional(),
  acquired_at: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).optional().or(z.literal('')),
  holder: z.string().optional(),
  location: z.string().optional(),
  notes: z.string().optional(),
});

export function buildEditSchema(fieldDefs: FieldDef[]) {
  return baseEditSchema.extend({
    custom_data: fieldDefsToZodSchema(fieldDefs),
  });
}

export type EditFormValues = z.infer<ReturnType<typeof buildEditSchema>>;
```

- [ ] **Step 2: 写 AssetEditForm**

`frontend/src/features/assets/form/asset-edit-form.tsx`：

```tsx
import { useEffect, useMemo } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useNavigate, useParams } from '@tanstack/react-router';
import { Button } from '@/components/ui/button';
import { Form } from '@/components/ui/form';
import { InlineErrorBanner } from '@/components/feedback/inline-error-banner';
import { useAssetTypesQuery } from '@/api/hooks/types';
import { useAssetDetailQuery, useUpdateAsset } from '@/api/hooks/assets';
import { toFriendlyMessage } from '@/lib/error';
import { AssetFormFields } from './asset-form-fields';
import { buildEditSchema, type EditFormValues } from './build-edit-schema';
import { TOAST, PENDING_TEXT } from './form-toast';
import type { FieldDef } from './types';

export function AssetEditForm() {
  const { id } = useParams({ from: '/assets/$id/edit' });
  const navigate = useNavigate({ from: '/assets/$id/edit' });
  const detailQuery = useAssetDetailQuery(id);
  const typesQuery = useAssetTypesQuery();
  const types = typesQuery.data ?? [];
  const mutation = useUpdateAsset(id);

  const asset = detailQuery.data;
  const selectedType = useMemo(
    () => (asset ? types.find((t) => t.id === asset.type_id) : undefined),
    [asset, types],
  );
  const fieldDefs = (selectedType?.custom_fields ?? []) as FieldDef[];

  const form = useForm<EditFormValues>({
    resolver: zodResolver(buildEditSchema(fieldDefs)),
    defaultValues: {
      name: '', serial_number: '', acquired_at: '', holder: '', location: '', notes: '', custom_data: {},
    },
    mode: 'onSubmit',
  });

  // 数据到位后 reset 表单
  useEffect(() => {
    if (asset) {
      form.reset({
        name: asset.name,
        serial_number: asset.serial_number ?? '',
        acquired_at: asset.acquired_at ?? '',
        holder: asset.holder ?? '',
        location: asset.location ?? '',
        notes: asset.notes ?? '',
        custom_data: (asset.custom_data ?? {}) as never,
      });
    }
  }, [asset, form]);

  async function onSubmit(values: EditFormValues) {
    const schema = buildEditSchema(fieldDefs);
    const parsed = schema.safeParse(values);
    if (!parsed.success) {
      for (const issue of parsed.error.issues) {
        form.setError(issue.path.join('.') as never, { message: issue.message });
      }
      return;
    }
    try {
      await mutation.mutateAsync({
        name: parsed.data.name,
        serial_number: parsed.data.serial_number || null,
        acquired_at: parsed.data.acquired_at || null,
        holder: parsed.data.holder || null,
        location: parsed.data.location || null,
        notes: parsed.data.notes || null,
        custom_data: parsed.data.custom_data ?? {},
      });
      navigate({ to: '/assets/$id', params: { id } });
    } catch (err) {
      form.setError('root', { message: toFriendlyMessage(err) });
    }
  }

  if (detailQuery.isLoading || typesQuery.isLoading) return <div className="text-muted-foreground">加载…</div>;
  if (detailQuery.isError) return <InlineErrorBanner message={toFriendlyMessage(detailQuery.error)} />;
  if (!asset) return null;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h1 className="text-2xl font-semibold">编辑资产</h1>

      {form.formState.errors.root && (
        <InlineErrorBanner message={String(form.formState.errors.root.message)} />
      )}

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-10">
          {/* type_id 不在 form values 中，但 AssetFormFields 需要展示 type select disabled。
             把 type_id 作为 form 的隐藏值（仅显示用），或在 AssetFormFields 里通过 prop 显式传当前 type。
             这里简单做法：临时把 asset.type_id 注入 form.control 的 watch 来触发 AssetFormFields 渲染。 */}
          <AssetFormFieldsForEdit
            control={form.control}
            types={types}
            currentTypeId={asset.type_id}
            assetCode={asset.asset_code}
          />

          <div className="flex justify-end gap-3 border-t pt-6">
            <Button type="button" variant="ghost" onClick={() => navigate({ to: '/assets/$id', params: { id } })}>
              取消
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? PENDING_TEXT.UPDATE : '保存'}
            </Button>
          </div>
        </form>
      </Form>
    </div>
  );
}

/**
 * 编辑模式专用 wrapper：把 currentTypeId 注入 form.setValue 让 AssetFormFields 的
 * useWatch('type_id') 能拿到值，进而正确渲染 custom_fields 区块。
 */
function AssetFormFieldsForEdit({
  control, types, currentTypeId, assetCode,
}: {
  control: any; types: any[]; currentTypeId: string; assetCode: string;
}) {
  // hack：把 type_id 写入 form state 让 useWatch 拿到，但 type_id 不参与提交
  // 更稳妥：在 buildEditSchema 加 type_id 字段（但禁止改），提交时 strip 掉。
  return (
    <AssetFormFieldsWithInjectedType
      control={control}
      types={types}
      typeId={currentTypeId}
      assetCode={assetCode}
    />
  );
}

function AssetFormFieldsWithInjectedType({
  control, types, typeId, assetCode,
}: {
  control: any; types: any[]; typeId: string; assetCode: string;
}) {
  // 简化路径：直接 prop 传 typeId 给 AssetFormFields 的内部 useWatch 兜底。
  // 实际实现：AssetFormFields 加 prop overrideSelectedTypeId，编辑模式下用 prop，
  // 创建模式下用 useWatch。下面修改 AssetFormFields 文件。
  return (
    <AssetFormFields
      control={control}
      types={types}
      mode="edit"
      assetCode={assetCode}
      forceTypeId={typeId}  // 新 prop——下一 step 在 AssetFormFields 加
    />
  );
}
```

- [ ] **Step 3: 改 AssetFormFields 接受 forceTypeId 兜底**

`frontend/src/features/assets/form/asset-form-fields.tsx`（修改）：

```tsx
interface AssetFormFieldsProps {
  control: Control;
  types: AssetTypeRead[];
  mode: 'create' | 'edit';
  assetCode?: string;
  /** 编辑模式下用 prop 传 type_id，绕过 useWatch（因为 type_id 不在 form values 中） */
  forceTypeId?: string;
}

export function AssetFormFields({ control, types, mode, assetCode, forceTypeId }: AssetFormFieldsProps) {
  const watchedTypeId = useWatch({ control, name: 'type_id' });
  const effectiveTypeId = mode === 'edit' ? forceTypeId : watchedTypeId;
  const selectedType = useMemo(
    () => types.find((t) => t.id === effectiveTypeId),
    [types, effectiveTypeId],
  );
  const fieldDefs = (selectedType?.custom_fields ?? []) as FieldDef[];
  // ... 其余不变
  // 但 GeneralFieldsForm 在 mode=edit 下不应该读 type_id field（不在 form 中）；
  // 改为传 currentTypeName 显示用：
  return (
    <div className="space-y-10">
      <section className="space-y-4">
        <h2 className="...">基础信息</h2>
        <GeneralFieldsForm
          control={control}
          types={types}
          typeReadonly={mode === 'edit'}
          assetCode={assetCode}
          forceTypeName={mode === 'edit' ? selectedType?.name : undefined}
        />
      </section>
      {selectedType && (
        <CustomFieldsForm control={control} fieldDefs={fieldDefs} typeName={selectedType.name} />
      )}
    </div>
  );
}
```

> 同步 `GeneralFieldsForm` 接受 `forceTypeName` prop：编辑模式下 type 字段渲染为只读 Input 显示 `forceTypeName`，不走 RHF Controller（因为 type_id 不在 form values 中）。

- [ ] **Step 4: 写路由**

`frontend/src/routes/assets.$id.edit.tsx`（新建）：

```tsx
import { createFileRoute } from '@tanstack/react-router';
import { AssetEditForm } from '@/features/assets/form/asset-edit-form';
import { parseUuid } from '@/lib/uuid';

export const Route = createFileRoute('/assets/$id/edit')({
  parseParams: ({ id }) => ({ id: parseUuid(id) }),
  component: AssetEditForm,
});
```

- [ ] **Step 5: build + lint + 烟测**

```bash
pnpm --dir frontend build && pnpm --dir frontend lint
```

浏览器：进入某 asset 详情 → 点 ⋯ 菜单"编辑"（菜单项已在 Task 13 接通） → 跳 `/assets/<id>/edit`；type 字段 disabled 显示当前类型；asset_code 只读 mono；改 holder 提交 → 跳回详情 + Toast "更新成功"。

- [ ] **Step 6: commit**

```bash
git add frontend/src/features/assets/form/asset-edit-form.tsx frontend/src/features/assets/form/asset-form-fields.tsx frontend/src/features/assets/form/general-fields-form.tsx frontend/src/features/assets/form/build-edit-schema.ts frontend/src/routes/assets.$id.edit.tsx
git commit -m "feat(form): AssetEditForm + /assets/:id/edit 路由 + type disabled + asset_code 只读"
```

**§3.5 约束引用：** §3.5.1 / §3.5.2（asset_code 只读 font-code muted bg）/ §3.5.3（保存按钮 primary，pending "保存中…"）/ §3.5.5（无 stagger）。

---

### Task 20: 详情页 ⋯ 菜单 "编辑" 项接通

详情页 ⋯ 菜单的"编辑"项已在 M2c-2 plan 中预留 disabled 项，本里程碑接通到 `/assets/$id/edit`。

> 这一步等 Task 23 的 `AssetHeader` 大改时一起做（Task 23 重写整个 4 状态 × ⋯ 菜单矩阵）。本 Task 在 Task 23 中合并。本编号保留，仅作占位说明。

跳转到 Task 21。

---

## ✅ Phase 3 完成判定

```bash
pnpm --dir frontend build && pnpm --dir frontend lint && pnpm --dir frontend test
uv run pytest -v
```

Expected: 全绿。`/assets/new` + `/assets/:id/edit` 可用。Vitest field-def-to-zod 11 case 全 PASS。

---

## Phase 4 · 详情页扩展（§14.5 + 删除 + 附件上传）（Task 21-26）

### Task 21: state-change-actions.ts + state-change-alert.tsx + useChangeAssetStatusMutation

**Files:**
- Create: `frontend/src/features/assets/detail/state-change-actions.ts`
- Create: `frontend/src/features/assets/detail/state-change-alert.tsx`
- Modify: `frontend/src/api/hooks/assets.ts`（加 useChangeAssetStatusMutation）
- Test: `frontend/tests/unit/state-change-actions.test.ts`（snapshot test 文案渲染）

- [ ] **Step 1: 写 state-change-actions 元数据**

`frontend/src/features/assets/detail/state-change-actions.ts`：

```ts
import type { components } from '@/api/generated/schema';

type AssetStatus = components['schemas']['AssetStatus'];
type AssetRead = components['schemas']['AssetRead'];

export type StateChangeKey = 'send_to_maintenance' | 'return_from_maintenance' | 'retire' | 'reactivate';

export interface StateChangeAction {
  fromStatuses: AssetStatus[];
  toStatus: AssetStatus;
  verb: string;
  inProgressVerb: string;
  /** 是否需要 AlertDialog 二次确认 */
  needsConfirm: boolean;
  /** 仅 needsConfirm=true 用 */
  confirmTitle?: string;
  confirmBody?: (a: AssetRead) => string;
  confirmAction?: string;
}

export const STATE_CHANGE_ACTIONS: Record<StateChangeKey, StateChangeAction> = {
  send_to_maintenance: {
    fromStatuses: ['IDLE'],
    toStatus: 'MAINTENANCE',
    verb: '送修',
    inProgressVerb: '送修中…',
    needsConfirm: false,
  },
  return_from_maintenance: {
    fromStatuses: ['MAINTENANCE'],
    toStatus: 'IDLE',
    verb: '修好回库',
    inProgressVerb: '回库中…',
    needsConfirm: false,
  },
  retire: {
    fromStatuses: ['IDLE', 'MAINTENANCE'],
    toStatus: 'RETIRED',
    verb: '退役',
    inProgressVerb: '退役中…',
    needsConfirm: true,
    confirmTitle: '退役这台资产？',
    confirmBody: (a) => `${a.name} · ${a.asset_code} 将标记为退役。退役后默认仍在列表中显示，可通过「重新启用」复活。`,
    confirmAction: '确认退役',
  },
  reactivate: {
    fromStatuses: ['RETIRED'],
    toStatus: 'IDLE',
    verb: '重新启用',
    inProgressVerb: '启用中…',
    needsConfirm: true,
    confirmTitle: '重新启用这台资产？',
    confirmBody: (a) => `${a.name} · ${a.asset_code} 将从退役状态恢复为闲置。`,
    confirmAction: '确认启用',
  },
};

/** 给定当前 status，返回菜单中应显示的所有 state change keys（顺序固定）。 */
export function availableStateChanges(status: AssetStatus): StateChangeKey[] {
  return (Object.entries(STATE_CHANGE_ACTIONS) as [StateChangeKey, StateChangeAction][])
    .filter(([, action]) => action.fromStatuses.includes(status))
    .map(([key]) => key);
}
```

- [ ] **Step 2: 写 useChangeAssetStatusMutation**

`frontend/src/api/hooks/assets.ts`（追加）：

```ts
export function useChangeAssetStatusMutation(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (toStatus: components["schemas"]["AssetStatus"]) => {
      const res = await http.PATCH("/api/assets/{asset_id}", {
        params: { path: { asset_id: id } },
        body: { status: toStatus },
      });
      return unwrap(res);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.assets.all });
      qc.invalidateQueries({ queryKey: qk.assets.detail(id) });
      qc.invalidateQueries({ queryKey: qk.assets.history(id) });
    },
    // toast 由调用方控制（Task 23 AssetHeader 接 STATE_CHANGE_ACTIONS 文案）
  });
}
```

- [ ] **Step 3: 写 StateChangeAlert 通用组件**

`frontend/src/features/assets/detail/state-change-alert.tsx`：

```tsx
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { toast } from 'sonner';
import { useChangeAssetStatusMutation } from '@/api/hooks/assets';
import { STATE_CHANGE_ACTIONS, type StateChangeKey } from './state-change-actions';
import { toFriendlyMessage } from '@/lib/error';
import type { components } from '@/api/generated/schema';

type AssetRead = components['schemas']['AssetRead'];

interface StateChangeAlertProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  asset: AssetRead;
  actionKey: StateChangeKey;
}

export function StateChangeAlert({ open, onOpenChange, asset, actionKey }: StateChangeAlertProps) {
  const action = STATE_CHANGE_ACTIONS[actionKey];
  const mutation = useChangeAssetStatusMutation(asset.id);

  async function confirm() {
    try {
      await mutation.mutateAsync(action.toStatus);
      toast.success(`${action.verb}成功`);
      onOpenChange(false);
    } catch (err) {
      toast.error(toFriendlyMessage(err));
    }
  }

  if (!action.needsConfirm) return null;

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{action.confirmTitle}</AlertDialogTitle>
          <AlertDialogDescription>
            {action.confirmBody?.(asset)}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={mutation.isPending}>取消</AlertDialogCancel>
          <AlertDialogAction
            onClick={confirm}
            disabled={mutation.isPending}
          >
            {mutation.isPending ? action.inProgressVerb : (action.confirmAction ?? '确认')}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
```

- [ ] **Step 4: 写 state-change-actions 单测（snapshot 文案）**

`frontend/tests/unit/state-change-actions.test.ts`：

```ts
import { describe, expect, it } from 'vitest';
import { STATE_CHANGE_ACTIONS, availableStateChanges } from '@/features/assets/detail/state-change-actions';

describe('STATE_CHANGE_ACTIONS', () => {
  it('IDLE allows send_to_maintenance + retire', () => {
    expect(availableStateChanges('IDLE')).toEqual(['send_to_maintenance', 'retire']);
  });
  it('IN_USE allows nothing (must return first)', () => {
    expect(availableStateChanges('IN_USE')).toEqual([]);
  });
  it('MAINTENANCE allows return_from_maintenance + retire', () => {
    expect(availableStateChanges('MAINTENANCE')).toEqual(['return_from_maintenance', 'retire']);
  });
  it('RETIRED allows reactivate', () => {
    expect(availableStateChanges('RETIRED')).toEqual(['reactivate']);
  });

  it('retire confirmBody includes asset name + code', () => {
    const asset = { name: 'X1', asset_code: 'NB-007' } as never;
    expect(STATE_CHANGE_ACTIONS.retire.confirmBody!(asset)).toContain('X1');
    expect(STATE_CHANGE_ACTIONS.retire.confirmBody!(asset)).toContain('NB-007');
  });

  it('only retire/reactivate need confirmation', () => {
    expect(STATE_CHANGE_ACTIONS.send_to_maintenance.needsConfirm).toBe(false);
    expect(STATE_CHANGE_ACTIONS.return_from_maintenance.needsConfirm).toBe(false);
    expect(STATE_CHANGE_ACTIONS.retire.needsConfirm).toBe(true);
    expect(STATE_CHANGE_ACTIONS.reactivate.needsConfirm).toBe(true);
  });
});
```

- [ ] **Step 5: 跑测 + build**

```bash
pnpm --dir frontend test -- state-change-actions
pnpm --dir frontend build
```

Expected: 6 case 全 PASS。

- [ ] **Step 6: lint + commit**

```bash
pnpm --dir frontend lint
git add frontend/src/features/assets/detail/state-change-actions.ts frontend/src/features/assets/detail/state-change-alert.tsx frontend/src/api/hooks/assets.ts frontend/tests/unit/state-change-actions.test.ts
git commit -m "feat(state-change): STATE_CHANGE_ACTIONS 元数据 + StateChangeAlert + useChangeAssetStatusMutation hook + 6 case 测试"
```

**§3.5 约束引用：** §3.5.5（mutation pending 文字切）；§3.5.6（AlertDialog overlay 不 blur，不用 destructive scale）。

---

### Task 22: DeleteAssetAlert（详情页 + 列表页共用）

**Files:**
- Create: `frontend/src/features/assets/detail/delete-asset-alert.tsx`
- Modify: `frontend/src/api/hooks/assets.ts`（确认 useDeleteAsset 已支持 success callback；现有 useDeleteAsset 已含 toast）
- Modify: `frontend/src/routes/index.tsx`（接通 onDelete prop → 弹 DeleteAssetAlert）

- [ ] **Step 1: 写 DeleteAssetAlert**

`frontend/src/features/assets/detail/delete-asset-alert.tsx`：

```tsx
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { toast } from 'sonner';
import { useDeleteAsset } from '@/api/hooks/assets';
import { toFriendlyMessage } from '@/lib/error';
import { TOAST, PENDING_TEXT } from '@/features/assets/form/form-toast';

interface DeleteAssetAlertProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  asset: { id: string; name: string; asset_code: string };
  /** 删除成功后回调，调用方决定是否 navigate */
  onDeleted?: () => void;
}

export function DeleteAssetAlert({ open, onOpenChange, asset, onDeleted }: DeleteAssetAlertProps) {
  const mutation = useDeleteAsset();

  async function confirm() {
    try {
      await mutation.mutateAsync(asset.id);
      toast.success(TOAST.DELETE_SUCCESS);
      onOpenChange(false);
      onDeleted?.();
    } catch (err) {
      toast.error(toFriendlyMessage(err));
    }
  }

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>确认删除？</AlertDialogTitle>
          <AlertDialogDescription className="space-y-2">
            <span className="block">
              <strong>{asset.name}</strong> · <span className="font-code">{asset.asset_code}</span> 将被永久删除，
              所有关联的派发记录、附件元数据也会清空。
            </span>
            <span className="block text-destructive font-medium">此操作不可撤销。</span>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={mutation.isPending}>取消</AlertDialogCancel>
          <AlertDialogAction
            onClick={confirm}
            disabled={mutation.isPending}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          >
            {mutation.isPending ? PENDING_TEXT.DELETE : '确认删除'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
```

> 注意：M2c-1 的 `useDeleteAsset` hook 已自带 toast.success，本 step 的 Alert 又叫了一次 toast。两者会重复——把 hook 中的 toast 移除，由调用方（Alert / 详情页）控制 toast。

- [ ] **Step 2: 改 useDeleteAsset hook 移除 toast，改由调用方控制**

`frontend/src/api/hooks/assets.ts` 中 `useDeleteAsset`：

```ts
export function useDeleteAsset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const res = await http.DELETE("/api/assets/{asset_id}", {
        params: { path: { asset_id: id } },
      });
      return unwrap(res);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.assets.all });
      // toast 由调用方（DeleteAssetAlert）控制——避免重复 + 允许调用方做 navigate
    },
    onError: (err) => toast.error(toFriendlyMessage(err)),
  });
}
```

- [ ] **Step 3: 改 routes/index.tsx 接通 onDelete**

`frontend/src/routes/index.tsx`（增加 state + 渲染 DeleteAssetAlert）：

```tsx
import { useState } from 'react';
import { DeleteAssetAlert } from '@/features/assets/detail/delete-asset-alert';
// ... existing imports

function IndexPage() {
  // ... existing state
  const [deleteRow, setDeleteRow] = useState<AssetRow | null>(null);

  return (
    <>
      {/* ... existing toolbar / table */}
      <AssetsTable
        rows={rows}
        // ... existing props
        onDelete={(row) => setDeleteRow(row)}
      />

      {deleteRow && (
        <DeleteAssetAlert
          open
          onOpenChange={(o) => !o && setDeleteRow(null)}
          asset={{ id: deleteRow.id, name: deleteRow.name, asset_code: deleteRow.asset_code }}
        />
      )}
    </>
  );
}
```

- [ ] **Step 4: build + lint + 烟测**

```bash
pnpm --dir frontend build && pnpm --dir frontend lint
```

浏览器：列表 ⋯ 菜单 → 删除… → AlertDialog 显示 → 确认 → 列表刷新（被删除条消失）+ Toast。

- [ ] **Step 5: commit**

```bash
git add frontend/src/features/assets/detail/delete-asset-alert.tsx frontend/src/api/hooks/assets.ts frontend/src/routes/index.tsx
git commit -m "feat(delete): DeleteAssetAlert（详情页 + 列表页共用）+ AlertDialog 二次确认 + useDeleteAsset 移除内置 toast"
```

**§3.5 约束引用：** §3.5.6（destructive 按钮无 hover scale；AlertDialog overlay bg-black/50 不 blur）；§3.5.1（无输入名称等高摩擦元素，文本 inline 即可）。

---

### Task 23: AssetHeader 重写 · 4 状态 × CTA + ⋯ 菜单矩阵

**Files:**
- Modify: `frontend/src/features/assets/detail/asset-header.tsx`
- Modify: `frontend/src/features/assets/detail/asset-detail-page.tsx`（接通 onCheckout/onReturn/onChangeStatus/onDelete state）

- [ ] **Step 1: 重写 AssetHeader**

`frontend/src/features/assets/detail/asset-header.tsx`（替换为）：

```tsx
import { Link } from "@tanstack/react-router";
import { MoreHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuTrigger, DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import {
  Tooltip, TooltipContent, TooltipProvider, TooltipTrigger,
} from "@/components/ui/tooltip";
import { formatDateTime } from "@/lib/date";
import { StatusBadge } from "@/components/status/status-badge";
import type { components } from "@/api/generated/schema";
import { CHECKOUT_VERB, RETURN_VERB } from "./checkout-actions";
import { STATE_CHANGE_ACTIONS, availableStateChanges, type StateChangeKey } from "./state-change-actions";

type AssetRead = components["schemas"]["AssetRead"];
type CheckoutRead = components["schemas"]["CheckoutRead"];

interface AssetHeaderProps {
  asset: AssetRead;
  currentCheckout: CheckoutRead | null;
  onCheckout: () => void;
  onReturn: () => void;
  onChangeStatus: (key: StateChangeKey) => void;
  onDelete: () => void;
}

export function AssetHeader({
  asset, currentCheckout, onCheckout, onReturn, onChangeStatus, onDelete,
}: AssetHeaderProps) {
  return (
    <header className="flex items-start justify-between gap-4">
      <div className="space-y-1">
        <Link
          to="/"
          search={{ page: 1, pageSize: 50 }}
          className="text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          ← 返回列表
        </Link>
        <h1 className="text-2xl font-semibold">{asset.name}</h1>
        <div className="flex items-center gap-3">
          <span className="font-code text-sm text-muted-foreground">{asset.asset_code}</span>
          <span className="text-sm text-muted-foreground">·</span>
          <span className="text-sm text-muted-foreground">{asset.type_name ?? "未知类型"}</span>
          <StatusBadge status={asset.status} />
        </div>
        {asset.status === "IN_USE" && currentCheckout && (
          <p className="text-sm text-muted-foreground">
            当前派发给 ·{" "}
            <span className="text-foreground">{currentCheckout.holder}</span>
            {currentCheckout.location ? <> · {currentCheckout.location}</> : null}
            {" · 自 "}
            <time className="font-code">{formatDateTime(currentCheckout.checked_out_at)}</time>
          </p>
        )}
      </div>
      <ActionArea
        asset={asset}
        onCheckout={onCheckout}
        onReturn={onReturn}
        onChangeStatus={onChangeStatus}
        onDelete={onDelete}
      />
    </header>
  );
}

function ActionArea({
  asset, onCheckout, onReturn, onChangeStatus, onDelete,
}: {
  asset: AssetRead;
  onCheckout: () => void;
  onReturn: () => void;
  onChangeStatus: (key: StateChangeKey) => void;
  onDelete: () => void;
}) {
  const status = asset.status;
  const stateChanges = availableStateChanges(status);

  return (
    <div className="flex items-center gap-2">
      {/* 主按钮：按状态决定 */}
      {status === "IDLE" && <Button onClick={onCheckout}>{CHECKOUT_VERB}</Button>}
      {status === "IN_USE" && <Button onClick={onReturn}>{RETURN_VERB}</Button>}
      {status === "MAINTENANCE" && (
        <Button onClick={() => onChangeStatus("return_from_maintenance")} className="bg-emerald-600 hover:bg-emerald-700">
          {STATE_CHANGE_ACTIONS.return_from_maintenance.verb}
        </Button>
      )}
      {status === "RETIRED" && (
        <Button onClick={() => onChangeStatus("reactivate")} variant="outline">
          {STATE_CHANGE_ACTIONS.reactivate.verb}
        </Button>
      )}

      {/* 次按钮：仅 IDLE 显示"送修" */}
      {status === "IDLE" && (
        <Button variant="outline" onClick={() => onChangeStatus("send_to_maintenance")}>
          {STATE_CHANGE_ACTIONS.send_to_maintenance.verb}
        </Button>
      )}

      {/* ⋯ 菜单 */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon" aria-label="更多操作">
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem asChild>
            <Link to="/assets/$id/edit" params={{ id: asset.id }}>编辑</Link>
          </DropdownMenuItem>

          {/* 状态切换中"需确认"的项（IDLE 状态下"退役"在这里；MAINTENANCE 状态下也是"退役"） */}
          {stateChanges.filter((k) => STATE_CHANGE_ACTIONS[k].needsConfirm
            && k !== "reactivate"  // reactivate 已是主按钮（RETIRED 状态）
          ).map((key) => (
            <DropdownMenuItem key={key} onSelect={() => onChangeStatus(key)}>
              {STATE_CHANGE_ACTIONS[key].verb}…
            </DropdownMenuItem>
          ))}

          <DropdownMenuSeparator />

          {status === "IN_USE" ? (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <span tabIndex={0}>
                    <DropdownMenuItem disabled className="text-destructive">删除</DropdownMenuItem>
                  </span>
                </TooltipTrigger>
                <TooltipContent>需先归还</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          ) : (
            <DropdownMenuItem onSelect={onDelete} className="text-destructive focus:text-destructive">
              删除…
            </DropdownMenuItem>
          )}
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
```

- [ ] **Step 2: 改 asset-detail-page.tsx 接通 state**

`frontend/src/features/assets/detail/asset-detail-page.tsx`（修改 dialog state）：

```tsx
import { useState } from 'react';
import { StateChangeAlert } from './state-change-alert';
import { DeleteAssetAlert } from './delete-asset-alert';
import { STATE_CHANGE_ACTIONS, type StateChangeKey } from './state-change-actions';
import { useNavigate } from '@tanstack/react-router';
import { toast } from 'sonner';
import { useChangeAssetStatusMutation } from '@/api/hooks/assets';

// 在 AssetDetailPage 组件内：
const navigate = useNavigate({ from: '/assets/$id' });
const [checkoutOpen, setCheckoutOpen] = useState(false);
const [returnOpen, setReturnOpen] = useState(false);
const [stateChangeKey, setStateChangeKey] = useState<StateChangeKey | null>(null);
const [deleteOpen, setDeleteOpen] = useState(false);

const changeStatusMutation = useChangeAssetStatusMutation(asset.id);

async function handleStateChange(key: StateChangeKey) {
  const action = STATE_CHANGE_ACTIONS[key];
  if (action.needsConfirm) {
    setStateChangeKey(key);  // 弹 AlertDialog
  } else {
    // 轻量动作（送修 / 修好回库），不弹 dialog 直接调
    try {
      await changeStatusMutation.mutateAsync(action.toStatus);
      toast.success(`${action.verb}成功`);
    } catch (err) {
      toast.error(toFriendlyMessage(err));
    }
  }
}

// JSX：
<AssetHeader
  asset={asset}
  currentCheckout={currentCheckout}
  onCheckout={() => setCheckoutOpen(true)}
  onReturn={() => setReturnOpen(true)}
  onChangeStatus={handleStateChange}
  onDelete={() => setDeleteOpen(true)}
/>

{/* ... existing CheckoutDialog / ReturnDialog */}

{stateChangeKey && (
  <StateChangeAlert
    open
    onOpenChange={(o) => !o && setStateChangeKey(null)}
    asset={asset}
    actionKey={stateChangeKey}
  />
)}

<DeleteAssetAlert
  open={deleteOpen}
  onOpenChange={setDeleteOpen}
  asset={{ id: asset.id, name: asset.name, asset_code: asset.asset_code }}
  onDeleted={() => navigate({ to: '/' })}
/>
```

- [ ] **Step 3: build + lint + 烟测**

```bash
pnpm --dir frontend build && pnpm --dir frontend lint
```

浏览器烟测（每个状态都试）：
- IDLE 详情页：主按钮"派发" + 次按钮"送修" + ⋯ 菜单含"编辑 / 退役… / [---] / 删除…"
- 点"送修" → 状态变 MAINTENANCE，主按钮变"修好回库"
- 点"退役…" → AlertDialog 出现
- IN_USE 详情页：主按钮"归还"，⋯ 菜单"删除"灰禁 + tooltip
- MAINTENANCE 详情页：主按钮"修好回库"绿色，⋯ 菜单含"退役…"
- RETIRED 详情页：主按钮"重新启用" outline，⋯ 菜单不含状态切换

- [ ] **Step 4: commit**

```bash
git add frontend/src/features/assets/detail/asset-header.tsx frontend/src/features/assets/detail/asset-detail-page.tsx
git commit -m "feat(state-change): AssetHeader 重写 · 4 状态 × 主按钮 + 次按钮 + ⋯ 菜单矩阵 + 接通状态切换 / 删除 dialog"
```

**§3.5 约束引用：** §3.5.3（IDLE→primary、MAINTENANCE→success 绿、RETIRED→muted outline）；§3.5.5（按钮 hover 色变 200ms，主按钮无 transform scale）；§3.5.6（红线 0 命中——禁 spinner / blur / scale-）；§3.5.7（DropdownMenu / Tooltip 已审 variant）。

---

### Task 24: lib/upload-progress.ts XHR helper + Vitest

**Files:**
- Create: `frontend/src/lib/upload-progress.ts`
- Test: `frontend/tests/unit/upload-progress.test.ts`

- [ ] **Step 1: 写测试**

`frontend/tests/unit/upload-progress.test.ts`：

```ts
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { uploadWithProgress } from '@/lib/upload-progress';

describe('uploadWithProgress', () => {
  let xhrMock: any;

  beforeEach(() => {
    xhrMock = {
      open: vi.fn(),
      send: vi.fn(),
      setRequestHeader: vi.fn(),
      upload: { addEventListener: vi.fn() },
      addEventListener: vi.fn(),
      readyState: 0,
      status: 0,
      responseText: '',
    };
    vi.stubGlobal('XMLHttpRequest', vi.fn(() => xhrMock));
  });

  it('resolves with parsed JSON on success', async () => {
    const formData = new FormData();
    const onProgress = vi.fn();
    const promise = uploadWithProgress<{ id: string }>('/api/x', formData, onProgress);

    // 模拟 progress event
    const progressHandler = xhrMock.upload.addEventListener.mock.calls.find(
      (c: any) => c[0] === 'progress',
    )[1];
    progressHandler({ lengthComputable: true, loaded: 50, total: 100 });
    expect(onProgress).toHaveBeenCalledWith(50);

    // 模拟 load event
    const loadHandler = xhrMock.addEventListener.mock.calls.find((c: any) => c[0] === 'load')[1];
    xhrMock.status = 201;
    xhrMock.responseText = '{"id":"abc"}';
    loadHandler({});

    await expect(promise).resolves.toEqual({ id: 'abc' });
  });

  it('rejects on HTTP error status', async () => {
    const promise = uploadWithProgress('/api/x', new FormData());
    const loadHandler = xhrMock.addEventListener.mock.calls.find((c: any) => c[0] === 'load')[1];
    xhrMock.status = 422;
    xhrMock.responseText = '{"detail":"too large"}';
    loadHandler({});
    await expect(promise).rejects.toMatchObject({ status: 422, detail: 'too large' });
  });

  it('rejects on network error', async () => {
    const promise = uploadWithProgress('/api/x', new FormData());
    const errorHandler = xhrMock.addEventListener.mock.calls.find((c: any) => c[0] === 'error')[1];
    errorHandler({});
    await expect(promise).rejects.toThrow(/网络错误/);
  });
});
```

- [ ] **Step 2: 跑测验证 FAIL**

```bash
pnpm --dir frontend test -- upload-progress
```

Expected: FAIL（模块不存在）。

- [ ] **Step 3: 实现**

`frontend/src/lib/upload-progress.ts`：

```ts
/**
 * XHR 封装，支持 upload progress 事件（fetch 不支持）。
 *
 * @param url - 目标 URL
 * @param formData - multipart/form-data body
 * @param onProgress - progress 回调，传入 0-100 整数百分比
 * @returns 解析后的 JSON body（成功 2xx）；失败抛 { status, detail } 形态错误
 */
export interface UploadError {
  status: number;
  detail: string;
}

export function uploadWithProgress<T>(
  url: string,
  formData: FormData,
  onProgress?: (percent: number) => void,
): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', url);

    if (onProgress) {
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
          const percent = Math.round((e.loaded / e.total) * 100);
          onProgress(percent);
        }
      });
    }

    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText) as T);
        } catch {
          resolve(xhr.responseText as unknown as T);
        }
      } else {
        let detail = 'unknown';
        try {
          detail = JSON.parse(xhr.responseText).detail ?? xhr.responseText;
        } catch {
          detail = xhr.responseText || `HTTP ${xhr.status}`;
        }
        const err: UploadError = { status: xhr.status, detail };
        reject(err);
      }
    });

    xhr.addEventListener('error', () => {
      reject(new Error('网络错误：上传失败'));
    });

    xhr.send(formData);
  });
}
```

- [ ] **Step 4: 跑测 PASS**

```bash
pnpm --dir frontend test -- upload-progress
```

Expected: 3 case PASS。

- [ ] **Step 5: commit**

```bash
git add frontend/src/lib/upload-progress.ts frontend/tests/unit/upload-progress.test.ts
git commit -m "feat(upload): XHR helper 封装 upload progress event + 3 case 测试"
```

---

### Task 25: useUploadAttachmentMutation + AttachmentAddSlot

**Files:**
- Modify: `frontend/src/api/hooks/attachments.ts`（加 useUploadAttachmentMutation）
- Create: `frontend/src/features/assets/detail/attachment-add-slot.tsx`

- [ ] **Step 1: 写 useUploadAttachmentMutation**

`frontend/src/api/hooks/attachments.ts`（追加）：

```ts
import { uploadWithProgress } from '@/lib/upload-progress';

export interface UploadProgressState {
  fileId: string;
  fileName: string;
  percent: number;
  error?: string;
}

export function useUploadAttachmentMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (args: {
      assetId: string;
      file: File;
      onProgress?: (percent: number) => void;
    }) => {
      const fd = new FormData();
      fd.append('file', args.file);
      // 让后端默认 kind=OTHER；M2c-3 不让用户选 kind（detail 页可后续改 metadata）
      return await uploadWithProgress<components['schemas']['AttachmentRead']>(
        `/api/assets/${args.assetId}/attachments`,
        fd,
        args.onProgress,
      );
    },
    onSuccess: (_data, { assetId }) => {
      qc.invalidateQueries({ queryKey: qk.attachments.byAsset(assetId) });
    },
  });
}
```

- [ ] **Step 2: 写 AttachmentAddSlot**

`frontend/src/features/assets/detail/attachment-add-slot.tsx`：

```tsx
import { useRef, useState } from 'react';
import { Plus, AlertCircle, RotateCw, X } from 'lucide-react';
import { toast } from 'sonner';
import { useUploadAttachmentMutation } from '@/api/hooks/attachments';
import { TOAST } from '@/features/assets/form/form-toast';
import { cn } from '@/lib/utils';

const MAX_SIZE_BYTES = 10 * 1024 * 1024; // 10MB

interface PendingFile {
  /** 临时本地 id（用于 React key） */
  localId: string;
  file: File;
  percent: number;
  error?: string;
}

interface AttachmentAddSlotProps {
  assetId: string;
}

export function AttachmentAddSlot({ assetId }: AttachmentAddSlotProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [pending, setPending] = useState<PendingFile[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const mutation = useUploadAttachmentMutation();

  function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    const accepted: PendingFile[] = [];
    for (const file of Array.from(files)) {
      if (file.size > MAX_SIZE_BYTES) {
        toast.error(`${file.name}: ${TOAST.FILE_TOO_LARGE}`);
        continue;
      }
      accepted.push({
        localId: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
        file,
        percent: 0,
      });
    }
    setPending((p) => [...p, ...accepted]);
    accepted.forEach((pf) => uploadOne(pf));
  }

  async function uploadOne(pf: PendingFile) {
    try {
      await mutation.mutateAsync({
        assetId,
        file: pf.file,
        onProgress: (percent) => {
          setPending((cur) => cur.map((p) => (p.localId === pf.localId ? { ...p, percent } : p)));
        },
      });
      // 成功 → 从 pending 列表移除（attachment query 自动 invalidate 后会出现在 grid）
      setPending((cur) => cur.filter((p) => p.localId !== pf.localId));
      toast.success(TOAST.UPLOAD_SUCCESS);
    } catch (err: unknown) {
      const detail = (err as { detail?: string }).detail ?? '上传失败';
      setPending((cur) => cur.map((p) => (p.localId === pf.localId ? { ...p, error: detail } : p)));
    }
  }

  function retry(localId: string) {
    const pf = pending.find((p) => p.localId === localId);
    if (!pf) return;
    setPending((cur) => cur.map((p) => (p.localId === localId ? { ...p, error: undefined, percent: 0 } : p)));
    uploadOne(pf);
  }

  function dismiss(localId: string) {
    setPending((cur) => cur.filter((p) => p.localId !== localId));
  }

  return (
    <>
      {/* 上传中 / 失败 tile */}
      {pending.map((pf) => (
        <div
          key={pf.localId}
          className={cn(
            'aspect-square rounded-md ring-1 flex flex-col p-3',
            pf.error ? 'ring-destructive bg-destructive/5' : 'ring-border bg-muted/30',
          )}
        >
          <div className="flex justify-between gap-2">
            <span className="line-clamp-2 text-xs">{pf.file.name}</span>
            <button
              type="button"
              onClick={() => dismiss(pf.localId)}
              className="text-muted-foreground hover:text-foreground"
              aria-label="取消"
            >
              <X className="h-3 w-3" />
            </button>
          </div>
          <div className="mt-auto">
            {pf.error ? (
              <button
                type="button"
                onClick={() => retry(pf.localId)}
                className="flex items-center gap-1 text-xs text-destructive cursor-pointer"
                aria-label="重试上传"
              >
                <AlertCircle className="h-3 w-3" />
                <span>{pf.error}</span>
                <RotateCw className="ml-auto h-3 w-3" />
              </button>
            ) : (
              <>
                <div className="text-xs text-muted-foreground mb-1">{pf.percent}%</div>
                <div className="h-1 bg-secondary rounded">
                  <div
                    className="h-full bg-primary rounded transition-[width] duration-150 ease-out"
                    style={{ width: `${pf.percent}%` }}
                  />
                </div>
              </>
            )}
          </div>
        </div>
      ))}

      {/* add slot */}
      <button
        type="button"
        onClick={() => fileInputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
        onDragLeave={() => setDragActive(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragActive(false);
          handleFiles(e.dataTransfer.files);
        }}
        className={cn(
          'aspect-square rounded-md border-[1.5px] border-dashed flex flex-col items-center justify-center gap-1 cursor-pointer transition-colors',
          dragActive
            ? 'border-primary bg-primary/5 text-primary'
            : 'border-muted-foreground/40 text-muted-foreground hover:border-primary hover:text-primary hover:bg-primary/5',
        )}
        aria-label="添加附件"
      >
        <Plus className="h-6 w-6" />
        <span className="text-xs">添加附件</span>
      </button>

      <input
        ref={fileInputRef}
        type="file"
        multiple
        className="hidden"
        accept="image/*,application/pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.md"
        onChange={(e) => {
          handleFiles(e.target.files);
          e.target.value = '';  // 让同一文件可重复选择
        }}
      />
    </>
  );
}
```

- [ ] **Step 3: build + lint**

```bash
pnpm --dir frontend build && pnpm --dir frontend lint
```

- [ ] **Step 4: §3.5 红线扫描**

```bash
grep -nE 'scale-|animate-spin|backdrop-blur|bg-gradient' frontend/src/features/assets/detail/attachment-add-slot.tsx
```

Expected: 0 命中（progress 用 width transition，不是 spinner）。

- [ ] **Step 5: commit**

```bash
git add frontend/src/api/hooks/attachments.ts frontend/src/features/assets/detail/attachment-add-slot.tsx
git commit -m "feat(upload): useUploadAttachmentMutation（XHR + progress）+ AttachmentAddSlot（拖拽 + 多文件 + 失败重试）"
```

**§3.5 约束引用：** §3.5.1 fewer-but-better（与 grid tile 同框）；§3.5.5（hover 色变 transition-colors，进度条 width transition）；§3.5.6（红线 0：禁 spinner / scale）；移动端响应式（grid 列数自然降级，已在 attachment-grid 实现）。

---

### Task 26: AttachmentSection 整合 add slot 到 grid

**Files:**
- Modify: `frontend/src/features/assets/detail/attachment-grid.tsx`

- [ ] **Step 1: 改 AttachmentGrid 接受 assetId + 在 grid 末尾渲染 AddSlot**

`frontend/src/features/assets/detail/attachment-grid.tsx`（修改）：

```tsx
import { AttachmentAddSlot } from './attachment-add-slot';

interface AttachmentGridProps {
  query: UseQueryResult<AttachmentRead[]>;
  onOpen: (att: AttachmentRead) => void;
  assetId: string;  // 新——传给 AddSlot
}

export function AttachmentGrid({ query, onOpen, assetId }: AttachmentGridProps) {
  return (
    <section>
      <h2 className="mb-3 text-lg font-medium">
        附件 {query.data && <span className="text-sm font-normal text-muted-foreground">{query.data.length}</span>}
      </h2>
      {query.isLoading ? (
        <GridSkeleton />
      ) : query.isError ? (
        <ErrorState error={query.error} onRetry={() => query.refetch()} />
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {(query.data ?? []).map((att) => (
            <AttachmentTile key={att.id} att={att} onOpen={onOpen} />
          ))}
          <AttachmentAddSlot assetId={assetId} />
        </div>
      )}
    </section>
  );
}

// AttachmentTile 抽出（既有 button 块抽成函数，结构不变）：
function AttachmentTile({ att, onOpen }: { att: AttachmentRead; onOpen: (a: AttachmentRead) => void }) {
  return (
    <button
      type="button"
      onClick={() => onOpen(att)}
      className="group relative aspect-square overflow-hidden rounded-md ring-1 ring-border cursor-pointer transition-shadow hover:ring-2 hover:ring-primary/40 focus-visible:ring-2 focus-visible:ring-primary/40"
      aria-label={`查看附件 ${att.original_name}`}
    >
      {att.mime_type.startsWith('image/') ? (
        <img src={`/api/attachments/${att.id}/content`} alt="" loading="lazy" className="h-full w-full object-cover" />
      ) : (
        <div className="flex h-full w-full flex-col items-center justify-center gap-2 bg-muted/30 p-2 text-muted-foreground">
          <KindIcon mime={att.mime_type} />
          <span className="line-clamp-2 text-xs text-center">{att.original_name}</span>
        </div>
      )}
    </button>
  );
}
```

> EmptyState 移除——空附件场景下 AddSlot 已经是引导（`+ 添加附件`），无附件不需要再显示"暂无附件"占位。

- [ ] **Step 2: 改 AssetDetailPage 传 assetId**

详情页内 `<AttachmentGrid query={...} onOpen={...} assetId={asset.id} />`。

- [ ] **Step 3: build + lint + 烟测**

```bash
pnpm --dir frontend build && pnpm --dir frontend lint
```

浏览器：详情页"附件"区 → grid 末尾出现"+ 添加附件"虚线 tile；点击文件选择器 → 选 3 文件 → 同时上传 → 成功后 thumbnail 出现 + 进度 tile 消失。

- [ ] **Step 4: commit**

```bash
git add frontend/src/features/assets/detail/attachment-grid.tsx frontend/src/features/assets/detail/asset-detail-page.tsx
git commit -m "feat(upload): AttachmentGrid 整合 AddSlot（grid 末尾内嵌虚线 tile）+ 移除 EmptyState（add slot 已是引导）"
```

**§3.5 约束引用：** §3.5.1 fewer-but-better（add slot 替代独立 dropzone 区）。

---

## ✅ Phase 4 完成判定

```bash
pnpm --dir frontend build && pnpm --dir frontend lint && pnpm --dir frontend test
```

Expected: 全绿。详情页 4 状态 × CTA 矩阵 + 删除 + 状态切换 + 附件上传全部可用。

---

## Phase 5 · M2c-2 Dialog 迁 RHF（Task 27-28）

### Task 27: CheckoutDialog 从纯 React state 迁到 RHF + Zod + Vitest 试点

**Files:**
- Modify: `frontend/src/features/assets/detail/checkout-dialog.tsx`
- Test: `frontend/tests/hooks/checkout-dialog.test.tsx`

- [ ] **Step 1: 写 Vitest 试点测试（在迁移前先确认行为基线）**

`frontend/tests/hooks/checkout-dialog.test.tsx`：

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import { CheckoutDialog } from '@/features/assets/detail/checkout-dialog';

declare const __mswServer: any;

function renderDialog(props: any = {}) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <CheckoutDialog open onOpenChange={() => {}} assetId="asset-1" {...props} />
    </QueryClientProvider>
  );
}

describe('CheckoutDialog (RHF)', () => {
  beforeEach(() => {
    __mswServer.use(
      http.post('/api/assets/asset-1/checkout', () =>
        HttpResponse.json({ id: 'rec-1', holder: '张三' }, { status: 201 })
      ),
    );
  });

  it('blocks submit when holder empty', async () => {
    const user = userEvent.setup();
    renderDialog();
    await user.click(screen.getByRole('button', { name: /确认派发/ }));
    expect(await screen.findByText(/保管人.*必填/)).toBeInTheDocument();
  });

  it('submits with valid holder', async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    renderDialog({ onOpenChange });
    await user.type(screen.getByLabelText(/保管人/), '张三');
    await user.click(screen.getByRole('button', { name: /确认派发/ }));
    await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false));
  });
});
```

- [ ] **Step 2: 跑测验证 FAIL（旧组件用纯 useState；error message 文案可能不一致）**

```bash
pnpm --dir frontend test -- checkout-dialog
```

Expected: FAIL（"保管人.*必填" 文案是新的，旧实现是 "请填写保管人"）。

- [ ] **Step 3: 迁 CheckoutDialog 到 RHF**

`frontend/src/features/assets/detail/checkout-dialog.tsx`（替换为）：

```tsx
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { InlineErrorBanner } from '@/components/feedback/inline-error-banner';
import { useCheckoutMutation } from '@/api/hooks/checkouts';
import { toFriendlyMessage } from '@/lib/error';
import {
  CHECKOUT_DIALOG_TITLE, CHECKOUT_PENDING_TEXT, CHECKOUT_VERB,
} from './checkout-actions';

const schema = z.object({
  holder: z.string().min(1, '保管人必填'),
  location: z.string().optional(),
  note: z.string().optional(),
});
type Values = z.infer<typeof schema>;

interface CheckoutDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  assetId: string;
}

export function CheckoutDialog({ open, onOpenChange, assetId }: CheckoutDialogProps) {
  const mutation = useCheckoutMutation();
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { holder: '', location: '', note: '' },
    mode: 'onSubmit',
  });

  function handleOpenChange(v: boolean) {
    if (mutation.isPending) return;
    if (!v) form.reset();
    onOpenChange(v);
  }

  async function onSubmit(values: Values) {
    try {
      await mutation.mutateAsync({
        assetId,
        body: {
          holder: values.holder.trim(),
          location: values.location?.trim() || null,
          note: values.note?.trim() || null,
        },
      });
      form.reset();
      onOpenChange(false);
    } catch (err) {
      form.setError('root', { message: toFriendlyMessage(err) });
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{CHECKOUT_DIALOG_TITLE}</DialogTitle>
          <DialogDescription>填写保管人后确认，派发记录会自动写入流转历史。</DialogDescription>
        </DialogHeader>

        {form.formState.errors.root && (
          <InlineErrorBanner message={String(form.formState.errors.root.message)} />
        )}

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="holder"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>保管人 <span className="text-destructive">*</span></FormLabel>
                  <FormControl>
                    <Input {...field} disabled={mutation.isPending} autoFocus />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="location"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>位置</FormLabel>
                  <FormControl><Input {...field} disabled={mutation.isPending} /></FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="note"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>备注</FormLabel>
                  <FormControl><Textarea {...field} disabled={mutation.isPending} rows={3} /></FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button
                type="button"
                variant="ghost"
                onClick={() => handleOpenChange(false)}
                disabled={mutation.isPending}
              >
                取消
              </Button>
              <Button type="submit" disabled={mutation.isPending}>
                {mutation.isPending ? CHECKOUT_PENDING_TEXT : `确认${CHECKOUT_VERB}`}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
```

- [ ] **Step 4: 跑测 PASS**

```bash
pnpm --dir frontend test -- checkout-dialog
```

Expected: 2 case PASS。

- [ ] **Step 5: 浏览器烟测验证 UX 行为前后一致**

进 IN_USE 资产详情页 → 点派发 dialog → holder 留空提交看到 "保管人必填" → 填上 → 提交 → dialog 关闭 + Toast。

- [ ] **Step 6: commit**

```bash
git add frontend/src/features/assets/detail/checkout-dialog.tsx frontend/tests/hooks/checkout-dialog.test.tsx
git commit -m "refactor(form): CheckoutDialog 从纯 useState 迁到 RHF + Zod + 2 case Vitest 试点"
```

---

### Task 28: ReturnDialog 迁 RHF

**Files:**
- Modify: `frontend/src/features/assets/detail/return-dialog.tsx`

> 与 Task 27 同款迁移，更简单（仅 1 个 optional 字段 note）。不再写专门 Vitest——CheckoutDialog 试点已确认 RHF + msw 链路通畅。

- [ ] **Step 1: 迁 ReturnDialog**

`frontend/src/features/assets/detail/return-dialog.tsx`（替换为）：

```tsx
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { InlineErrorBanner } from '@/components/feedback/inline-error-banner';
import { useReturnMutation } from '@/api/hooks/checkouts';
import { toFriendlyMessage } from '@/lib/error';
import { formatDateTime } from '@/lib/date';
import {
  RETURN_DIALOG_TITLE, RETURN_PENDING_TEXT, RETURN_VERB,
} from './checkout-actions';
import type { components } from '@/api/generated/schema';

type CheckoutRead = components['schemas']['CheckoutRead'];

const schema = z.object({
  note: z.string().optional(),
});
type Values = z.infer<typeof schema>;

interface ReturnDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  assetId: string;
  currentCheckout: CheckoutRead | null;
}

export function ReturnDialog({ open, onOpenChange, assetId, currentCheckout }: ReturnDialogProps) {
  const mutation = useReturnMutation();
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { note: '' },
    mode: 'onSubmit',
  });

  function handleOpenChange(v: boolean) {
    if (mutation.isPending) return;
    if (!v) form.reset();
    onOpenChange(v);
  }

  async function onSubmit(values: Values) {
    if (!currentCheckout) return;
    try {
      await mutation.mutateAsync({
        assetId,
        body: { note: values.note?.trim() || null },
      });
      form.reset();
      onOpenChange(false);
    } catch (err) {
      form.setError('root', { message: toFriendlyMessage(err) });
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{RETURN_DIALOG_TITLE}</DialogTitle>
          <DialogDescription>确认归还后会在流转历史中记录归还时间与备注。</DialogDescription>
        </DialogHeader>

        {currentCheckout ? (
          <div className="rounded-sm bg-muted/50 px-3 py-2 text-sm">
            当前派发给 · <strong>{currentCheckout.holder}</strong>
            {currentCheckout.location ? <> · {currentCheckout.location}</> : null}
            <br />
            派发于 ·{' '}
            <time className="font-code">{formatDateTime(currentCheckout.checked_out_at)}</time>
          </div>
        ) : (
          <InlineErrorBanner message="此资产当前无派发中记录，请刷新页面。" />
        )}

        {form.formState.errors.root && (
          <InlineErrorBanner message={String(form.formState.errors.root.message)} />
        )}

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="note"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>备注</FormLabel>
                  <FormControl>
                    <Textarea
                      {...field}
                      disabled={mutation.isPending || !currentCheckout}
                      rows={3}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button
                type="button"
                variant="ghost"
                onClick={() => handleOpenChange(false)}
                disabled={mutation.isPending}
              >
                取消
              </Button>
              <Button
                type="submit"
                disabled={mutation.isPending || !currentCheckout}
              >
                {mutation.isPending ? RETURN_PENDING_TEXT : `确认${RETURN_VERB}`}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
```

- [ ] **Step 2: build + lint + 烟测**

```bash
pnpm --dir frontend build && pnpm --dir frontend lint
```

浏览器：派发后归还 → dialog 出现 → 提交（note 空也可）→ 成功 + dialog 关闭。

- [ ] **Step 3: commit**

```bash
git add frontend/src/features/assets/detail/return-dialog.tsx
git commit -m "refactor(form): ReturnDialog 从纯 useState 迁到 RHF + Zod"
```

---

## ✅ Phase 5 完成判定

```bash
pnpm --dir frontend build && pnpm --dir frontend lint && pnpm --dir frontend test
```

Expected: 全绿。两个 Dialog 行为前后一致；CheckoutDialog Vitest 2 case PASS。

---

## Phase 6 · 测试补全 + frontend-design 闸门 + 收尾（Task 29-30）

### Task 29: 补齐 Vitest 覆盖（纯函数 + 关键 hook 失效逻辑）

**Files:**
- Test: `frontend/tests/unit/current-checkout.test.ts`
- Test: `frontend/tests/unit/custom-field-formatter.test.ts`
- Test: `frontend/tests/hooks/use-create-asset-mutation.test.tsx`
- Test: `frontend/tests/hooks/use-delete-asset-mutation.test.tsx`
- Test: `frontend/tests/hooks/use-change-asset-status-mutation.test.tsx`

- [ ] **Step 1: current-checkout 纯函数测试**

`frontend/tests/unit/current-checkout.test.ts`：

```ts
import { describe, expect, it } from 'vitest';
import { deriveCurrentCheckout } from '@/features/assets/detail/current-checkout';

describe('deriveCurrentCheckout', () => {
  it('returns null for empty history', () => {
    expect(deriveCurrentCheckout([])).toBeNull();
    expect(deriveCurrentCheckout(undefined)).toBeNull();
  });

  it('returns null when all returned', () => {
    const history = [
      { id: 'a', returned_at: '2025-01-01T00:00:00Z' } as any,
      { id: 'b', returned_at: '2025-02-01T00:00:00Z' } as any,
    ];
    expect(deriveCurrentCheckout(history)).toBeNull();
  });

  it('returns the single active record', () => {
    const active = { id: 'b', returned_at: null } as any;
    const history = [{ id: 'a', returned_at: '2025-01-01T00:00:00Z' } as any, active];
    expect(deriveCurrentCheckout(history)).toBe(active);
  });

  it('returns most recent when multiple active (anomaly safety)', () => {
    const older = { id: 'a', returned_at: null, checked_out_at: '2025-01-01T00:00:00Z' } as any;
    const newer = { id: 'b', returned_at: null, checked_out_at: '2025-02-01T00:00:00Z' } as any;
    expect(deriveCurrentCheckout([older, newer])).toBe(newer);
  });
});
```

- [ ] **Step 2: custom-field-formatter 测试**

`frontend/tests/unit/custom-field-formatter.test.ts`：

```ts
import { describe, expect, it } from 'vitest';
import { formatCustomField } from '@/features/assets/detail/custom-field-formatter';

describe('formatCustomField', () => {
  it('string: returns as-is', () => {
    expect(formatCustomField('Intel i7', { name: 'cpu', type: 'string' })).toBe('Intel i7');
  });
  it('int with unit: appends unit', () => {
    expect(formatCustomField(32, { name: 'ram', type: 'int', unit: 'GB' })).toBe('32 GB');
  });
  it('bool: 是/否', () => {
    expect(formatCustomField(true, { name: 'x', type: 'bool' })).toBe('是');
    expect(formatCustomField(false, { name: 'x', type: 'bool' })).toBe('否');
  });
  it('date: formatted', () => {
    expect(formatCustomField('2026-04-26', { name: 'd', type: 'date' })).toMatch(/2026/);
  });
  it('null/undefined: —', () => {
    expect(formatCustomField(null, { name: 'x', type: 'string' })).toBe('—');
    expect(formatCustomField(undefined, { name: 'x', type: 'string' })).toBe('—');
  });
  it('multi-enum: joined', () => {
    expect(formatCustomField(['Type-C', 'HDMI'], { name: 'p', type: 'multi-enum' })).toBe('Type-C, HDMI');
  });
});
```

> 如果 `formatCustomField` 现有签名/行为与上面预期不一致，调整测试以匹配实际行为。重点是：纯函数有了第一批 case 兜底防回归。

- [ ] **Step 3: useCreateAssetMutation 失效测试**

`frontend/tests/hooks/use-create-asset-mutation.test.tsx`：

```tsx
import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import { useCreateAsset } from '@/api/hooks/assets';
import { qk } from '@/api/query-keys';

declare const __mswServer: any;

function makeWrapper(qc: QueryClient) {
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

describe('useCreateAsset', () => {
  it('invalidates assets.all on success', async () => {
    __mswServer.use(
      http.post('/api/assets', () =>
        HttpResponse.json({ id: 'new-1', asset_code: 'NB-001', name: 'X1' }, { status: 201 })),
    );

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries');

    const { result } = renderHook(() => useCreateAsset(), { wrapper: makeWrapper(qc) });
    result.current.mutate({ name: 'X1', type_id: 't1', custom_data: {} } as any);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: qk.assets.all });
  });
});
```

- [ ] **Step 4: useDeleteAsset 失效测试**

`frontend/tests/hooks/use-delete-asset-mutation.test.tsx`：

```tsx
import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import { useDeleteAsset } from '@/api/hooks/assets';
import { qk } from '@/api/query-keys';

declare const __mswServer: any;

describe('useDeleteAsset', () => {
  it('invalidates assets.all on 204', async () => {
    __mswServer.use(
      http.delete('/api/assets/:id', () => new HttpResponse(null, { status: 204 })),
    );
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const spy = vi.spyOn(qc, 'invalidateQueries');
    const { result } = renderHook(() => useDeleteAsset(), {
      wrapper: ({ children }) => <QueryClientProvider client={qc}>{children}</QueryClientProvider>,
    });
    result.current.mutate('asset-1');
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(spy).toHaveBeenCalledWith({ queryKey: qk.assets.all });
  });
});
```

> 注意 useDeleteAsset 现在期望 204 无 body；hook 中走 `unwrap` 可能因为 data 缺失抛错。如果出现这个问题，按 M2c-2 spec §10 第 5 条同款方案：DELETE hook 内手工处理 res.error 不走 unwrap。改 useDeleteAsset hook 实现：

```ts
mutationFn: async (id: string) => {
  const res = await http.DELETE("/api/assets/{asset_id}", { params: { path: { asset_id: id } } });
  if (res.error) throw res.error;  // 不走 unwrap，因为 204 无 body
  return undefined;
},
```

- [ ] **Step 5: useChangeAssetStatusMutation 失效测试**

`frontend/tests/hooks/use-change-asset-status-mutation.test.tsx`（参照 use-create 套法，验证失效 detail + history + all 三个 key）：

```tsx
import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import { useChangeAssetStatusMutation } from '@/api/hooks/assets';
import { qk } from '@/api/query-keys';

declare const __mswServer: any;

describe('useChangeAssetStatusMutation', () => {
  it('invalidates detail + history + all on success', async () => {
    __mswServer.use(
      http.patch('/api/assets/:id', () =>
        HttpResponse.json({ id: 'a-1', status: 'MAINTENANCE' }, { status: 200 })),
    );
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const spy = vi.spyOn(qc, 'invalidateQueries');
    const { result } = renderHook(() => useChangeAssetStatusMutation('a-1'), {
      wrapper: ({ children }) => <QueryClientProvider client={qc}>{children}</QueryClientProvider>,
    });
    result.current.mutate('MAINTENANCE');
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const calls = spy.mock.calls.map((c) => c[0].queryKey);
    expect(calls).toContainEqual(qk.assets.all);
    expect(calls).toContainEqual(qk.assets.detail('a-1'));
    expect(calls).toContainEqual(qk.assets.history('a-1'));
  });
});
```

- [ ] **Step 6: 跑全部 Vitest**

```bash
pnpm --dir frontend test
```

Expected: 所有 case PASS。统计：smoke(1) + field-def-to-zod(11) + state-change-actions(6) + upload-progress(3) + current-checkout(4) + custom-field-formatter(6) + checkout-dialog(2) + 3 个 hook 测 = 约 36 case。

- [ ] **Step 7: commit**

```bash
git add frontend/tests/
git commit -m "test(vitest): 补齐 β 档覆盖 · current-checkout / formatter / 3 个 mutation hook 失效逻辑"
```

---

### Task 30: frontend-design 闸门 ②③ + 红线扫描 + MASTER 纠偏回写 + 主 spec 钩子状态更新

**Files:**
- 修改: `design-system/asset-hub/MASTER.md`（追加"实施期纠偏（M2c-3）"区块）
- 修改: `design-system/asset-hub/pages/assets-list.md`（如存在；加列顺序 override）
- 修改: `docs/superpowers/specs/2026-04-15-asset-hub-design.md`（M2c-1 §K 缺口标"M2c-3 已落地"）
- 修改: `docs/superpowers/specs/2026-04-25-m2c2-detail-flow-attachments-design.md`（§10.3 后端字段补齐 标"M2c-3 已落地"）
- 修改: `frontend/src/features/assets/detail/copyable-text.tsx:12`（去掉"未来 asset_code"注释，因为已落地）

- [ ] **Step 1: 红线 grep（前后端全覆盖）**

```bash
cd frontend
grep -rnE 'scale-(75|90|95|100|105|110|125|150)|animate-spin|backdrop-blur|bg-gradient-to' src/ tests/
```

Expected: 0 命中。任一命中要在 commit 前修复。

- [ ] **Step 2: MASTER `Pre-Delivery Checklist` 7 项手工过**

参照 `design-system/asset-hub/MASTER.md:191-204`，浏览器逐项确认：
- 无 emoji 当 icon（全 Lucide SVG）
- clickable 元素都有 `cursor-pointer`（shadcn 默认 + 显式 button）
- hover transition 150-300ms（color / shadow，无 scale）
- light mode 文本对比度 ≥ 4.5:1
- focus-visible 可见
- prefers-reduced-motion 降级
- 1024+ 响应式

- [ ] **Step 3: 跑附录 A 18 项手工烟测**

按 M2c-3 spec §附录 A 顺序执行（A.1 登记 / A.2 编辑 / A.3 删除 / A.4 上传 / A.5 状态切换 / A.6 列表 / A.7 RHF 迁移 / A.8 红线）。每项打勾或记录纠偏。

- [ ] **Step 4: 写 MASTER 纠偏回写**

`design-system/asset-hub/MASTER.md` 末尾追加：

```markdown
---

## 实施期纠偏（M2c-3，2026-04-26）

frontend-design 闸门 ②③ + Pre-Delivery Checklist 7 项 + 红线 0 命中 + spec 附录 A 18 项手工烟测全部通过后回写。承接 M2c-1 / M2c-2 已写入的覆盖清单。

### 1. M2c-1 / M2c-2 上游缺口"asset_code 字段"已落地

**M2c-1 实施期纠偏 §1**（"后端 AssetRead DTO 缺 asset_code 字段，权宜列表用 SN ?? id.slice(0, 8) 顶替"）状态：**M2c-3 已落地**。具体落地形态参考 M2c-3 spec §12 反向纠偏说明 + §1.1.2 / §5.1 / §7.9。

新形态：
- `Asset.asset_code` 自动生成 `{prefix}-{seq:03d}`（如 `NB-007`）
- `AssetType.code_prefix` 必填字段（`^[A-Z]{2,4}$`、unique、immutable）
- 列表第一列改回 asset_code（mono Fira Code），SN 拆为独立列

### 2. type_name 反规范化方式

**plan 决议**：SQLAlchemy `Relationship` + `lazy="joined"` + `Asset.type_name` `@property` 暴露。详见 `src/asset_hub/models/asset.py`。

- 单 SELECT 自动 JOIN，对单 asset 查询无 N+1
- list_assets 走默认 select(Asset)，relationship lazy=joined 兜底
- AssetRead DTO 通过 `from_attributes=True` 自动读取 `Asset.type_name` property

### 3. shadcn 新增组件 variant 审查清单

本里程碑首次引入 `form / checkbox / radio-group / select / popover / calendar / command / label`。引入即审：
- 全部移除 Next 残留 `"use client"` 指令
- Calendar 设 `locale={zhCN}`
- Select / Popover / Calendar 全部用 `bg-popover` token，未硬编码 `bg-white`

### 4. 表单 input padding override（与 MASTER baseline 不同）

MASTER 给的 `.input { padding: 12px 16px }` 是 hero/landing 风格；表单密度场景下 shadcn 默认 size="default"（更紧）更合适。本里程碑表单 input 沿用 shadcn 默认。

### 5. RHF 迁移已完成（M2c-2 留的债）

`CheckoutDialog` / `ReturnDialog` 从纯 React state 迁到 RHF + Zod，UX 行为前后一致。Vitest 2 case 试点用例已加。

### 6. 附件 add slot 视觉样式

MASTER 未涉及 dropzone 元素。本里程碑显式定义：
- 默认：`border: 1.5px dashed muted-foreground/40 + 圆角同 tile + transition-colors`
- hover：`border-primary text-primary bg-primary/5`
- 拖拽 active：同 hover
- 上传中：tile 内显示文件名 + 进度条（width transition），无 spinner
- 失败：destructive 文本 + 重试按钮（lucide `RotateCw`）

与 MASTER hover 用色温变化（不是 shadow / scale）同源。

### 7. 上传进度条用 width transition 而非 spinner

`AttachmentAddSlot` 的进度态用 `<div style={{ width: `${percent}%` }} className="transition-[width] duration-150 ease-out">`，避免 `animate-spin`。承接 M2c-2 反 AI-slop 红线。

### Pre-Delivery Checklist（M2c-3 验证）

- [x] No emojis as icons（全 Lucide：Plus / X / RotateCw / AlertCircle / CalendarIcon / ChevronsUpDown / Check 等）
- [x] cursor-pointer on clickable elements（shadcn Button / DropdownMenuItem 默认；AddSlot button 显式）
- [x] Hover transitions smooth 150-300ms（`transition-colors`，无 `transform: scale`）
- [x] Light mode text contrast 4.5:1（沿用 M2c-1 token，无新色）
- [x] Focus states visible for keyboard（globals.css 兜底；form / dialog 默认 focus-visible）
- [x] `prefers-reduced-motion` respected（沿用 globals.css 媒体查询；表单页本身无 stagger）
- [x] Responsive 1024+（max-w-2xl 表单；详情页继续 max-w-960）

### 红线扫描结果

`grep -rnE 'scale-|animate-spin|backdrop-blur|bg-gradient-to'` 在 M2c-3 新增/修改文件内：**0 命中**。

### 手工烟测（spec 附录 A 18 项）

由作者在浏览器中逐项执行；本静态闸门已通过。
```

- [ ] **Step 5: 改 design-system/asset-hub/pages/assets-list.md（如存在）**

加一条列顺序 override：

```markdown
## 列顺序（M2c-3 落地）

| # | 列 | 字体 | 备注 |
| --- | --- | --- | --- |
| 1 | 编号（asset_code） | Fira Code mono | 主标识符；mono 字体调性锚点 |
| 2 | 名称（name） | Fira Sans | 含义 |
| 3 | SN（serial_number） | Fira Code mono | 物理铭牌；缺失显 — muted |
| 4 | 类型（type_name） | Fira Sans muted | 后端 §K relationship 提供 |
| 5 | 状态（status） | StatusBadge | |
| 6 | 持有人 | Fira Sans | |
| 7 | 位置 | Fira Sans | |
| 8 | 更新时间 | Fira Code mono（tnum） | |
| 9 | 入账日期（acquired_at） | Fira Code mono | **默认隐藏**，column-visibility 可开启 |
| 10 | ⋯ 行操作 | — | |

**默认排序**：`asset_code` 升序。
```

- [ ] **Step 6: 改主 spec / M2c-2 spec 钩子状态**

`docs/superpowers/specs/2026-04-25-m2c2-detail-flow-attachments-design.md` §10.3 改：

```markdown
### 10.3 后端字段补齐

**M2c-1 + M2c-2 共同遗留**，**M2c-3 已落地**（详见 `2026-04-26-m2c3-form-attachments-actions-design.md` §1.1.4 / §5）：
- ✅ `Asset.asset_code`（`{type_prefix}-{seq:03d}` 简化形态；M2c-3 落地）
- ✅ `Asset.type_name` 反规范化（SQLAlchemy `Relationship + lazy="joined"` + `@property`）
- ✅ `Asset.current_checkout_id`（service 层 checkout/return 维护）
- ✅ `AssetType.code_prefix`（必填、^[A-Z]{2,4}$、unique、immutable）
```

- [ ] **Step 7: 改 copyable-text.tsx 注释（去掉"未来 asset_code"）**

`frontend/src/components/copyable-text.tsx:12` 注释更新（不再"未来"）：

```ts
/**
 * 标识符类长字符串的复制 UI（SN / 资产 ID / asset_code 等）。
 */
```

- [ ] **Step 8: 跑最后一遍全套测试**

```bash
uv run pytest -v
uv run ruff check .
pnpm --dir frontend build
pnpm --dir frontend lint
pnpm --dir frontend test
uv run alembic current
```

Expected: 全绿；alembic 在最新 head。

- [ ] **Step 9: commit**

```bash
git add design-system/ docs/ frontend/src/components/copyable-text.tsx
git commit -m "chore(m2c3): 闸门②③通过 + MASTER 实施期纠偏回写 + 主 spec 钩子状态更新（asset_code 反向纠偏已落地）"
```

---

## ✅ Phase 6 / M2c-3 完成判定

参考 spec §11 DoD：

### 11.1 功能 DoD
- [x] `/assets/new` + AssetCreateForm（Task 18）
- [x] `/assets/:id/edit` + AssetEditForm（Task 19）
- [x] 删除 ⋯ 菜单 + AlertDialog + IN_USE disable（Task 22 / 23）
- [x] 附件 add slot + 拖拽 + progress + 重试（Task 25 / 26）
- [x] §14.5 状态切换 4 动作（Task 21 / 23）
- [x] 列表 asset_code 主列 + SN 独立 + acquired_at 默认隐藏 + sort（Task 13）
- [x] CheckoutDialog / ReturnDialog 迁 RHF（Task 27 / 28）
- [x] 后端字段补齐 + alembic migration（Task 1 / 2 / 3 / 8）
- [x] state_machine 4×4 矩阵 + pytest（Task 5）
- [x] CLI 扩展（Task 9）

### 11.2 工程 DoD（Task 30 step 8 验证）
- [x] frontend pnpm build / lint / test 全绿
- [x] backend pytest / ruff 全绿
- [x] alembic upgrade head 跑通（Task 8 step 3）
- [x] MASTER Pre-Delivery 7 项过（Task 30 step 2）
- [x] frontend-design 闸门 ②③ 过（Task 30 step 4-5）
- [x] 红线 0 命中（Task 30 step 1）

### 11.3 文档 DoD
- [x] 主 spec §11 / §14.5 / §14.10 / §14.11 已在 spec 提交时更新
- [x] M2c-2 spec §10.3 状态更新（Task 30 step 6）
- [x] MASTER "实施期纠偏（M2c-3）"区块已写（Task 30 step 4）
- [x] release-notes-m2c3.md 部署清单（Task 8 step 5）

---

## 实施期纠偏占位（M2c-3）

与 M2c-1 / M2c-2 plan 同款占位：实施期发现的上游缺口、临时权宜、偏离 MASTER 的细节由 Task 30 step 4 回写到 `design-system/asset-hub/MASTER.md` 末尾"实施期纠偏（M2c-3）"区块。本 plan 不在此节展开（避免 plan 与 MASTER 双源）。

---

## 自检清单（写完 plan 的最后一步）

本节仅作者阅读；执行者无需勾选。

### 1. Spec 覆盖

| spec 节点 | 对应 Task |
| --- | --- |
| §1.1.1 资产侧（登记/编辑/删除/上传/§14.5） | Task 18 / 19 / 22 / 25-26 / 21 / 23 |
| §1.1.2 类型侧（code_prefix） | Task 2 / 9 |
| §1.1.3 列表页变更 | Task 13 / 14 |
| §1.1.4 后端字段补齐 | Task 1-8 |
| §1.1.5 框架引入（Vitest / RHF） | Task 10-12 / 27-28 / 29 |
| D1-D21 决策矩阵 | 全部 Task 贯穿（每条决策都有对应 Task 落地，Task body 显式引用 D 编号） |
| §3 设计系统 baseline / 4 闸门 / 反 AI-slop 红线 | 每个 UI Task 末尾 §3.5 约束引用 + Task 30 闸门②③ |
| §4.2 文件结构（30+ 新建 + 10+ 修改） | 每个 Task 的 Files 段对应 |
| §5 数据层（model / migration / API 端点 / hook / state_machine / FieldDef→Zod） | Task 1-9 / 13 / 15 / 21 |
| §6 路由 | Task 18 / 19 |
| §7 UI（10 个组件） | Task 16 / 17 / 18 / 19 / 21 / 22 / 23 / 25 / 26 / 27 / 28 |
| §8 错误处理 4 层 | 各 form Task / Dialog Task 显式 inline / Toast / FormMessage 处理 |
| §9 测试策略 β 档 | Task 15（field-def-to-zod 11 case）/ Task 21（state-change-actions 6 case）/ Task 24（upload-progress 3 case）/ Task 27（checkout-dialog 2 case）/ Task 29（current-checkout / formatter / 3 hook 失效 共约 14 case）/ 后端 pytest（state_machine / register / state_change endpoint / cli）|
| §10 扩展兼容性锚点（M2c-4 / M2d / §14.1 / §14.6 / §14.7）| 每个相关 Task 内显式说明（state_machine 模块 / checkout-actions 常量 / Asset 模型字段 immutable 等）|
| §11 DoD | Task 30 step 8 跑全套 + Phase 6 完成判定 |
| §12 反向纠偏（asset_code 简化版加回） | Task 2 / 3 / 8 / 30 step 4 |
| 附录 A 18 项手工烟测 | Task 30 step 3 逐项执行 |

### 2. Placeholder 扫描

grep `TBD|TODO|implement later|FIXME` ——本 plan：
- "TODO 注释" 作为字面值出现（Task 14 step 2 临时方案的内联说明）— OK，是真实 fallback 实现指引而非 plan 占位
- 无 "TBD" / "implement later" 命中

### 3. 类型一致

- `FieldDef`（spec D2 + types.ts）签名一致；fieldDefsToZodSchema 消费、DynamicFieldRenderer 消费、AssetFormFields 消费均用同一类型
- `STATE_CHANGE_ACTIONS` / `StateChangeKey` 在 state-change-actions.ts 定义；StateChangeAlert / AssetHeader / AssetDetailPage 均按相同签名引用
- `CreateFormValues` / `EditFormValues` 由 `buildCreateSchema` / `buildEditSchema` 推导，与 RHF resolver 形态一致
- 后端：`AssetRead` 含 `asset_code / type_name / acquired_at / current_checkout_id`；router / CLI / service 出入口一致
- alembic migration 中 `code_prefix` 字段长度无显式约束——SQLAlchemy 默认 String，SQLite 不强制长度，service 层的 regex 是真正 enforce；这是有意为之

### 4. frontend-design 隐性 shadcn 默认扫描（spec §3.3 ② 要求）

每个 UI Task 末尾的 §3.5 约束引用栏列出该 Task 触发的红线条款。Task 30 闸门②的 grep 红线扫描覆盖整轮实施。

---

**plan 完。**








