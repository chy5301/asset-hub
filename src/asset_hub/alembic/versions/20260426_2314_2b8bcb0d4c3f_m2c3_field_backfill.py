"""m2c3_field_backfill

Revision ID: 2b8bcb0d4c3f
Revises: 492867df5ecb
Create Date: 2026-04-26 23:14:16.122719

四字段补齐 + 旧数据回填：
1. AssetType.code_prefix（必填、unique；旧数据要手工补 prefix，否则 raise 提示运维 SQL 直填）
2. Asset.asset_code（必填、unique；按 type + created_at 顺序回填 {prefix}-{seq:03d}）
3. Asset.acquired_at（nullable；不回填——"不知道时不填"）
4. Asset.current_checkout_id（nullable FK；扫描 status=IN_USE 的回填最新未归还 record）
"""

import re
from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# code_prefix 必须满足 ^[A-Z]{2,4}$（与 service 层校验对齐）。
# Python str.isalpha()/isupper() 对 CJK 字符返回 True，必须用 ASCII 严格 regex 守门。
_PREFIX_RE = re.compile(r"^[A-Z]{2,4}$")

# revision identifiers, used by Alembic.
revision: str = "2b8bcb0d4c3f"
down_revision: str | Sequence[str] | None = "492867df5ecb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()

    # ===== Step 1: AssetType.code_prefix =====
    # 1a. 加 nullable 列（先放进去，再回填，再改 not null + unique）
    with op.batch_alter_table("asset_types", schema=None) as batch:
        batch.add_column(
            sa.Column("code_prefix", sqlmodel.sql.sqltypes.AutoString(), nullable=True)
        )

    # 1b. 旧数据回填——派生候选：name 首字母大写 + "X"，不合法或撞车则强制运维手工补。
    #     v1 单用户场景，与其写一坨脆弱派生不如让运维填精确 prefix。
    types = bind.execute(
        sa.text(
            "SELECT id, name FROM asset_types WHERE code_prefix IS NULL ORDER BY created_at"
        )
    ).fetchall()
    used_prefixes = set(
        r[0]
        for r in bind.execute(
            sa.text("SELECT code_prefix FROM asset_types WHERE code_prefix IS NOT NULL")
        ).fetchall()
    )
    for t in types:
        first = t.name[0].upper() if t.name else "X"
        candidate = (first + "X")[:2]
        if not _PREFIX_RE.fullmatch(candidate) or candidate in used_prefixes:
            raise RuntimeError(
                f"无法为 type '{t.name}' 派生合法 code_prefix（^[A-Z]{{2,4}}$），"
                f"请先用 SQL 手工补：UPDATE asset_types SET code_prefix='NB' "
                f"WHERE id='{t.id}'  -- 替换 NB 为该类型的实际前缀（2-4 个 ASCII 大写字母）"
            )
        used_prefixes.add(candidate)
        bind.execute(
            sa.text("UPDATE asset_types SET code_prefix = :p WHERE id = :i"),
            {"p": candidate, "i": str(t.id)},
        )

    # 1c. 改为 not null + unique（batch_alter_table 在 SQLite 下重建表）
    with op.batch_alter_table("asset_types", schema=None) as batch:
        batch.alter_column(
            "code_prefix",
            existing_type=sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
        )
        batch.create_index("ix_asset_types_code_prefix", ["code_prefix"], unique=True)

    # ===== Step 2: Asset.asset_code =====
    # 2a. 加 nullable 列
    with op.batch_alter_table("assets", schema=None) as batch:
        batch.add_column(
            sa.Column("asset_code", sqlmodel.sql.sqltypes.AutoString(), nullable=True)
        )

    # 2b. 按 type_id + created_at 顺序回填 {prefix}-{seq:03d}
    rows = bind.execute(
        sa.text(
            "SELECT a.id, a.type_id, t.code_prefix "
            "FROM assets a JOIN asset_types t ON t.id = a.type_id "
            "ORDER BY a.type_id, a.created_at"
        )
    ).fetchall()
    seq_by_type = {}
    for r in rows:
        type_key = str(r.type_id)
        seq_by_type[type_key] = seq_by_type.get(type_key, 0) + 1
        code = f"{r.code_prefix}-{seq_by_type[type_key]:03d}"
        bind.execute(
            sa.text("UPDATE assets SET asset_code = :c WHERE id = :i"),
            {"c": code, "i": str(r.id)},
        )

    # 2c. 改 not null + unique
    with op.batch_alter_table("assets", schema=None) as batch:
        batch.alter_column(
            "asset_code",
            existing_type=sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
        )
        batch.create_index("ix_assets_asset_code", ["asset_code"], unique=True)

    # ===== Step 3: Asset.acquired_at =====
    with op.batch_alter_table("assets", schema=None) as batch:
        batch.add_column(sa.Column("acquired_at", sa.Date(), nullable=True))
    # 不回填——保持 null，"不知道时不填"

    # ===== Step 4: Asset.current_checkout_id =====
    with op.batch_alter_table("assets", schema=None) as batch:
        batch.add_column(sa.Column("current_checkout_id", sa.Uuid(), nullable=True))
        batch.create_foreign_key(
            "fk_assets_current_checkout_id",
            "checkout_records",
            ["current_checkout_id"],
            ["id"],
        )
        batch.create_index("ix_assets_current_checkout_id", ["current_checkout_id"])

    # 4b. 扫描 IN_USE 资产，回填最近一条未归还的 CheckoutRecord.id
    in_use = bind.execute(
        sa.text(
            "SELECT a.id, "
            "  (SELECT cr.id FROM checkout_records cr "
            "   WHERE cr.asset_id = a.id AND cr.returned_at IS NULL "
            "   ORDER BY cr.checked_out_at DESC LIMIT 1) AS rec_id "
            "FROM assets a WHERE a.status = 'IN_USE'"
        )
    ).fetchall()
    for r in in_use:
        if r.rec_id is not None:
            bind.execute(
                sa.text("UPDATE assets SET current_checkout_id = :rid WHERE id = :aid"),
                {"rid": str(r.rec_id), "aid": str(r.id)},
            )


def downgrade() -> None:
    """允许回滚到 baseline（删除新列）。"""
    with op.batch_alter_table("assets", schema=None) as batch:
        batch.drop_index("ix_assets_current_checkout_id")
        batch.drop_constraint("fk_assets_current_checkout_id", type_="foreignkey")
        batch.drop_column("current_checkout_id")
        batch.drop_column("acquired_at")
        batch.drop_index("ix_assets_asset_code")
        batch.drop_column("asset_code")
    with op.batch_alter_table("asset_types", schema=None) as batch:
        batch.drop_index("ix_asset_types_code_prefix")
        batch.drop_column("code_prefix")
