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
