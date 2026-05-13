"""m1_initial_schema_baseline

Revision ID: 492867df5ecb
Revises:
Create Date: 2026-04-26 21:49:49.273157

M1 初始 schema — 含 4 张原生表（asset_types / assets / checkout_records / attachments），
不含后续增量字段（code_prefix / asset_code / acquired_at / current_checkout_id /
return_location / return_receiver）——这些由 m2c3 / 2ec8fc 增量 migration 补齐。
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "492867df5ecb"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "asset_types",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("custom_fields", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("asset_types", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_asset_types_name"), ["name"], unique=True)

    op.create_table(
        "assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("serial_number", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("type_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("IN_USE", "IDLE", "MAINTENANCE", "RETIRED", name="assetstatus"),
            nullable=False,
        ),
        sa.Column("holder", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("location", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("notes", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("custom_data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["type_id"],
            ["asset_types.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("assets", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_assets_name"), ["name"], unique=False)
        batch_op.create_index(
            batch_op.f("ix_assets_serial_number"), ["serial_number"], unique=True
        )
        batch_op.create_index(
            batch_op.f("ix_assets_type_id"), ["type_id"], unique=False
        )

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
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["assets.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("checkout_records", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_checkout_records_asset_id"), ["asset_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_checkout_records_returned_at"), ["returned_at"], unique=False
        )
        batch_op.create_index(
            "ix_one_open_checkout_per_asset",
            ["asset_id"],
            unique=True,
            sqlite_where=sa.text("returned_at IS NULL"),
        )

    op.create_table(
        "attachments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("PHOTO", "INVOICE", "DOC", "OTHER", name="attachmentkind"),
            nullable=False,
        ),
        sa.Column("storage_path", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("sha256", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("mime_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("original_name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["assets.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id", "sha256", name="uq_attachment_asset_sha256"),
    )
    with op.batch_alter_table("attachments", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_attachments_asset_id"), ["asset_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_attachments_sha256"), ["sha256"], unique=False
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("attachments", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_attachments_sha256"))
        batch_op.drop_index(batch_op.f("ix_attachments_asset_id"))

    op.drop_table("attachments")

    with op.batch_alter_table("checkout_records", schema=None) as batch_op:
        batch_op.drop_index("ix_one_open_checkout_per_asset")
        batch_op.drop_index(batch_op.f("ix_checkout_records_returned_at"))
        batch_op.drop_index(batch_op.f("ix_checkout_records_asset_id"))

    op.drop_table("checkout_records")

    with op.batch_alter_table("assets", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_assets_type_id"))
        batch_op.drop_index(batch_op.f("ix_assets_serial_number"))
        batch_op.drop_index(batch_op.f("ix_assets_name"))

    op.drop_table("assets")

    with op.batch_alter_table("asset_types", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_asset_types_name"))

    op.drop_table("asset_types")
