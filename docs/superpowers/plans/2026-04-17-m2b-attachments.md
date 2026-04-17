# M2b · 附件（CLI + API + FS 存储）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 M2a 基础上实现资产附件的上传、列出、下载、删除，覆盖 `StorageAdapter` 抽象 + service / CLI / API 三层，保证"同资产同内容的附件不重复"。

**Architecture:** 新增 `Attachment` 表 + `UniqueConstraint(asset_id, sha256)`；新增 `StorageAdapter` 抽象（`storage/base.py`）与 `LocalFSStorage` 实现（`storage/local_fs.py`）。`AttachmentService` 是唯一事实源：注入一个 `StorageAdapter`，接受 `BinaryIO` stream，在同事务内落盘 + 写元数据。物理文件按 `<yyyy>/<mm>/<sha256>.<ext>` 存放，相同内容天然共享一份磁盘文件；CLI 直接构造 `LocalFSStorage`，API 通过 `Depends` 注入。

**Tech Stack:** 沿用 M1+M2a（Python 3.12 + FastAPI + SQLModel + Typer + pytest）。新增：`python-multipart`（FastAPI `UploadFile` / `Form` 解析）；标准库 `hashlib.sha256`、`mimetypes`。

## 关键决策（先读再动手）

1. **内容寻址 + (asset_id, sha256) 唯一约束**：物理文件路径用 sha256 命名，同内容自动共享磁盘；DB 用复合唯一约束保证同资产同内容不会重复登记。
2. **`StorageAdapter` 抽象**：`save(stream, *, original_ext) -> StoredFile`、`open(path) -> BinaryIO`、`delete(path)`。`save` 边读边算 sha256，先写 `.tmp` 再 `rename` 到最终路径；若最终路径已存在（同内容已落盘），则丢弃 tmp 文件直接复用。
3. **同内容复用文件**：`AttachmentService.add` 在 `save` 之后做 `(asset_id, sha256)` 去重检查；跨资产重复的 sha256 视为"合法共享同一物理文件"，不报错。
4. **删除策略**：`AttachmentService.delete` 删 DB 行后，**当且仅当**没有其他 `Attachment` 引用相同 sha256 才物理删文件。保证不会留下孤儿，也不会误删共享文件。
5. **service 入口统一 `BinaryIO`**：CLI 用 `Path.open("rb")`、API 用 `UploadFile.file`，两边都是 binary file-like；MIME 由 service 兜底（API 优先用 `UploadFile.content_type`，否则 `mimetypes.guess_type(filename)` fallback 到 `application/octet-stream`）。
6. **CLI 范围严格对齐 spec §6.1**：仅 `attachment add / attachment list` 两条，作为顶层子命令（`asset-hub attachment ...`，不是 `asset attachment`）。下载 / 删除留给 API，不在 CLI 暴露（M3+ 再议）。
7. **API 暴露 5 个端点**：`POST /api/assets/{id}/attachments`、`GET /api/assets/{id}/attachments`、`GET /api/attachments/{id}`（元数据）、`GET /api/attachments/{id}/content`（下载文件）、`DELETE /api/attachments/{id}`。M2c 前端直接消费。
8. **依赖事务一致性（v1 放松）**：写文件成功但 DB commit 失败时，tmp 已重命名为 sha256 命名——接受极低概率残留（按 sha256 寻址，下次同内容上传会直接复用，不算孤儿）。写完 DB 后不再回滚文件。
9. **Commit message 规范** 遵循全局 Angular 约定，中文 subject，**不**附带工具标记或 Co-Authored-By。

---

## 文件结构

M2b 结束后，新增/修改如下：

```
asset-hub/
├── pyproject.toml                                # 修改：加 python-multipart 依赖
│
├── src/asset_hub/
│   ├── models/
│   │   ├── __init__.py                           # 修改：注册 Attachment / AttachmentKind
│   │   └── attachment.py                         # 新增：Attachment + AttachmentKind + UniqueConstraint
│   │
│   ├── storage/                                  # 新增目录
│   │   ├── __init__.py                           # 新增：空
│   │   ├── base.py                               # 新增：StorageAdapter ABC + StoredFile
│   │   └── local_fs.py                           # 新增：LocalFSStorage 实现
│   │
│   ├── repositories/
│   │   └── attachment.py                         # 新增：AttachmentRepository
│   │
│   ├── services/
│   │   └── attachment.py                         # 新增：AttachmentService
│   │
│   ├── api/
│   │   ├── app.py                                # 修改：挂 attachments 路由
│   │   ├── deps.py                               # 修改：新增 get_storage / AttachmentService 依赖
│   │   ├── schemas/
│   │   │   └── attachment.py                     # 新增：AttachmentRead
│   │   └── routers/
│   │       └── attachments.py                    # 新增：上传/列表/元数据/下载/删除
│   │
│   └── cli/
│       ├── main.py                               # 修改：挂 attachment_app
│       └── attachment_cmd.py                     # 新增：attachment add / list 命令
│
└── tests/
    ├── unit/
    │   ├── test_attachment_model.py              # 新增：模型 smoke + 唯一约束
    │   ├── test_local_fs_storage.py              # 新增：存储适配器行为
    │   └── test_attachment_service.py            # 新增：service 行为
    ├── cli/
    │   └── test_attachment_cli.py                # 新增：CLI 信封 + 退出码
    └── api/
        └── test_attachment_routes.py             # 新增：HTTP 行为（multipart 上传 / 下载）
```

---

## Task 1: Attachment 模型 + 枚举 + 唯一约束

**Files:**
- Create: `src/asset_hub/models/attachment.py`
- Modify: `src/asset_hub/models/__init__.py`
- Create: `tests/unit/test_attachment_model.py`

- [ ] **Step 1.1: 写失败测试**

Create `tests/unit/test_attachment_model.py`:

```python
from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from asset_hub.models.asset import Asset
from asset_hub.models.asset_type import AssetType
from asset_hub.models.attachment import Attachment, AttachmentKind


def _make_asset(session: Session) -> Asset:
    t = AssetType(name="T", custom_fields=[])
    session.add(t)
    session.flush()
    a = Asset(name="A", type_id=t.id, custom_data={})
    session.add(a)
    session.commit()
    session.refresh(a)
    return a


def test_attachment_can_be_persisted(session: Session):
    a = _make_asset(session)
    att = Attachment(
        asset_id=a.id,
        kind=AttachmentKind.PHOTO,
        storage_path="2026/04/abc.jpg",
        sha256="a" * 64,
        size=1024,
        mime_type="image/jpeg",
        original_name="x.jpg",
    )
    session.add(att)
    session.commit()
    session.refresh(att)

    assert att.id is not None
    assert att.kind == AttachmentKind.PHOTO
    assert isinstance(att.uploaded_at, datetime)


def test_unique_constraint_blocks_same_asset_same_sha256(session: Session):
    a = _make_asset(session)
    session.add(
        Attachment(
            asset_id=a.id,
            kind=AttachmentKind.PHOTO,
            storage_path="2026/04/abc.jpg",
            sha256="a" * 64,
            size=1,
            mime_type="image/jpeg",
            original_name="x.jpg",
        )
    )
    session.commit()

    session.add(
        Attachment(
            asset_id=a.id,
            kind=AttachmentKind.PHOTO,
            storage_path="2026/04/abc.jpg",
            sha256="a" * 64,
            size=1,
            mime_type="image/jpeg",
            original_name="x2.jpg",
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_different_assets_can_share_sha256(session: Session):
    t = AssetType(name="T2", custom_fields=[])
    session.add(t)
    session.flush()
    a1 = Asset(name="A1", type_id=t.id, custom_data={})
    a2 = Asset(name="A2", type_id=t.id, custom_data={})
    session.add(a1)
    session.add(a2)
    session.commit()

    session.add(
        Attachment(
            asset_id=a1.id,
            kind=AttachmentKind.DOC,
            storage_path="2026/04/xxx.pdf",
            sha256="b" * 64,
            size=1,
            mime_type="application/pdf",
            original_name="x.pdf",
        )
    )
    session.add(
        Attachment(
            asset_id=a2.id,
            kind=AttachmentKind.DOC,
            storage_path="2026/04/xxx.pdf",
            sha256="b" * 64,
            size=1,
            mime_type="application/pdf",
            original_name="x.pdf",
        )
    )
    session.commit()  # 不应抛异常：跨资产共享同一物理文件是合法的


def test_enum_values_match_spec():
    assert AttachmentKind.PHOTO.value == "photo"
    assert AttachmentKind.INVOICE.value == "invoice"
    assert AttachmentKind.DOC.value == "doc"
    assert AttachmentKind.OTHER.value == "other"
    assert {k.value for k in AttachmentKind} == {"photo", "invoice", "doc", "other"}
```

- [ ] **Step 1.2: 运行测试确认失败**

Run: `uv run pytest tests/unit/test_attachment_model.py -v`

Expected: `ModuleNotFoundError: No module named 'asset_hub.models.attachment'`

- [ ] **Step 1.3: 创建 Attachment 模型**

Create `src/asset_hub/models/attachment.py`:

```python
import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class AttachmentKind(StrEnum):
    PHOTO = "photo"
    INVOICE = "invoice"
    DOC = "doc"
    OTHER = "other"


class Attachment(SQLModel, table=True):
    __tablename__ = "attachments"
    __table_args__ = (
        UniqueConstraint("asset_id", "sha256", name="uq_attachment_asset_sha256"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    asset_id: uuid.UUID = Field(foreign_key="assets.id", index=True)
    kind: AttachmentKind = Field(default=AttachmentKind.OTHER)
    storage_path: str  # 相对 storage root 的路径，如 "2026/04/<sha256>.jpg"
    sha256: str = Field(index=True)
    size: int
    mime_type: str
    original_name: str
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
```

- [ ] **Step 1.4: 注册到 models/__init__.py**

Overwrite `src/asset_hub/models/__init__.py` with:

```python
# 汇总导出，确保 SQLModel.metadata.create_all 能发现所有表模型
from asset_hub.models.asset import Asset, AssetStatus
from asset_hub.models.asset_type import AssetType
from asset_hub.models.attachment import Attachment, AttachmentKind
from asset_hub.models.checkout import CheckoutRecord

__all__ = [
    "Asset",
    "AssetStatus",
    "AssetType",
    "Attachment",
    "AttachmentKind",
    "CheckoutRecord",
]
```

- [ ] **Step 1.5: 运行模型测试确认通过**

Run: `uv run pytest tests/unit/test_attachment_model.py -v`

Expected: 4 tests PASS

- [ ] **Step 1.6: 回归全量测试**

Run: `uv run pytest -q`

Expected: M1 + M2a + 新 4 条模型测试全部通过。

- [ ] **Step 1.7: 提交**

```bash
git add src/asset_hub/models/attachment.py src/asset_hub/models/__init__.py tests/unit/test_attachment_model.py
git commit -m "$(cat <<'EOF'
feat(model): 新增 Attachment 与 AttachmentKind

- Attachment 表：asset_id / kind / storage_path / sha256 / size / mime_type / original_name / uploaded_at
- UniqueConstraint(asset_id, sha256) 保证同资产同内容不重复
- 跨资产共享同一 sha256（指向同一物理文件）允许存在
- AttachmentKind: photo | invoice | doc | other
EOF
)"
```

---

## Task 2: StorageAdapter 抽象 + LocalFSStorage (TDD)

**Files:**
- Create: `src/asset_hub/storage/__init__.py`
- Create: `src/asset_hub/storage/base.py`
- Create: `src/asset_hub/storage/local_fs.py`
- Create: `tests/unit/test_local_fs_storage.py`

- [ ] **Step 2.1: 写失败测试**

Create `tests/unit/test_local_fs_storage.py`:

```python
import hashlib
import io
from pathlib import Path

import pytest

from asset_hub.storage.base import StoredFile
from asset_hub.storage.local_fs import LocalFSStorage


@pytest.fixture()
def storage(tmp_path: Path) -> LocalFSStorage:
    return LocalFSStorage(root=tmp_path / "attachments")


def test_save_writes_file_and_returns_metadata(storage: LocalFSStorage):
    data = b"hello world"
    expected_sha = hashlib.sha256(data).hexdigest()

    result = storage.save(io.BytesIO(data), original_ext=".txt")

    assert isinstance(result, StoredFile)
    assert result.sha256 == expected_sha
    assert result.size == len(data)
    assert result.storage_path.endswith(f"{expected_sha}.txt")
    # 路径形如 "2026/04/<sha>.txt"
    parts = result.storage_path.split("/")
    assert len(parts) == 3
    assert parts[0].isdigit() and len(parts[0]) == 4  # year
    assert parts[1].isdigit() and len(parts[1]) == 2  # month

    # 物理文件真实存在且内容正确
    full = storage.root / result.storage_path
    assert full.read_bytes() == data


def test_save_same_content_is_idempotent_on_disk(storage: LocalFSStorage):
    data = b"same content"
    first = storage.save(io.BytesIO(data), original_ext=".bin")
    second = storage.save(io.BytesIO(data), original_ext=".bin")

    assert first.sha256 == second.sha256
    assert first.storage_path == second.storage_path

    # 没有残留的 tmp 文件
    all_files = list(storage.root.rglob("*"))
    non_dirs = [p for p in all_files if p.is_file()]
    assert len(non_dirs) == 1
    assert non_dirs[0].name.endswith(".bin")


def test_save_empty_extension(storage: LocalFSStorage):
    result = storage.save(io.BytesIO(b"x"), original_ext="")
    assert result.storage_path.endswith(result.sha256)
    # 没有多余的点
    assert "." not in Path(result.storage_path).name


def test_open_returns_readable_stream(storage: LocalFSStorage):
    data = b"payload"
    saved = storage.save(io.BytesIO(data), original_ext=".bin")

    with storage.open(saved.storage_path) as fh:
        assert fh.read() == data


def test_delete_removes_file(storage: LocalFSStorage):
    saved = storage.save(io.BytesIO(b"zzz"), original_ext=".bin")
    full = storage.root / saved.storage_path
    assert full.exists()

    storage.delete(saved.storage_path)
    assert not full.exists()


def test_delete_missing_file_is_silent(storage: LocalFSStorage):
    # 删除不存在的路径不应抛异常（便于 service 层容错）
    storage.delete("nowhere/does/not-exist.bin")
```

- [ ] **Step 2.2: 运行测试确认失败**

Run: `uv run pytest tests/unit/test_local_fs_storage.py -v`

Expected: `ModuleNotFoundError: No module named 'asset_hub.storage'`

- [ ] **Step 2.3: 创建 storage 包骨架**

Create `src/asset_hub/storage/__init__.py`（空文件）。

Create `src/asset_hub/storage/base.py`:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import BinaryIO


@dataclass
class StoredFile:
    """存储后返回给调用方的元数据。storage_path 是相对 storage root 的相对路径。"""

    storage_path: str
    sha256: str
    size: int


class StorageAdapter(ABC):
    @abstractmethod
    def save(self, stream: BinaryIO, *, original_ext: str) -> StoredFile:
        """读取 stream 全量写入存储，返回 sha256 / size / 相对路径。

        实现需保证：边读边算 sha256；同内容（相同 sha256）落到同一物理位置。
        """

    @abstractmethod
    def open(self, storage_path: str) -> BinaryIO:
        """以二进制只读方式打开存储中的文件。"""

    @abstractmethod
    def delete(self, storage_path: str) -> None:
        """删除存储中的文件。文件不存在时静默返回。"""
```

- [ ] **Step 2.4: 实现 LocalFSStorage**

Create `src/asset_hub/storage/local_fs.py`:

```python
import hashlib
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO

from asset_hub.storage.base import StorageAdapter, StoredFile

_CHUNK = 1 << 20  # 1 MiB


class LocalFSStorage(StorageAdapter):
    """本地文件系统存储。路径结构：<root>/<yyyy>/<mm>/<sha256><ext>。

    实现细节：
    - `save` 先写 tmp 文件，边写边算 sha256，读完后 rename 到 sha256 命名的最终路径。
    - 若目标路径已存在（同 sha256 已落盘），则丢弃 tmp、复用现有文件；调用方拿到
      的 `storage_path` 对同内容的两次调用完全相同。
    - `delete` 对不存在的路径保持静默，便于 service 层容错。
    """

    def __init__(self, root: Path):
        self.root = Path(root)

    def save(self, stream: BinaryIO, *, original_ext: str) -> StoredFile:
        now = datetime.now(UTC)
        subdir = self.root / f"{now.year:04d}" / f"{now.month:02d}"
        subdir.mkdir(parents=True, exist_ok=True)

        tmp_path = subdir / f".upload-{uuid.uuid4().hex}.tmp"
        hasher = hashlib.sha256()
        size = 0
        try:
            with tmp_path.open("wb") as fh:
                while chunk := stream.read(_CHUNK):
                    hasher.update(chunk)
                    fh.write(chunk)
                    size += len(chunk)

            sha256 = hasher.hexdigest()
            filename = f"{sha256}{original_ext}"
            final_path = subdir / filename

            if final_path.exists():
                tmp_path.unlink(missing_ok=True)
            else:
                tmp_path.replace(final_path)
        except BaseException:
            tmp_path.unlink(missing_ok=True)
            raise

        rel = final_path.relative_to(self.root).as_posix()
        return StoredFile(storage_path=rel, sha256=sha256, size=size)

    def open(self, storage_path: str) -> BinaryIO:
        return (self.root / storage_path).open("rb")

    def delete(self, storage_path: str) -> None:
        (self.root / storage_path).unlink(missing_ok=True)
```

- [ ] **Step 2.5: 运行测试确认通过**

Run: `uv run pytest tests/unit/test_local_fs_storage.py -v`

Expected: 6 tests PASS

- [ ] **Step 2.6: 提交**

```bash
git add src/asset_hub/storage/__init__.py src/asset_hub/storage/base.py src/asset_hub/storage/local_fs.py tests/unit/test_local_fs_storage.py
git commit -m "$(cat <<'EOF'
feat(storage): StorageAdapter 接口与 LocalFSStorage 实现

- StoredFile dataclass 承载 storage_path / sha256 / size
- LocalFSStorage 按 <root>/<yyyy>/<mm>/<sha256><ext> 组织文件
- save 边读边算 sha256，tmp → rename；同内容复用同一物理路径
- delete 对缺失路径静默（missing_ok=True）
EOF
)"
```

---

## Task 3: AttachmentRepository + AttachmentService.add (TDD)

**Files:**
- Create: `src/asset_hub/repositories/attachment.py`
- Create: `src/asset_hub/services/attachment.py`
- Create: `tests/unit/test_attachment_service.py`

- [ ] **Step 3.1: 写失败测试**

Create `tests/unit/test_attachment_service.py`:

```python
import io
from pathlib import Path
from uuid import uuid4

import pytest
from sqlmodel import Session

from asset_hub.errors import DuplicateError, NotFoundError
from asset_hub.models.attachment import AttachmentKind
from asset_hub.services.asset import AssetService
from asset_hub.services.asset_type import TypeService
from asset_hub.services.attachment import AttachmentService
from asset_hub.storage.local_fs import LocalFSStorage


@pytest.fixture()
def storage(tmp_path: Path) -> LocalFSStorage:
    return LocalFSStorage(root=tmp_path / "attachments")


@pytest.fixture()
def type_svc(session: Session) -> TypeService:
    return TypeService(session)


@pytest.fixture()
def asset_svc(session: Session) -> AssetService:
    return AssetService(session)


@pytest.fixture()
def att_svc(session: Session, storage: LocalFSStorage) -> AttachmentService:
    return AttachmentService(session, storage)


@pytest.fixture()
def simple_type(type_svc: TypeService):
    return type_svc.create_type(name="笔记本", custom_fields=[])


@pytest.fixture()
def asset(asset_svc: AssetService, simple_type):
    return asset_svc.register(name="X1", type_id=simple_type.id, custom_data={})


class TestAdd:
    def test_add_persists_file_and_metadata(
        self,
        att_svc: AttachmentService,
        storage: LocalFSStorage,
        asset,
    ):
        att = att_svc.add(
            asset_id=asset.id,
            kind=AttachmentKind.PHOTO,
            original_name="photo.jpg",
            stream=io.BytesIO(b"fake-jpeg-bytes"),
        )
        assert att.id is not None
        assert att.asset_id == asset.id
        assert att.kind == AttachmentKind.PHOTO
        assert att.size == len(b"fake-jpeg-bytes")
        assert att.original_name == "photo.jpg"
        assert att.mime_type == "image/jpeg"
        assert len(att.sha256) == 64
        assert att.storage_path.endswith(f"{att.sha256}.jpg")

        # 物理文件落盘
        assert (storage.root / att.storage_path).read_bytes() == b"fake-jpeg-bytes"

    def test_add_uses_explicit_mime_type_when_given(
        self, att_svc: AttachmentService, asset
    ):
        att = att_svc.add(
            asset_id=asset.id,
            kind=AttachmentKind.OTHER,
            original_name="whatever.bin",
            stream=io.BytesIO(b"x"),
            mime_type="application/x-custom",
        )
        assert att.mime_type == "application/x-custom"

    def test_add_fallbacks_to_octet_stream_for_unknown_ext(
        self, att_svc: AttachmentService, asset
    ):
        att = att_svc.add(
            asset_id=asset.id,
            kind=AttachmentKind.OTHER,
            original_name="file.mystery",
            stream=io.BytesIO(b"x"),
        )
        assert att.mime_type == "application/octet-stream"

    def test_add_to_nonexistent_asset_raises(self, att_svc: AttachmentService):
        with pytest.raises(NotFoundError):
            att_svc.add(
                asset_id=uuid4(),
                kind=AttachmentKind.OTHER,
                original_name="x.bin",
                stream=io.BytesIO(b"x"),
            )

    def test_add_same_sha256_to_same_asset_raises_duplicate(
        self, att_svc: AttachmentService, asset
    ):
        att_svc.add(
            asset_id=asset.id,
            kind=AttachmentKind.PHOTO,
            original_name="a.jpg",
            stream=io.BytesIO(b"same-bytes"),
        )
        with pytest.raises(DuplicateError, match="已有相同内容"):
            att_svc.add(
                asset_id=asset.id,
                kind=AttachmentKind.PHOTO,
                original_name="b.jpg",  # 不同文件名，但 bytes 相同
                stream=io.BytesIO(b"same-bytes"),
            )

    def test_add_same_sha256_across_different_assets_succeeds(
        self,
        att_svc: AttachmentService,
        asset_svc: AssetService,
        asset,
        simple_type,
    ):
        other = asset_svc.register(name="X2", type_id=simple_type.id, custom_data={})

        first = att_svc.add(
            asset_id=asset.id,
            kind=AttachmentKind.DOC,
            original_name="shared.pdf",
            stream=io.BytesIO(b"shared"),
        )
        second = att_svc.add(
            asset_id=other.id,
            kind=AttachmentKind.DOC,
            original_name="shared.pdf",
            stream=io.BytesIO(b"shared"),
        )
        assert first.sha256 == second.sha256
        assert first.storage_path == second.storage_path
        assert first.id != second.id
```

- [ ] **Step 3.2: 运行测试确认失败**

Run: `uv run pytest tests/unit/test_attachment_service.py -v`

Expected: `ModuleNotFoundError: No module named 'asset_hub.services.attachment'`

- [ ] **Step 3.3: 创建 AttachmentRepository**

Create `src/asset_hub/repositories/attachment.py`:

```python
import uuid

from sqlmodel import Session, select

from asset_hub.models.attachment import Attachment


class AttachmentRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, att: Attachment) -> Attachment:
        self.session.add(att)
        self.session.flush()
        return att

    def get(self, attachment_id: uuid.UUID) -> Attachment | None:
        return self.session.get(Attachment, attachment_id)

    def list_by_asset(self, asset_id: uuid.UUID) -> list[Attachment]:
        stmt = (
            select(Attachment)
            .where(Attachment.asset_id == asset_id)
            .order_by(Attachment.uploaded_at.desc())
        )
        return list(self.session.exec(stmt).all())

    def find_by_asset_and_sha256(
        self, asset_id: uuid.UUID, sha256: str
    ) -> Attachment | None:
        stmt = (
            select(Attachment)
            .where(Attachment.asset_id == asset_id)
            .where(Attachment.sha256 == sha256)
        )
        return self.session.exec(stmt).first()

    def any_with_sha256(self, sha256: str) -> bool:
        stmt = select(Attachment.id).where(Attachment.sha256 == sha256).limit(1)
        return self.session.exec(stmt).first() is not None

    def delete(self, att: Attachment) -> None:
        self.session.delete(att)
        self.session.flush()
```

- [ ] **Step 3.4: 创建 AttachmentService.add**

Create `src/asset_hub/services/attachment.py`:

```python
import mimetypes
import uuid
from pathlib import Path
from typing import BinaryIO

from sqlmodel import Session

from asset_hub.errors import DuplicateError
from asset_hub.models.attachment import Attachment, AttachmentKind
from asset_hub.repositories.attachment import AttachmentRepository
from asset_hub.services.asset import AssetService
from asset_hub.storage.base import StorageAdapter


class AttachmentService:
    def __init__(self, session: Session, storage: StorageAdapter):
        self.session = session
        self.repo = AttachmentRepository(session)
        self.asset_svc = AssetService(session)
        self.storage = storage

    def add(
        self,
        asset_id: uuid.UUID,
        *,
        kind: AttachmentKind,
        original_name: str,
        stream: BinaryIO,
        mime_type: str | None = None,
    ) -> Attachment:
        # 1. 资产存在性（NotFoundError 会自然冒泡）
        self.asset_svc.get_asset(asset_id)

        # 2. 落盘（边写边算 sha256）
        ext = Path(original_name).suffix.lower()
        stored = self.storage.save(stream, original_ext=ext)

        # 3. 同资产同内容去重（UniqueConstraint 已兜底，此处给出更友好的错误）
        existing = self.repo.find_by_asset_and_sha256(asset_id, stored.sha256)
        if existing is not None:
            raise DuplicateError(
                f"附件已有相同内容: 资产 {asset_id} 已存在 sha256={stored.sha256} "
                f"的附件（id={existing.id}）"
            )

        # 4. MIME 兜底
        if not mime_type:
            guessed, _ = mimetypes.guess_type(original_name)
            mime_type = guessed or "application/octet-stream"

        att = Attachment(
            asset_id=asset_id,
            kind=kind,
            storage_path=stored.storage_path,
            sha256=stored.sha256,
            size=stored.size,
            mime_type=mime_type,
            original_name=original_name,
        )
        self.repo.add(att)
        self.session.commit()
        self.session.refresh(att)
        return att
```

- [ ] **Step 3.5: 运行测试确认通过**

Run: `uv run pytest tests/unit/test_attachment_service.py -v`

Expected: 6 tests PASS

- [ ] **Step 3.6: 提交**

```bash
git add src/asset_hub/repositories/attachment.py src/asset_hub/services/attachment.py tests/unit/test_attachment_service.py
git commit -m "$(cat <<'EOF'
feat(service): AttachmentService.add — 上传附件并去重

- AttachmentRepository 封装常用查询（list_by_asset / find_by_asset_and_sha256 / any_with_sha256）
- add 校验：资产存在；同资产同 sha256 显式 DuplicateError（UniqueConstraint 兜底）
- MIME 兜底：调用方显式 > mimetypes.guess_type > application/octet-stream
- 跨资产共享同一 sha256 合法，物理文件按内容寻址天然复用
EOF
)"
```

---

## Task 4: AttachmentService.list / get / delete (TDD)

**Files:**
- Modify: `src/asset_hub/services/attachment.py`
- Modify: `tests/unit/test_attachment_service.py`

- [ ] **Step 4.1: 追加失败测试**

Append to `tests/unit/test_attachment_service.py`:

```python
class TestList:
    def test_list_empty(self, att_svc: AttachmentService, asset):
        assert att_svc.list(asset_id=asset.id) == []

    def test_list_newest_first(self, att_svc: AttachmentService, asset):
        first = att_svc.add(
            asset_id=asset.id,
            kind=AttachmentKind.PHOTO,
            original_name="a.jpg",
            stream=io.BytesIO(b"a"),
        )
        second = att_svc.add(
            asset_id=asset.id,
            kind=AttachmentKind.PHOTO,
            original_name="b.jpg",
            stream=io.BytesIO(b"b"),
        )
        items = att_svc.list(asset_id=asset.id)
        assert [i.id for i in items] == [second.id, first.id]

    def test_list_nonexistent_asset_raises(self, att_svc: AttachmentService):
        with pytest.raises(NotFoundError):
            att_svc.list(asset_id=uuid4())


class TestGet:
    def test_get_returns_attachment(self, att_svc: AttachmentService, asset):
        att = att_svc.add(
            asset_id=asset.id,
            kind=AttachmentKind.OTHER,
            original_name="x.bin",
            stream=io.BytesIO(b"x"),
        )
        got = att_svc.get(att.id)
        assert got.id == att.id

    def test_get_missing_raises(self, att_svc: AttachmentService):
        with pytest.raises(NotFoundError):
            att_svc.get(uuid4())


class TestDelete:
    def test_delete_removes_db_row_and_file(
        self,
        att_svc: AttachmentService,
        storage: LocalFSStorage,
        asset,
    ):
        att = att_svc.add(
            asset_id=asset.id,
            kind=AttachmentKind.PHOTO,
            original_name="a.jpg",
            stream=io.BytesIO(b"a"),
        )
        full = storage.root / att.storage_path
        assert full.exists()

        att_svc.delete(att.id)

        assert (storage.root / att.storage_path).exists() is False
        with pytest.raises(NotFoundError):
            att_svc.get(att.id)

    def test_delete_keeps_file_if_shared_with_other_asset(
        self,
        att_svc: AttachmentService,
        asset_svc: AssetService,
        storage: LocalFSStorage,
        asset,
        simple_type,
    ):
        other = asset_svc.register(name="X2", type_id=simple_type.id, custom_data={})

        a = att_svc.add(
            asset_id=asset.id,
            kind=AttachmentKind.DOC,
            original_name="s.pdf",
            stream=io.BytesIO(b"shared"),
        )
        b = att_svc.add(
            asset_id=other.id,
            kind=AttachmentKind.DOC,
            original_name="s.pdf",
            stream=io.BytesIO(b"shared"),
        )
        shared_path = storage.root / a.storage_path

        att_svc.delete(a.id)

        assert shared_path.exists(), "文件仍被 other 资产引用，不应被删除"
        assert att_svc.get(b.id).id == b.id

    def test_delete_missing_raises(self, att_svc: AttachmentService):
        with pytest.raises(NotFoundError):
            att_svc.delete(uuid4())
```

- [ ] **Step 4.2: 运行测试确认失败**

Run: `uv run pytest tests/unit/test_attachment_service.py::TestList tests/unit/test_attachment_service.py::TestGet tests/unit/test_attachment_service.py::TestDelete -v`

Expected: `AttributeError: 'AttachmentService' object has no attribute 'list'`（及后续 get/delete 同理）

- [ ] **Step 4.3: 实现 list / get / delete**

Append to `src/asset_hub/services/attachment.py`:

```python
    def list(self, asset_id: uuid.UUID) -> list[Attachment]:
        self.asset_svc.get_asset(asset_id)
        return self.repo.list_by_asset(asset_id)

    def get(self, attachment_id: uuid.UUID) -> Attachment:
        from asset_hub.errors import NotFoundError

        att = self.repo.get(attachment_id)
        if att is None:
            raise NotFoundError(f"附件不存在: {attachment_id}")
        return att

    def delete(self, attachment_id: uuid.UUID) -> None:
        att = self.get(attachment_id)
        sha256 = att.sha256
        storage_path = att.storage_path

        self.repo.delete(att)
        self.session.commit()

        # 仅当没有其他 Attachment 引用同 sha256 时才删物理文件
        if not self.repo.any_with_sha256(sha256):
            self.storage.delete(storage_path)
```

并把 `NotFoundError` 提升到文件顶部的 imports（替换 `get` 方法内的 lazy import）：

把 `from asset_hub.errors import DuplicateError` 改为：

```python
from asset_hub.errors import DuplicateError, NotFoundError
```

并删掉 `get()` 方法内的 `from asset_hub.errors import NotFoundError` 那一行。

- [ ] **Step 4.4: 运行测试确认通过**

Run: `uv run pytest tests/unit/test_attachment_service.py -v`

Expected: 14 tests PASS（Task 3 的 6 条 + 本任务新增 8 条）

- [ ] **Step 4.5: 提交**

```bash
git add src/asset_hub/services/attachment.py tests/unit/test_attachment_service.py
git commit -m "$(cat <<'EOF'
feat(service): AttachmentService.list/get/delete

- list: 按资产倒序列出附件；NotFoundError 在资产不存在时
- get: 按 id 取，缺失抛 NotFoundError
- delete: 删 DB 行，仅当无其他附件引用同 sha256 时才物理删文件
EOF
)"
```

---

## Task 5: AttachmentRead DTO + CLI attachment add/list (TDD)

**Files:**
- Create: `src/asset_hub/api/schemas/attachment.py`
- Create: `src/asset_hub/cli/attachment_cmd.py`
- Modify: `src/asset_hub/cli/main.py`
- Create: `tests/cli/test_attachment_cli.py`

- [ ] **Step 5.1: 写失败测试**

Create `tests/cli/test_attachment_cli.py`:

```python
import json
from pathlib import Path
from uuid import uuid4

from typer.testing import CliRunner

from asset_hub.cli.main import app

runner = CliRunner()


def _define_type_and_asset() -> str:
    r = runner.invoke(app, ["type", "define", "--name", "笔记本", "--json"])
    type_id = json.loads(r.stdout)["data"]["id"]
    r = runner.invoke(
        app,
        ["asset", "register", "--name", "X1", "--type-id", type_id, "--json"],
    )
    return json.loads(r.stdout)["data"]["id"]


class TestAttachmentAdd:
    def test_add_photo(self, tmp_path: Path):
        asset_id = _define_type_and_asset()

        photo = tmp_path / "photo.jpg"
        photo.write_bytes(b"fake-jpeg-bytes")

        result = runner.invoke(
            app,
            [
                "attachment",
                "add",
                asset_id,
                "--file",
                str(photo),
                "--kind",
                "photo",
                "--json",
            ],
        )
        assert result.exit_code == 0, result.stdout
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert data["data"]["kind"] == "photo"
        assert data["data"]["size"] == len(b"fake-jpeg-bytes")
        assert data["data"]["mime_type"] == "image/jpeg"
        assert data["data"]["original_name"] == "photo.jpg"
        assert len(data["data"]["sha256"]) == 64

    def test_add_to_nonexistent_asset_exits_3(self, tmp_path: Path):
        photo = tmp_path / "a.jpg"
        photo.write_bytes(b"x")
        result = runner.invoke(
            app,
            [
                "attachment",
                "add",
                str(uuid4()),
                "--file",
                str(photo),
                "--kind",
                "photo",
                "--json",
            ],
        )
        assert result.exit_code == 3

    def test_add_duplicate_exits_1(self, tmp_path: Path):
        asset_id = _define_type_and_asset()
        photo = tmp_path / "a.jpg"
        photo.write_bytes(b"same")

        first = runner.invoke(
            app,
            [
                "attachment", "add", asset_id,
                "--file", str(photo), "--kind", "photo", "--json",
            ],
        )
        assert first.exit_code == 0

        second = runner.invoke(
            app,
            [
                "attachment", "add", asset_id,
                "--file", str(photo), "--kind", "photo", "--json",
            ],
        )
        assert second.exit_code == 1
        data = json.loads(second.stdout)
        assert data["success"] is False
        assert "相同内容" in data["error"]

    def test_add_bad_uuid_exits_2(self, tmp_path: Path):
        photo = tmp_path / "a.jpg"
        photo.write_bytes(b"x")
        result = runner.invoke(
            app,
            [
                "attachment", "add", "not-a-uuid",
                "--file", str(photo), "--kind", "photo", "--json",
            ],
        )
        assert result.exit_code == 2

    def test_add_missing_file_exits_2(self):
        asset_id = _define_type_and_asset()
        result = runner.invoke(
            app,
            [
                "attachment", "add", asset_id,
                "--file", "/no/such/file.jpg", "--kind", "photo", "--json",
            ],
        )
        # typer 的 exists=True 校验会以 usage error（exit 2）退出
        assert result.exit_code == 2


class TestAttachmentList:
    def test_list_empty(self):
        asset_id = _define_type_and_asset()
        result = runner.invoke(
            app, ["attachment", "list", asset_id, "--json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["data"] == []
        assert data["metadata"]["count"] == 0

    def test_list_newest_first(self, tmp_path: Path):
        asset_id = _define_type_and_asset()
        a = tmp_path / "a.jpg"
        a.write_bytes(b"a-bytes")
        b = tmp_path / "b.jpg"
        b.write_bytes(b"b-bytes")

        runner.invoke(app, [
            "attachment", "add", asset_id, "--file", str(a),
            "--kind", "photo", "--json",
        ])
        runner.invoke(app, [
            "attachment", "add", asset_id, "--file", str(b),
            "--kind", "photo", "--json",
        ])

        result = runner.invoke(app, [
            "attachment", "list", asset_id, "--json",
        ])
        data = json.loads(result.stdout)
        assert data["metadata"]["count"] == 2
        assert data["data"][0]["original_name"] == "b.jpg"
        assert data["data"][1]["original_name"] == "a.jpg"

    def test_list_nonexistent_exits_3(self):
        result = runner.invoke(
            app, ["attachment", "list", str(uuid4()), "--json"]
        )
        assert result.exit_code == 3
```

- [ ] **Step 5.2: 运行测试确认失败**

Run: `uv run pytest tests/cli/test_attachment_cli.py -v`

Expected: 全部失败（typer 报 "No such command 'attachment'"，exit_code 2 或 KeyError）

- [ ] **Step 5.3: 创建 AttachmentRead DTO**

Create `src/asset_hub/api/schemas/attachment.py`:

```python
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from asset_hub.models.attachment import AttachmentKind


class AttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    asset_id: UUID
    kind: AttachmentKind
    storage_path: str
    sha256: str
    size: int
    mime_type: str
    original_name: str
    uploaded_at: datetime
```

- [ ] **Step 5.4: 创建 CLI attachment 命令**

Create `src/asset_hub/cli/attachment_cmd.py`:

```python
from pathlib import Path
from typing import Annotated

import typer

from asset_hub.api.schemas.attachment import AttachmentRead
from asset_hub.cli.deps import cli_session, parse_uuid
from asset_hub.cli.envelope import print_error, print_result
from asset_hub.config import Settings
from asset_hub.errors import DuplicateError, NotFoundError
from asset_hub.models.attachment import AttachmentKind
from asset_hub.services.attachment import AttachmentService
from asset_hub.storage.local_fs import LocalFSStorage

attachment_app = typer.Typer(
    name="attachment", help="附件管理", no_args_is_help=True
)


def _att_to_dict(att) -> dict:
    return AttachmentRead.model_validate(att).model_dump(mode="json")


def _get_storage() -> LocalFSStorage:
    return LocalFSStorage(root=Settings().data_dir / "attachments")


@attachment_app.command("add")
def attachment_add(
    asset_id: Annotated[str, typer.Argument(help="资产 UUID")],
    file: Annotated[
        Path,
        typer.Option("--file", exists=True, dir_okay=False, readable=True, help="要上传的文件"),
    ],
    kind: Annotated[AttachmentKind, typer.Option(help="附件类型")] = AttachmentKind.OTHER,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """上传附件到指定资产。"""
    uid = parse_uuid(asset_id, json_output)
    storage = _get_storage()
    with cli_session() as session:
        svc = AttachmentService(session, storage)
        try:
            with file.open("rb") as fh:
                att = svc.add(
                    asset_id=uid,
                    kind=kind,
                    original_name=file.name,
                    stream=fh,
                )
        except NotFoundError as e:
            print_error(str(e), json_output, exit_code=3)
            return
        except DuplicateError as e:
            print_error(str(e), json_output, exit_code=1)
            return
    print_result(_att_to_dict(att), json_output)


@attachment_app.command("list")
def attachment_list(
    asset_id: Annotated[str, typer.Argument(help="资产 UUID")],
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """列出某资产的全部附件。"""
    uid = parse_uuid(asset_id, json_output)
    storage = _get_storage()
    with cli_session() as session:
        svc = AttachmentService(session, storage)
        try:
            items = svc.list(asset_id=uid)
        except NotFoundError as e:
            print_error(str(e), json_output, exit_code=3)
            return
    data = [_att_to_dict(a) for a in items]
    print_result(data, json_output, count=len(data))
```

- [ ] **Step 5.5: 挂载 attachment_app 到 CLI 根**

Overwrite `src/asset_hub/cli/main.py` with:

```python
import typer

from asset_hub.cli.asset_cmd import asset_app
from asset_hub.cli.attachment_cmd import attachment_app
from asset_hub.cli.type_cmd import type_app

app = typer.Typer(name="asset-hub", no_args_is_help=True)
app.add_typer(type_app, name="type")
app.add_typer(asset_app, name="asset")
app.add_typer(attachment_app, name="attachment")
```

- [ ] **Step 5.6: 运行 CLI 测试确认通过**

Run: `uv run pytest tests/cli/test_attachment_cli.py -v`

Expected: 8 tests PASS

- [ ] **Step 5.7: 提交**

```bash
git add src/asset_hub/api/schemas/attachment.py src/asset_hub/cli/attachment_cmd.py src/asset_hub/cli/main.py tests/cli/test_attachment_cli.py
git commit -m "$(cat <<'EOF'
feat(cli): attachment add/list 命令

- 顶层子命令 asset-hub attachment add/list（对齐 spec §6.1）
- --file 用 typer 的 exists 校验，非法路径直接 exit 2
- --kind 接受 photo|invoice|doc|other，默认 other
- 退出码：0/1（重复）/2（用法）/3（资产不存在）
- AttachmentRead DTO 在 CLI/API 间复用（ConfigDict(from_attributes=True)）
EOF
)"
```

---

## Task 6: API 路由（upload / list / metadata / download / delete）(TDD)

**Files:**
- Modify: `pyproject.toml`（加 `python-multipart` 依赖）
- Modify: `src/asset_hub/api/deps.py`
- Create: `src/asset_hub/api/routers/attachments.py`
- Modify: `src/asset_hub/api/app.py`
- Modify: `tests/api/conftest.py`（monkeypatch `ASSET_HUB_DATA_DIR`，防止污染真实 data/）
- Create: `tests/api/test_attachment_routes.py`

- [ ] **Step 6.0: 让 API 测试隔离 data_dir（避免污染真实 data/）**

Overwrite `tests/api/conftest.py` with:

```python
import pytest
from sqlmodel import Session, SQLModel, create_engine


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSET_HUB_DATA_DIR", str(tmp_path))

    from fastapi.testclient import TestClient

    from asset_hub.api.app import create_app
    from asset_hub.api.deps import get_session

    url = f"sqlite:///{tmp_path / 'test.db'}"
    engine = create_engine(url)
    SQLModel.metadata.create_all(engine)

    def _override_session():
        with Session(engine) as s:
            yield s

    app = create_app()
    app.dependency_overrides[get_session] = _override_session
    with TestClient(app) as c:
        yield c
```

变化：新增 `monkeypatch.setenv("ASSET_HUB_DATA_DIR", ...)`，让 `get_storage()` 内的 `Settings()` 读到 tmp_path。既有的 M1/M2a API 测试不碰 storage，加这一行对它们是无副作用增强。

- [ ] **Step 6.1: 加 python-multipart 依赖**

Modify `pyproject.toml`：在 `dependencies` 列表里追加 `"python-multipart>=0.0.19",`。

改后 `dependencies` 段应为：

```toml
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
    "sqlmodel>=0.0.22",
    "pydantic-settings>=2.7",
    "typer>=0.15",
    "rich>=13.9",
    "python-multipart>=0.0.19",
]
```

Run: `uv sync`

Expected: `python-multipart` 被装到虚拟环境。

- [ ] **Step 6.2: 写失败测试**

Create `tests/api/test_attachment_routes.py`:

```python
import io
from uuid import uuid4

from fastapi.testclient import TestClient


def _create_type_and_asset(client: TestClient) -> str:
    r = client.post("/api/types", json={"name": "笔记本"})
    type_id = r.json()["id"]
    r = client.post(
        "/api/assets",
        json={"name": "X1", "type_id": type_id, "custom_data": {}},
    )
    return r.json()["id"]


def _upload(client: TestClient, asset_id: str, content: bytes, *, kind: str = "photo", filename: str = "a.jpg"):
    return client.post(
        f"/api/assets/{asset_id}/attachments",
        data={"kind": kind},
        files={"file": (filename, io.BytesIO(content), "image/jpeg")},
    )


class TestUploadEndpoint:
    def test_upload_returns_201_and_metadata(self, client: TestClient):
        asset_id = _create_type_and_asset(client)
        resp = _upload(client, asset_id, b"fake-jpeg")
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["kind"] == "photo"
        assert data["size"] == len(b"fake-jpeg")
        assert data["mime_type"] == "image/jpeg"
        assert len(data["sha256"]) == 64
        assert data["original_name"] == "a.jpg"
        assert data["asset_id"] == asset_id

    def test_upload_to_missing_asset_404(self, client: TestClient):
        resp = _upload(client, str(uuid4()), b"x")
        assert resp.status_code == 404

    def test_upload_duplicate_same_content_409(self, client: TestClient):
        asset_id = _create_type_and_asset(client)
        _upload(client, asset_id, b"same")
        resp = _upload(client, asset_id, b"same")
        assert resp.status_code == 409


class TestListEndpoint:
    def test_list_empty(self, client: TestClient):
        asset_id = _create_type_and_asset(client)
        resp = client.get(f"/api/assets/{asset_id}/attachments")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_newest_first(self, client: TestClient):
        asset_id = _create_type_and_asset(client)
        _upload(client, asset_id, b"first", filename="a.jpg")
        _upload(client, asset_id, b"second", filename="b.jpg")

        resp = client.get(f"/api/assets/{asset_id}/attachments")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 2
        assert items[0]["original_name"] == "b.jpg"
        assert items[1]["original_name"] == "a.jpg"

    def test_list_missing_asset_404(self, client: TestClient):
        resp = client.get(f"/api/assets/{uuid4()}/attachments")
        assert resp.status_code == 404


class TestMetadataEndpoint:
    def test_get_returns_metadata(self, client: TestClient):
        asset_id = _create_type_and_asset(client)
        up = _upload(client, asset_id, b"abc").json()

        resp = client.get(f"/api/attachments/{up['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == up["id"]

    def test_get_missing_404(self, client: TestClient):
        resp = client.get(f"/api/attachments/{uuid4()}")
        assert resp.status_code == 404


class TestDownloadEndpoint:
    def test_download_returns_binary(self, client: TestClient):
        asset_id = _create_type_and_asset(client)
        content = b"binary-payload-123"
        up = _upload(client, asset_id, content).json()

        resp = client.get(f"/api/attachments/{up['id']}/content")
        assert resp.status_code == 200
        assert resp.content == content
        assert resp.headers["content-type"].startswith("image/jpeg")

    def test_download_missing_404(self, client: TestClient):
        resp = client.get(f"/api/attachments/{uuid4()}/content")
        assert resp.status_code == 404


class TestDeleteEndpoint:
    def test_delete_returns_204_and_removes(self, client: TestClient):
        asset_id = _create_type_and_asset(client)
        up = _upload(client, asset_id, b"xxx").json()

        resp = client.delete(f"/api/attachments/{up['id']}")
        assert resp.status_code == 204

        follow = client.get(f"/api/attachments/{up['id']}")
        assert follow.status_code == 404

    def test_delete_missing_404(self, client: TestClient):
        resp = client.delete(f"/api/attachments/{uuid4()}")
        assert resp.status_code == 404
```

- [ ] **Step 6.3: 运行测试确认失败**

Run: `uv run pytest tests/api/test_attachment_routes.py -v`

Expected: 全部 404 或 405（endpoint 未挂载）。

- [ ] **Step 6.4: 在 api/deps.py 加 storage / attachment service 依赖**

Overwrite `src/asset_hub/api/deps.py` with:

```python
from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlmodel import Session

from asset_hub.config import Settings
from asset_hub.db import get_engine
from asset_hub.services.attachment import AttachmentService
from asset_hub.storage.base import StorageAdapter
from asset_hub.storage.local_fs import LocalFSStorage


def get_session() -> Generator[Session, None, None]:
    with Session(get_engine()) as session:
        yield session


def get_storage() -> StorageAdapter:
    return LocalFSStorage(root=Settings().data_dir / "attachments")


def get_attachment_service(
    session: Annotated[Session, Depends(get_session)],
    storage: Annotated[StorageAdapter, Depends(get_storage)],
) -> AttachmentService:
    return AttachmentService(session, storage)
```

- [ ] **Step 6.5: 创建 routers/attachments.py**

Create `src/asset_hub/api/routers/attachments.py`:

```python
import mimetypes
import uuid
from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile
from fastapi.responses import StreamingResponse

from asset_hub.api.deps import get_attachment_service, get_storage
from asset_hub.api.schemas.attachment import AttachmentRead
from asset_hub.models.attachment import AttachmentKind
from asset_hub.services.attachment import AttachmentService
from asset_hub.storage.base import StorageAdapter

router = APIRouter()


def _iter_file(fh, chunk_size: int = 1 << 16) -> Iterator[bytes]:
    try:
        while chunk := fh.read(chunk_size):
            yield chunk
    finally:
        fh.close()


@router.post(
    "/assets/{asset_id}/attachments",
    status_code=201,
    response_model=AttachmentRead,
    tags=["attachments"],
)
def upload_attachment(
    asset_id: uuid.UUID,
    svc: Annotated[AttachmentService, Depends(get_attachment_service)],
    kind: Annotated[AttachmentKind, Form()] = AttachmentKind.OTHER,
    file: UploadFile = File(...),
):
    filename = file.filename or "unnamed"
    return svc.add(
        asset_id=asset_id,
        kind=kind,
        original_name=filename,
        stream=file.file,
        mime_type=file.content_type or None,
    )


@router.get(
    "/assets/{asset_id}/attachments",
    response_model=list[AttachmentRead],
    tags=["attachments"],
)
def list_attachments(
    asset_id: uuid.UUID,
    svc: Annotated[AttachmentService, Depends(get_attachment_service)],
):
    return svc.list(asset_id=asset_id)


@router.get(
    "/attachments/{attachment_id}",
    response_model=AttachmentRead,
    tags=["attachments"],
)
def get_attachment(
    attachment_id: uuid.UUID,
    svc: Annotated[AttachmentService, Depends(get_attachment_service)],
):
    return svc.get(attachment_id)


@router.get("/attachments/{attachment_id}/content", tags=["attachments"])
def download_attachment(
    attachment_id: uuid.UUID,
    svc: Annotated[AttachmentService, Depends(get_attachment_service)],
    storage: Annotated[StorageAdapter, Depends(get_storage)],
):
    att = svc.get(attachment_id)
    fh = storage.open(att.storage_path)
    media_type = att.mime_type or (
        mimetypes.guess_type(att.original_name)[0] or "application/octet-stream"
    )
    return StreamingResponse(_iter_file(fh), media_type=media_type)


@router.delete(
    "/attachments/{attachment_id}", status_code=204, tags=["attachments"]
)
def delete_attachment(
    attachment_id: uuid.UUID,
    svc: Annotated[AttachmentService, Depends(get_attachment_service)],
):
    svc.delete(attachment_id)
    return Response(status_code=204)
```

- [ ] **Step 6.6: 挂载路由**

Modify `src/asset_hub/api/app.py`：

- 修改 router 导入行，把 `from asset_hub.api.routers import assets, checkouts, types` 改为：

```python
from asset_hub.api.routers import assets, attachments, checkouts, types
```

- 在 `app.include_router(checkouts.router, ...)` 行之后追加：

```python
    app.include_router(attachments.router, prefix="/api", tags=["attachments"])
```

（注意：`attachments.router` 内部自己声明了 `/assets/{asset_id}/attachments` 与 `/attachments/{id}` 两类路径，因此前缀只用 `/api`。）

- [ ] **Step 6.7: 运行 API 测试确认通过**

Run: `uv run pytest tests/api/test_attachment_routes.py -v`

Expected: 12 tests PASS

- [ ] **Step 6.8: 回归全量测试**

Run: `uv run pytest -q`

Expected: M1 + M2a + M2b 全部测试通过，无回归。

- [ ] **Step 6.9: 提交**

```bash
git add pyproject.toml uv.lock src/asset_hub/api/deps.py src/asset_hub/api/routers/attachments.py src/asset_hub/api/app.py tests/api/conftest.py tests/api/test_attachment_routes.py
git commit -m "$(cat <<'EOF'
feat(api): 附件端点 upload/list/metadata/content/delete

- POST /api/assets/{id}/attachments  multipart 上传 → 201 + AttachmentRead
- GET  /api/assets/{id}/attachments  列出
- GET  /api/attachments/{id}         元数据
- GET  /api/attachments/{id}/content 下载文件（StreamingResponse）
- DELETE /api/attachments/{id}       删除 → 204
- 新增 python-multipart 依赖；api/deps 抽出 get_storage / get_attachment_service
EOF
)"
```

---

## Task 7: 收尾（lint + 手工烟测）

本任务不写新测试；目标是确保 lint 干净、OpenAPI 暴露新端点、CLI 真正可用。

- [ ] **Step 7.1: ruff 检查**

Run: `uv run ruff check .`

Expected: `All checks passed!`。若有报错，修复后重新运行。

- [ ] **Step 7.2: 全量测试（详细输出便于对照）**

Run: `uv run pytest -v`

Expected: 全绿。本里程碑新增测试合计 ≥ 34（模型 4 + storage 6 + service 14 + CLI 8 + API 12）。

- [ ] **Step 7.3: 手工烟测 CLI**

```bash
# 使用临时 DATA_DIR 避免污染真实数据
export ASSET_HUB_DATA_DIR=/tmp/asset-hub-smoke-m2b
rm -rf "$ASSET_HUB_DATA_DIR" && mkdir -p "$ASSET_HUB_DATA_DIR"

TYPE_ID=$(uv run asset-hub type define --name "笔记本" --json \
  | python -c "import sys,json; print(json.load(sys.stdin)['data']['id'])")
ASSET_ID=$(uv run asset-hub asset register --name "X1" --type-id "$TYPE_ID" --json \
  | python -c "import sys,json; print(json.load(sys.stdin)['data']['id'])")

# 造一个测试文件
echo "fake photo bytes $(date)" > /tmp/photo.jpg

# 上传
uv run asset-hub attachment add "$ASSET_ID" --file /tmp/photo.jpg --kind photo --json
# 期望：success=true、kind=photo、sha256=<64 hex>、mime_type=image/jpeg

# 重复上传应失败
uv run asset-hub attachment add "$ASSET_ID" --file /tmp/photo.jpg --kind photo --json
echo "exit=$?"
# 期望：success=false、error 含「相同内容」、exit=1

# 列出
uv run asset-hub attachment list "$ASSET_ID" --json
# 期望：count=1，包含刚才那条

# 检查磁盘布局
find "$ASSET_HUB_DATA_DIR/attachments" -type f
# 期望：<data_dir>/attachments/<yyyy>/<mm>/<sha256>.jpg
```

- [ ] **Step 7.4: 手工烟测 OpenAPI**

```bash
uv run uvicorn asset_hub.api.app:app --port 8000 &
UVICORN_PID=$!
sleep 1
curl -s http://localhost:8000/openapi.json | python -c "
import sys, json
spec = json.load(sys.stdin)
paths = list(spec['paths'].keys())
expected = [
    '/api/assets/{asset_id}/attachments',
    '/api/attachments/{attachment_id}',
    '/api/attachments/{attachment_id}/content',
]
for p in expected:
    assert p in paths, f'missing: {p}'
print('OK:', expected)
"
kill $UVICORN_PID
```

Expected: `OK: [...三条路径...]`。

- [ ] **Step 7.5: 手工烟测 API 上传 + 下载**

```bash
uv run uvicorn asset_hub.api.app:app --port 8000 &
UVICORN_PID=$!
sleep 1

# 准备类型和资产（走 JSON API，避免依赖 CLI 数据路径）
TYPE_ID=$(curl -s -X POST http://localhost:8000/api/types \
  -H 'Content-Type: application/json' \
  -d '{"name":"服务器"}' | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
ASSET_ID=$(curl -s -X POST http://localhost:8000/api/assets \
  -H 'Content-Type: application/json' \
  -d "{\"name\":\"S1\",\"type_id\":\"$TYPE_ID\",\"custom_data\":{}}" \
  | python -c "import sys,json; print(json.load(sys.stdin)['id'])")

# 上传
echo "api smoke payload $(date)" > /tmp/upload.txt
ATT_ID=$(curl -s -X POST "http://localhost:8000/api/assets/$ASSET_ID/attachments" \
  -F "kind=doc" \
  -F "file=@/tmp/upload.txt" \
  | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "uploaded: $ATT_ID"

# 下载并对比
curl -s -o /tmp/download.txt "http://localhost:8000/api/attachments/$ATT_ID/content"
diff /tmp/upload.txt /tmp/download.txt && echo "download OK"

# 删除
curl -s -o /dev/null -w "%{http_code}\n" -X DELETE "http://localhost:8000/api/attachments/$ATT_ID"
# 期望：204

# 再次 GET 应 404
curl -s -o /dev/null -w "%{http_code}\n" "http://localhost:8000/api/attachments/$ATT_ID"
# 期望：404

kill $UVICORN_PID
```

Expected: `download OK` + `204` + `404`。

- [ ] **Step 7.6: 若有修复，提交收尾**

如有 lint 或格式无害修正：

```bash
git add -u
git commit -m "chore: M2b 收尾——lint 与格式修正"
```

若无改动跳过此步骤。

---

## 自检清单

| 需求 / 来源                                                         | 对应 Task                                          |
| ------------------------------------------------------------------- | -------------------------------------------------- |
| `Attachment` 表结构（spec §5.2）                                    | Task 1                                             |
| `AttachmentKind` 枚举 photo/invoice/doc/other（spec §5.2）          | Task 1                                             |
| 同资产同内容不重复（UniqueConstraint + service 预校验）             | Task 1（约束）+ Task 3（service + 友好错误）       |
| 跨资产共享同一物理文件                                              | Task 1（测试覆盖）+ Task 2（按 sha256 寻址）       |
| `StorageAdapter` 抽象 + `LocalFSStorage`（spec §4 / §10）           | Task 2                                             |
| 存储路径 `<yyyy>/<mm>/<sha256>.<ext>`（spec §10）                   | Task 2                                             |
| AttachmentService CRUD + MIME 兜底                                  | Task 3（add）+ Task 4（list/get/delete）           |
| 删除时保证不误删共享文件                                            | Task 4（测试覆盖 + any_with_sha256）               |
| CLI `attachment add / list`（spec §6.1）                            | Task 5                                             |
| CLI `--json` 标准信封（spec §6.2）                                  | Task 5 测试覆盖                                    |
| CLI 退出码 0/1/2/3（spec §6.3，CLAUDE.md）                          | Task 5 测试覆盖                                    |
| API 端点（spec §11 M2 目标）                                        | Task 6                                             |
| 异常映射 NotFound→404 / Duplicate→409 / Validation→422（CLAUDE.md） | 已在 M2a 注册；Task 6 测试覆盖                     |
| ORM/DTO 隔离（AttachmentRead 基于 attributes）                      | Task 5（DTO）+ Task 6（router 用 `response_model`）|
| Service 层为唯一事实源，CLI 不走 HTTP（CLAUDE.md §1）               | Task 5 直接 `from asset_hub.services.attachment`   |

**明确不在本计划范围内：**

- Web 前端消费附件端点 → M2c
- CLI `attachment delete / get / download` → 暂不做，需要时再加（API 已暴露）
- 多种存储后端（S3/MinIO）→ v2+（`StorageAdapter` 抽象已为此预留）
- 附件缩略图生成 → M3+
- 附件 MIME 严格白名单 / 最大体积校验 → v2+（单用户场景放松）
