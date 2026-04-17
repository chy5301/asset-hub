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
