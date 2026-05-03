"""m3a_state_machine

Revision ID: c6c0960805a9
Revises: 2ec8fc27d0f6
Create Date: 2026-05-04 07:27:31.985840

M3a 纯 schema 变更：
1. AssetStatus enum 加 DISPOSED（5 态）
2. Asset 删 current_checkout_id 列 + 索引（不再依赖单条 checkout 引用）
3. 删除旧 checkout_records 表
4. 创建 state_transition_records 表（10 transition kind + 5 态 from/to + closes_transition_id 自引用）

注意：autogenerate 在当前 metadata 下无法生成 drop_table('checkout_records')
（CheckoutRecord 模型已先于本迁移删除），因此手工编写。SQLite 走 batch_alter_table。
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c6c0960805a9"
down_revision: str | Sequence[str] | None = "2ec8fc27d0f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # ===== 1. assets：加 DISPOSED enum + 删 current_checkout_id =====
    with op.batch_alter_table("assets", schema=None) as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=sa.Enum(
                "IN_USE", "IDLE", "MAINTENANCE", "RETIRED", name="assetstatus"
            ),
            type_=sa.Enum(
                "IN_USE",
                "IDLE",
                "MAINTENANCE",
                "RETIRED",
                "DISPOSED",
                name="assetstatus",
            ),
            existing_nullable=False,
        )
        batch_op.drop_index("ix_assets_current_checkout_id")
        batch_op.drop_column("current_checkout_id")

    # ===== 2. 删 checkout_records 表 =====
    op.drop_index("ix_one_open_checkout_per_asset", table_name="checkout_records")
    op.drop_index("ix_checkout_records_asset_id", table_name="checkout_records")
    op.drop_index("ix_checkout_records_returned_at", table_name="checkout_records")
    op.drop_table("checkout_records")

    # ===== 3. 建 state_transition_records 表 =====
    op.create_table(
        "state_transition_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "CHECKOUT_INTERNAL",
                "CHECKOUT_EXTERNAL",
                "RETURN",
                "SEND_TO_MAINTENANCE",
                "RECOVER_FROM_MAINTENANCE",
                "RETIRE",
                "REINSTATE",
                "DISPOSE",
                "RELOCATE",
                "TRANSFER_HOLDER",
                name="transitionkind",
            ),
            nullable=False,
        ),
        sa.Column(
            "from_status",
            sa.Enum(
                "IN_USE",
                "IDLE",
                "MAINTENANCE",
                "RETIRED",
                "DISPOSED",
                name="assetstatus",
            ),
            nullable=False,
        ),
        sa.Column(
            "to_status",
            sa.Enum(
                "IN_USE",
                "IDLE",
                "MAINTENANCE",
                "RETIRED",
                "DISPOSED",
                name="assetstatus",
            ),
            nullable=False,
        ),
        sa.Column("from_holder", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("to_holder", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("from_location", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("to_location", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("note", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("due_at", sa.DateTime(), nullable=True),
        sa.Column("closes_transition_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.ForeignKeyConstraint(
            ["closes_transition_id"], ["state_transition_records.id"]
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_state_transition_records_asset_id",
        "state_transition_records",
        ["asset_id"],
    )
    op.create_index(
        "ix_state_transition_records_created_at",
        "state_transition_records",
        ["created_at"],
    )
    op.create_index(
        "ix_state_transition_records_closes_transition_id",
        "state_transition_records",
        ["closes_transition_id"],
    )
    op.create_index(
        "ix_transition_asset_created",
        "state_transition_records",
        ["asset_id", "created_at"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    # ===== 反向 3：drop state_transition_records =====
    op.drop_index("ix_transition_asset_created", table_name="state_transition_records")
    op.drop_index(
        "ix_state_transition_records_closes_transition_id",
        table_name="state_transition_records",
    )
    op.drop_index(
        "ix_state_transition_records_created_at",
        table_name="state_transition_records",
    )
    op.drop_index(
        "ix_state_transition_records_asset_id",
        table_name="state_transition_records",
    )
    op.drop_table("state_transition_records")

    # ===== 反向 2：recreate checkout_records（与 m2c3 + 2ec8fc27d0f6 后状态一致）=====
    op.create_table(
        "checkout_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("checked_out_at", sa.DateTime(), nullable=False),
        sa.Column("returned_at", sa.DateTime(), nullable=True),
        sa.Column("expected_return_at", sa.DateTime(), nullable=True),
        sa.Column("holder", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("location", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("note", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("return_location", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("return_receiver", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_checkout_records_returned_at",
        "checkout_records",
        ["returned_at"],
    )
    op.create_index("ix_checkout_records_asset_id", "checkout_records", ["asset_id"])
    op.create_index(
        "ix_one_open_checkout_per_asset",
        "checkout_records",
        ["asset_id"],
        unique=True,
        sqlite_where=sa.text("returned_at IS NULL"),
    )

    # ===== 反向 1：assets 回退 status enum + 加回 current_checkout_id =====
    with op.batch_alter_table("assets", schema=None) as batch_op:
        batch_op.add_column(sa.Column("current_checkout_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_assets_current_checkout_id",
            "checkout_records",
            ["current_checkout_id"],
            ["id"],
        )
        batch_op.create_index("ix_assets_current_checkout_id", ["current_checkout_id"])
        batch_op.alter_column(
            "status",
            existing_type=sa.Enum(
                "IN_USE",
                "IDLE",
                "MAINTENANCE",
                "RETIRED",
                "DISPOSED",
                name="assetstatus",
            ),
            type_=sa.Enum(
                "IN_USE", "IDLE", "MAINTENANCE", "RETIRED", name="assetstatus"
            ),
            existing_nullable=False,
        )
