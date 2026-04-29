from __future__ import annotations

import socket
import subprocess
import sys
from collections.abc import Sequence
from enum import StrEnum
from pathlib import Path

import psutil

DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200


class KillMethod(StrEnum):
    SIGTERM = "sigterm"
    SIGKILL = "sigkill"


class KillFailedError(RuntimeError):
    """SIGKILL 后仍存活的极端情况。"""


def start_detached(
    cmd: Sequence[str],
    *,
    log_file: Path,
    cwd: Path,
) -> int:
    """跨平台后台启动子进程，返回 PID；stdout/stderr 重定向到 log_file（append）。"""
    log_file.parent.mkdir(parents=True, exist_ok=True)
    fd = open(log_file, "ab")  # binary append; uvicorn / pnpm 自带编码

    if sys.platform == "win32":
        proc = subprocess.Popen(
            list(cmd),
            stdout=fd,
            stderr=subprocess.STDOUT,
            creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
            cwd=str(cwd),
            close_fds=True,
        )
    else:
        proc = subprocess.Popen(
            list(cmd),
            stdout=fd,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            cwd=str(cwd),
        )
    return proc.pid


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """检查 host:port 是否被占用（true = 已占用）。"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.5)
    try:
        s.bind((host, port))
    except OSError:
        return True
    finally:
        s.close()
    return False


def kill_tree(pid: int, timeout: float = 5.0) -> KillMethod:
    """递归 SIGTERM 后回退 SIGKILL；返回最终采用的方法；KillFailedError 表示 SIGKILL 也失败。"""
    try:
        proc = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return KillMethod.SIGTERM  # 已死视为成功

    children = []
    try:
        children = proc.children(recursive=True)
    except psutil.NoSuchProcess:
        pass

    targets = [proc] + children
    for p in targets:
        try:
            p.terminate()
        except psutil.NoSuchProcess:
            pass

    _, alive = psutil.wait_procs(targets, timeout=timeout)
    if not alive:
        return KillMethod.SIGTERM

    for p in alive:
        try:
            p.kill()
        except psutil.NoSuchProcess:
            pass

    _, alive2 = psutil.wait_procs(alive, timeout=2.0)
    if alive2:
        raise KillFailedError(
            f"failed to kill {len(alive2)} process(es) after SIGKILL: "
            f"{[p.pid for p in alive2]}"
        )
    return KillMethod.SIGKILL
