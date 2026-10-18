"""Default new employee accounts to active; preserve existing account states.

Revision ID: 20261018_status_default
Revises: None

Requires an existing nhan_vien.trang_thai column. This migration does not
bootstrap the database or reconcile unrelated SQL/ORM differences.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261018_status_default"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("nhan_vien", "trang_thai", server_default=sa.text("'hoat_dong'"))


def downgrade() -> None:
    op.alter_column("nhan_vien", "trang_thai", server_default=None)
