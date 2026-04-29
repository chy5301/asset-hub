from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path

_TAIL_BYTES_PER_LINE_ESTIMATE = 200


def rotate_log(log_path: Path) -> None:
    """启动次数轮转：log → log.1（覆盖旧 .1），不动其他代。"""
    if not log_path.exists():
        return
    rotated = log_path.with_suffix(log_path.suffix + ".1")
    if rotated.exists():
        rotated.unlink()
    log_path.rename(rotated)


def tail_lines(log_path: Path, n: int) -> list[str]:
    """读取文件最后 N 行；文件不存在或为空返回 []."""
    if not log_path.exists():
        return []
    size = log_path.stat().st_size
    if size == 0:
        return []
    chunk = min(size, _TAIL_BYTES_PER_LINE_ESTIMATE * n)
    with log_path.open("rb") as f:
        f.seek(max(0, size - chunk))
        data = f.read()
    text = data.decode("utf-8", errors="replace")
    lines = text.splitlines()
    return lines[-n:]


def follow_log(log_path: Path, sleep_interval: float = 0.1) -> Iterator[str]:
    """追加模式 tail -f；遇 EOF 不退出，靠 KeyboardInterrupt 退出。"""
    if not log_path.exists():
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.touch()
    with log_path.open("r", encoding="utf-8", errors="replace") as f:
        f.seek(0, 2)  # SEEK_END
        while True:
            line = f.readline()
            if not line:
                time.sleep(sleep_interval)
                continue
            yield line
