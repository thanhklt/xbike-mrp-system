"""Default new employee accounts to active; preserve existing account states.

Revision ID: 20261018_status_default
Revises: None

Accepts the supplied v3 SQL without trang_thai and the existing ORM schema.
Existing accounts without a status remain NULL for explicit review;
the following auth migration rejects unresolved statuses.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261018_status_default"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = sa.inspect(op.get_bind()).get_columns("nhan_vien")
    if not any(column["name"] == "trang_thai" for column in columns):
        op.add_column("nhan_vien", sa.Column("trang_thai", sa.String(), nullable=True))
    op.alter_column("nhan_vien", "trang_thai", server_default=sa.text("'hoat_dong'"))


def downgrade() -> None:
    op.alter_column("nhan_vien", "trang_thai", server_default=None)
