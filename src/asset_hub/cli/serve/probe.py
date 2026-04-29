from __future__ import annotations

import time
from dataclasses import dataclass
from urllib.error import URLError
from urllib.request import urlopen

SLEEP_INTERVALS = [0.2, 0.5, 1.0, 1.0, 2.0, 2.0, 3.0]
PROBE_TIMEOUT_PER_CALL = 1.0
STATUS_PROBE_TIMEOUT = 2.0


@dataclass
class ProbeResult:
    ok: bool


def probe_until_ready(url: str) -> ProbeResult:
    """渐进退避轮询直到 200 或全部 interval 用完（累计 ~10s）。"""
    for interval in SLEEP_INTERVALS:
        time.sleep(interval)
        try:
            with urlopen(url, timeout=PROBE_TIMEOUT_PER_CALL) as r:
                if r.status == 200:
                    return ProbeResult(ok=True)
        except (TimeoutError, URLError, ConnectionRefusedError, OSError):
            continue
    return ProbeResult(ok=False)


def probe_once(url: str, timeout: float = STATUS_PROBE_TIMEOUT) -> bool:
    """status 命令使用，单次探测无重试。"""
    try:
        with urlopen(url, timeout=timeout) as r:
            return r.status == 200
    except (TimeoutError, URLError, ConnectionRefusedError, OSError):
        return False
