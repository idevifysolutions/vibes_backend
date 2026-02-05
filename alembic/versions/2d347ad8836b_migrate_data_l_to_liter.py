"""migrate_data_L_to_liter

Revision ID: 2d347ad8836b
Revises: 039845f71798
Create Date: 2026-02-01 10:58:10.311653

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2d347ad8836b'
down_revision: Union[str, Sequence[str], None] = '039845f71798'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def  upgrade() -> None:
    # First, add the new enum value with COMMIT
    op.execute("COMMIT")  # Commit previous transaction
    op.execute("ALTER TYPE unittype ADD VALUE IF NOT EXISTS 'liter'")
    op.execute("COMMIT")  # Commit the enum addition
    
    # Now migrate the data
    op.execute("""
        UPDATE inventory
        SET unit = 'liter'
        WHERE unit = 'L'
    """)


def downgrade() -> None:
    # Migrate back
    op.execute("""
        UPDATE inventory
        SET unit = 'L'
        WHERE unit = 'liter'
    """)