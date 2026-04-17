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
