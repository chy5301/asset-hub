"""v3 asset model column

Revision ID: 2d589d84e584
Revises: 2b6e5509aeef
Create Date: 2026-05-13 11:35:58.440961

v2.0 PR-3：Asset 顶层新增 model 列（nullable / non-unique），并建立 ix_assets_model 索引。
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2d589d84e584"
down_revision: str | Sequence[str] | None = "2b6e5509aeef"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("assets", schema=None) as batch_op:
        batch_op.add_column(sa.Column("model", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
        batch_op.create_index(batch_op.f("ix_assets_model"), ["model"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("assets", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_assets_model"))
        batch_op.drop_column("model")
