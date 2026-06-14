"""进程内 uvicorn：后台线程跑 Server + /api/healthz 轮询判就绪。

不传字符串 app 路径（"asset_hub.api.app:app"），直接传 create_app() 对象——
绕开 uvicorn 字符串动态 import，让 PyInstaller 走静态图收集 routers。
"""

import socket
import threading

import uvicorn

from asset_hub.api.app import create_app
from asset_hub.probe import probe_until_ready


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class BackgroundServer:
    def __init__(self, host: str = "127.0.0.1", port: int | None = None) -> None:
        self.host = host
        self.port = port if port is not None else find_free_port()
        config = uvicorn.Config(
            create_app(),
            host=self.host,
            port=self.port,
            reload=False,
            workers=1,
            # console=False 的 windowed exe 下 sys.stdout/stderr=None：uvicorn 默认
            # dictConfig 构造 ColourizedFormatter 会调 sys.stdout.isatty() → 崩。
            # 关掉自带 logging 配置 + access_log，彻底规避启动期 AttributeError。
            log_config=None,
            access_log=False,
        )
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(target=self._server.run, daemon=True)

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}/"

    def start(self) -> None:
        self._thread.start()

    def wait_until_ready(self) -> bool:
        """轮询 /api/healthz 直到就绪。复用 asset_hub.probe（退避重试 + 绕过 HTTP 代理：
        loopback 探测若走系统代理会被吞 → 误判超时，对设了代理的用户尤其致命）。"""
        return probe_until_ready(f"{self.url}api/healthz").ok

    def stop(self) -> None:
        self._server.should_exit = True
        if self._thread.is_alive():
            self._thread.join(timeout=5.0)  # 等线程真正收束，"干净退出"才名副其实
