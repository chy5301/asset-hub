from __future__ import annotations

import shutil
import socket
import subprocess
import sys
from collections.abc import Sequence
from enum import StrEnum
from pathlib import Path

import psutil

DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200
CREATE_NO_WINDOW = 0x08000000

# Windows detach 选 CREATE_NO_WINDOW + CREATE_NEW_PROCESS_GROUP 而非 DETACHED_PROCESS：
# DETACHED_PROCESS 完全剥离 console handle，会让 .cmd / .bat 等批处理 wrapper
# （如 pnpm.cmd / npm.cmd）启动后立即崩溃；CREATE_NO_WINDOW 同样隐藏窗口但保留
# console handle，对批处理与 native exe 都安全。CREATE_NEW_PROCESS_GROUP 让父
# CLI 退出后子进程不被父终端的 Ctrl+C 信号传递误杀。


class KillMethod(StrEnum):
    SIGTERM = "sigterm"
    SIGKILL = "sigkill"


class KillFailedError(RuntimeError):
    """SIGKILL 后仍存活的极端情况。"""


class CommandNotFoundError(RuntimeError):
    """指定的可执行文件在 PATH 上找不到。"""


def _resolve_executable(name: str) -> str:
    """在 PATH 上解析可执行文件名为完整路径。

    Windows 必需：subprocess.Popen 不会自动解析 PATHEXT（如 pnpm.cmd / pnpm.ps1），
    必须给出含扩展名的完整路径才能起；shutil.which 处理 PATHEXT 解析。
    Unix 上若 name 已含路径分隔符则直接返回，否则 shutil.which 也是同样的查 PATH。
    """
    if "/" in name or "\\" in name:
        return name
    resolved = shutil.which(name)
    if resolved is None:
        raise CommandNotFoundError(f"executable not found on PATH: {name}")
    return resolved


def start_detached(
    cmd: Sequence[str],
    *,
    log_file: Path,
    cwd: Path,
) -> int:
    """跨平台后台启动子进程，返回 PID；stdout/stderr 重定向到 log_file（append）。"""
    log_file.parent.mkdir(parents=True, exist_ok=True)
    fd = open(log_file, "ab")  # binary append; uvicorn / pnpm 自带编码

    cmd_list = list(cmd)
    cmd_list[0] = _resolve_executable(cmd_list[0])

    if sys.platform == "win32":
        proc = subprocess.Popen(
            cmd_list,
            stdout=fd,
            stderr=subprocess.STDOUT,
            creationflags=CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP,
            cwd=str(cwd),
            close_fds=True,
        )
    else:
        proc = subprocess.Popen(
            cmd_list,
            stdout=fd,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            cwd=str(cwd),
        )
    return proc.pid


def is_port_in_use(port: int) -> bool:
    """检查指定端口是否被占用（IPv4 127.0.0.1 或 IPv6 ::1 任一被占即 True）。

    Vite 8.x dev 默认只监听 IPv6 ::1；uvicorn 显式 --host 绑 IPv4 127.0.0.1。
    任一栈被占用都需要识别，否则会出现 "IPv4 探测显示空闲但 IPv6 已被占" 的漏检，
    导致 Vite 偷偷 fallback 到下一个端口而 PID 文件撒谎。

    系统级 IPv6 不可用（容器、特殊网络栈）时，AF_INET6 socket 创建即抛 OSError，
    捕获后视为"那一栈不占"继续 IPv4 探测——graceful degrade 不让该函数变成系统
    可用性 gate。
    """
    for family, host in (
        (socket.AF_INET, "127.0.0.1"),
        (socket.AF_INET6, "::1"),
    ):
        try:
            s = socket.socket(family, socket.SOCK_STREAM)
        except OSError:
            continue
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
