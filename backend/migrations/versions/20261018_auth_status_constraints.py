"""Require known account states without guessing the status of existing employees.

Revision ID: 20261018_auth_status
Revises: 20261018_status_default
"""

import sqlalchemy as sa
from alembic import op

revision = "20261018_auth_status"
down_revision = "20261018_status_default"
branch_labels = None
depends_on = None


def upgrade() -> None:
    invalid = op.get_bind().scalar(
        sa.text(
            "SELECT count(*) FROM nhan_vien "
            "WHERE trang_thai IS NULL OR trang_thai NOT IN ('hoat_dong', 'bi_khoa')"
        )
    )
    if invalid:
        raise RuntimeError(
            "Account status migration stopped: existing employees have missing/invalid "
            "trang_thai. Obtain an explicit hoat_dong/bi_khoa mapping before migrating; "
            "no employee is automatically unlocked or reclassified."
        )
    op.alter_column(
        "nhan_vien", "trang_thai", nullable=False, server_default=sa.text("'hoat_dong'")
    )
    checks = sa.inspect(op.get_bind()).get_check_constraints("nhan_vien")
    if not any(check["name"] == "ck_nhan_vien_trang_thai" for check in checks):
        op.create_check_constraint(
            "ck_nhan_vien_trang_thai", "nhan_vien", "trang_thai IN ('hoat_dong', 'bi_khoa')"
        )


def downgrade() -> None:
    op.drop_constraint("ck_nhan_vien_trang_thai", "nhan_vien", type_="check")
    op.alter_column("nhan_vien", "trang_thai", nullable=True)
