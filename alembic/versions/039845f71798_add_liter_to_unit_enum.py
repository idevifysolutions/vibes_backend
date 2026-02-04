"""add_liter_to_unit_enum

Revision ID: 039845f71798
Revises: 5135f1c1444c
Create Date: 2026-02-01 10:48:06.250717

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '039845f71798'
down_revision: Union[str, Sequence[str], None] = '5135f1c1444c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    """
    ONLY add 'liter' to the enum - DO NOT UPDATE DATA YET
    """
    
    # Just add the enum value, nothing else
    op.execute("ALTER TYPE unittype ADD VALUE IF NOT EXISTS 'liter'")
    
    # That's it! No UPDATE statements here


def downgrade():
    """
    Cannot easily remove enum value in PostgreSQL
    Will be handled in next migration
    """
    pass