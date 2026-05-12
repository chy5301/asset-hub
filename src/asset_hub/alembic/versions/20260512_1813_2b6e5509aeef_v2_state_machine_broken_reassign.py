"""v2 state machine broken reassign

Revision ID: 2b6e5509aeef
Revises: c6c0960805a9
Create Date: 2026-05-12 18:13:50.051557

v2.0 状态机焕新：
1. AssetStatus enum 加 BROKEN（6 态）
2. TransitionKind enum 删 RELOCATE/TRANSFER_HOLDER，加 REASSIGN/REPORT_BROKEN/DECLARE_UNREPAIRABLE/DISMISS（12 个）
3. 数据迁移：旧 RELOCATE/TRANSFER_HOLDER state_transition_records 改写为 REASSIGN
"""
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op


revision: str = "2b6e5509aeef"
down_revision: str | Sequence[str] | None = "c6c0960805a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. assets.status enum 加 BROKEN（batch 必需，SQLite CHECK constraint）
    with op.batch_alter_table("assets") as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=sa.Enum(
                "IN_USE", "IDLE", "MAINTENANCE", "RETIRED", "DISPOSED",
                name="assetstatus",
            ),
            type_=sa.Enum(
                "IDLE", "IN_USE", "MAINTENANCE", "BROKEN", "RETIRED", "DISPOSED",
                name="assetstatus",
            ),
            existing_nullable=False,
        )

    # 2. 先数据迁移：旧 RELOCATE / TRANSFER_HOLDER → REASSIGN
    op.execute(
        "UPDATE state_transition_records SET kind = 'REASSIGN' "
        "WHERE kind IN ('RELOCATE', 'TRANSFER_HOLDER')"
    )

    # 3. state_transition_records.kind enum 替换为 v2 集合
    with op.batch_alter_table("state_transition_records") as batch_op:
        batch_op.alter_column(
            "kind",
            existing_type=sa.Enum(
                "CHECKOUT_INTERNAL", "CHECKOUT_EXTERNAL", "RETURN",
                "SEND_TO_MAINTENANCE", "RECOVER_FROM_MAINTENANCE",
                "RETIRE", "REINSTATE", "DISPOSE",
                "RELOCATE", "TRANSFER_HOLDER",
                name="transitionkind",
            ),
            type_=sa.Enum(
                "CHECKOUT_INTERNAL", "CHECKOUT_EXTERNAL", "RETURN",
                "SEND_TO_MAINTENANCE", "RECOVER_FROM_MAINTENANCE",
                "RETIRE", "REINSTATE", "DISPOSE",
                "REASSIGN",
                "REPORT_BROKEN", "DECLARE_UNREPAIRABLE", "DISMISS",
                name="transitionkind",
            ),
            existing_nullable=False,
        )


def downgrade() -> None:
    # 拒绝 downgrade 如有 BROKEN 状态资产
    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT COUNT(*) FROM assets WHERE status = 'BROKEN'")).scalar()
    if result and result > 0:
        raise RuntimeError(f"拒绝 downgrade：仍有 {result} 个 BROKEN 状态资产，请先迁移其状态")

    result = conn.execute(sa.text(
        "SELECT COUNT(*) FROM state_transition_records "
        "WHERE kind IN ('REASSIGN', 'REPORT_BROKEN', 'DECLARE_UNREPAIRABLE', 'DISMISS')"
    )).scalar()
    if result and result > 0:
        raise RuntimeError(f"拒绝 downgrade：仍有 {result} 个 v2.0 新 kind 的 transition records")

    with op.batch_alter_table("state_transition_records") as batch_op:
        batch_op.alter_column(
            "kind",
            existing_type=sa.Enum(
                "CHECKOUT_INTERNAL", "CHECKOUT_EXTERNAL", "RETURN",
                "SEND_TO_MAINTENANCE", "RECOVER_FROM_MAINTENANCE",
                "RETIRE", "REINSTATE", "DISPOSE",
                "REASSIGN",
                "REPORT_BROKEN", "DECLARE_UNREPAIRABLE", "DISMISS",
                name="transitionkind",
            ),
            type_=sa.Enum(
                "CHECKOUT_INTERNAL", "CHECKOUT_EXTERNAL", "RETURN",
                "SEND_TO_MAINTENANCE", "RECOVER_FROM_MAINTENANCE",
                "RETIRE", "REINSTATE", "DISPOSE",
                "RELOCATE", "TRANSFER_HOLDER",
                name="transitionkind",
            ),
            existing_nullable=False,
        )

    with op.batch_alter_table("assets") as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=sa.Enum(
                "IDLE", "IN_USE", "MAINTENANCE", "BROKEN", "RETIRED", "DISPOSED",
                name="assetstatus",
            ),
            type_=sa.Enum(
                "IN_USE", "IDLE", "MAINTENANCE", "RETIRED", "DISPOSED",
                name="assetstatus",
            ),
            existing_nullable=False,
        )
