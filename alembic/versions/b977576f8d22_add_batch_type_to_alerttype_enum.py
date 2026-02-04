"""add BATCH_TYPE to alerttype enum

Revision ID: b977576f8d22
Revises: d5728476ca9a
Create Date: 2026-02-04 04:47:07.189451

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b977576f8d22'
down_revision: Union[str, Sequence[str], None] = 'd5728476ca9a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.execute(
        "ALTER TYPE alerttype ADD VALUE IF NOT EXISTS 'BATCH_TYPE';"
    )

def downgrade():
    # PostgreSQL DOES NOT support removing enum values easily
    pass