from __future__ import annotations

import time
from dataclasses import dataclass
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener

SLEEP_INTERVALS = [0.2, 0.5, 1.0, 1.0, 2.0, 2.0, 3.0]
PROBE_TIMEOUT_PER_CALL = 1.0
STATUS_PROBE_TIMEOUT = 2.0

# 强制不走 HTTP_PROXY / http_proxy 环境变量。
# probe 目标永远是 loopback（127.0.0.1）；用户系统若设了 HTTP 代理（如 7890），
# urllib 默认会拿环境变量 routed → 代理无法转发到本机内部端口 → 返回 503/timeout
# → probe 误判服务没起。loopback 流量必须 bypass 代理。
_NO_PROXY_OPENER = build_opener(ProxyHandler({}))


@dataclass
class ProbeResult:
    ok: bool


def _open(url: str, timeout: float):
    return _NO_PROXY_OPENER.open(url, timeout=timeout)


def probe_until_ready(url: str) -> ProbeResult:
    """渐进退避轮询直到 200 或全部 interval 用完（累计 ~10s）。"""
    for interval in SLEEP_INTERVALS:
        time.sleep(interval)
        try:
            with _open(url, timeout=PROBE_TIMEOUT_PER_CALL) as r:
                if r.status == 200:
                    return ProbeResult(ok=True)
        except (TimeoutError, URLError, ConnectionRefusedError, OSError):
            continue
    return ProbeResult(ok=False)


def probe_once(url: str, timeout: float = STATUS_PROBE_TIMEOUT) -> bool:
    """status 命令使用，单次探测无重试。"""
    try:
        with _open(url, timeout=timeout) as r:
            return r.status == 200
    except (TimeoutError, URLError, ConnectionRefusedError, OSError):
        return False
