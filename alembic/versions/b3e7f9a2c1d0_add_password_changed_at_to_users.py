"""add password_changed_at to users

Revision ID: b3e7f9a2c1d0
Revises: 109c2f0e098b
Create Date: 2026-08-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b3e7f9a2c1d0'
down_revision: Union[str, Sequence[str], None] = '109c2f0e098b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column(
        'password_changed_at', sa.DateTime(timezone=True), nullable=True
    ))


def downgrade() -> None:
    op.drop_column('users', 'password_changed_at')
