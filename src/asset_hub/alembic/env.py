from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlmodel import SQLModel

from asset_hub.config import Settings

# 显式导入所有模型，让 metadata 包含
from asset_hub.models import asset, asset_type, attachment, state_transition  # noqa: F401

config = context.config

# 用 Settings 覆盖 alembic.ini 里的 sqlalchemy.url
settings = Settings()
config.set_main_option("sqlalchemy.url", settings.db_url)

if config.config_file_name is not None and config.get_section("loggers"):
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # SQLite 必需，让 alembic 用 batch_alter_table
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """同步模式：v1 单线程 SQLite 不需要 async；保留同步入口。"""
    from sqlalchemy import create_engine

    connectable = create_engine(
        config.get_main_option("sqlalchemy.url"), poolclass=pool.NullPool
    )
    with connectable.connect() as connection:
        do_run_migrations(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
