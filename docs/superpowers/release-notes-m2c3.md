# M2c-3 部署手工干预清单

## 升级前（停服）

1. 备份数据库：`cp data/asset_hub.db data/asset_hub.db.<日期>.bak`
2. 用 SQL 给每个 AssetType 显式补 code_prefix（避免 fallback 派生丑陋）：

   ```bash
   sqlite3 data/asset_hub.db
   ```

   ```sql
   UPDATE asset_types SET code_prefix = 'NB' WHERE name = '笔记本电脑';
   UPDATE asset_types SET code_prefix = 'PJ' WHERE name = '投影仪';
   UPDATE asset_types SET code_prefix = 'MS' WHERE name = '鼠标';
   -- 按实际数据补全
   ```

   注意：如果 step 2 已被 migration step 1a 加了 code_prefix 列（仅在跑过部分 migration 后），可直接 UPDATE。如果还没加列，跑 alembic 中途出 RuntimeError 时再补。

## 升级

```bash
uv run alembic upgrade head
```

## 升级后验证

```bash
uv run python -c "
from asset_hub.db import get_engine
from sqlmodel import Session, select
from asset_hub.models.asset_type import AssetType
from asset_hub.models.asset import Asset
s = Session(get_engine())
print('TYPES:')
for t in s.exec(select(AssetType)).all():
    print(' ', t.name, t.code_prefix)
print('ASSETS:')
for a in s.exec(select(Asset)).all():
    print(' ', a.asset_code, a.name, '| acquired_at:', a.acquired_at)
"
```

## 回滚（如需）

```bash
uv run alembic downgrade -1
cp data/asset_hub.db.<日期>.bak data/asset_hub.db
```

## 补充：alembic post_write_hooks ruff_format 不工作

`alembic.ini` 中的 `[post_write_hooks] ruff_format` 当前不工作（ruff 没注册 console_scripts entrypoint）。新生成 migration 文件后**手工跑 `uv run ruff format <文件>`**。Task 1 / Task 8 都踩过这个，留作 follow-up。
