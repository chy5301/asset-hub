"""Frozen（PyInstaller）感知的路径解析。

两类资源分开处理：
- 只读资源（frontend/dist 等包外资源）：resource_root() = _MEIPASS（frozen）/ 仓库根（源码）
- 可写数据（DB/附件/日志）：data_root() = exe 同级 ./data（frozen）/ cwd 下 ./data（源码）
包内资源（如 alembic）不走这里，按包目录 `Path(asset_hub.__file__).parent` 解析（见 migrate.py）。
"""

import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def resource_root() -> Path:
    """只读资源根。frozen → sys._MEIPASS（onedir/onefile 均设置）；源码 → 仓库根。"""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parents[2]


def resource_path(*parts: str) -> Path:
    return resource_root().joinpath(*parts)


def data_root() -> Path:
    """可写数据根。frozen → exe 同级 ./data；源码 → cwd 下 ./data（等价现状 Path("data")）。

    无自动回退——exe 同级不可写时由启动预检（PR3）弹框提示用户移动文件夹。
    """
    if is_frozen():
        return Path(sys.executable).resolve().parent / "data"
    return Path("data")


def is_writable_dir(path: Path) -> bool:
    """目标目录能否创建并写入：mkdir(parents=True) 后 touch 测试文件再删。best-effort。"""
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write-test"
        probe.touch()
        probe.unlink()
        return True
    except OSError:
        return False
