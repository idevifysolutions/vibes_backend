"""store role value

Revision ID: be2d7badcd85
Revises: 19b2a249acf6
Create Date: 2026-01-05 16:49:13.217607

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'be2d7badcd85'
down_revision: Union[str, Sequence[str], None] = '19b2a249acf6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD_ENUM = "item_category_type"
NEW_ENUM = "item_category_type_new"
TABLE_NAME = "item_categories"
COLUMN_NAME = "category_type"

def upgrade():
    # 1. Create new enum with lowercase values
    op.execute(
        f"""
        CREATE TYPE {NEW_ENUM} AS ENUM (
            'perishable',
            'non_perishable'
        )
        """
    )

    # 2. Alter column to use new enum, converting data
    op.execute(
        f"""
        ALTER TABLE {TABLE_NAME}
        ALTER COLUMN {COLUMN_NAME}
        TYPE {NEW_ENUM}
        USING LOWER({COLUMN_NAME}::text):: {NEW_ENUM}
        """
    )

    # 3. Drop old enum
    op.execute(f"DROP TYPE {OLD_ENUM}")

    # 4. Rename new enum to original name
    op.execute(
        f"""
        ALTER TYPE {NEW_ENUM}
        RENAME TO {OLD_ENUM}
        """
    )


def downgrade():
    # Downgrade back to uppercase enum (optional but safe)

    op.execute(
        f"""
        CREATE TYPE {OLD_ENUM}_old AS ENUM (
            'PERISHABLE',
            'NON_PERISHABLE'
        )
        """
    )

    op.execute(
        f"""
        ALTER TABLE {TABLE_NAME}
        ALTER COLUMN {COLUMN_NAME}
        TYPE {OLD_ENUM}_old
        USING UPPER({COLUMN_NAME}::text):: {OLD_ENUM}_old
        """
    )

    op.execute(f"DROP TYPE {OLD_ENUM}")

    op.execute(
        f"""
        ALTER TYPE {OLD_ENUM}_old
        RENAME TO {OLD_ENUM}
        """
    )
    # ### end Alembic commands ###
