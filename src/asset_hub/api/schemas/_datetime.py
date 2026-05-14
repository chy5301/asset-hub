"""共享 datetime 处理：SQLite 存 naive datetime（即便 default_factory 用 datetime.now(UTC)
存进去也丢 tzinfo），Pydantic 序列化时若无 tz designator 会让前端 parseISO 按本地时区解析，
造成时区漂移（如 UTC 03:53 被当作北京 03:53 显示）。

UtcDatetime 用 BeforeValidator 把 naive datetime 视作 UTC 补回 tzinfo，序列化即带 +00:00 后缀。
"""

from datetime import UTC, datetime
from typing import Annotated

from pydantic import BeforeValidator


def _ensure_utc(v: object) -> object:
    if isinstance(v, datetime) and v.tzinfo is None:
        return v.replace(tzinfo=UTC)
    return v


UtcDatetime = Annotated[datetime, BeforeValidator(_ensure_utc)]
