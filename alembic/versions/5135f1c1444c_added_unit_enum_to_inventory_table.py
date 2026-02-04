"""added unit enum to inventory table

Revision ID: 5135f1c1444c
Revises: aeba1357c4c9
Create Date: 2026-01-31 04:28:17.099368
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '5135f1c1444c'
down_revision: Union[str, Sequence[str], None] = 'aeba1357c4c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# PostgreSQL enum must match *values* of your Python enum
unit_enum = postgresql.ENUM(
    'kg',
    'gm',
    'mg',
    'L',
    'ml',
    name='unittype',
)


def upgrade() -> None:
    # 1. Create enum type in PostgreSQL
    unit_enum.create(op.get_bind(), checkfirst=True)

    # 2. Alter column to use enum
    op.alter_column(
        'inventory',
        'unit',
        existing_type=sa.VARCHAR(),
        type_=unit_enum,
        postgresql_using='unit::unittype',
        existing_nullable=False,
    )


def downgrade() -> None:
    # 1. Convert enum back to varchar
    op.alter_column(
        'inventory',
        'unit',
        existing_type=unit_enum,
        type_=sa.VARCHAR(),
        postgresql_using='unit::text',
        existing_nullable=False,
    )

    # 2. Drop enum type
    unit_enum.drop(op.get_bind(), checkfirst=True)
