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



def upgrade():
    """
    Now 'liter' exists in enum (from previous migration)
    Safe to update data and remove 'L'
    """
    
    # Step 1: Update data from 'L' to 'liter' (now safe)
    op.execute("""
        UPDATE inventory 
        SET unit = 'liter' 
        WHERE unit = 'L'
    """)
    
    op.execute("""
        UPDATE inventory 
        SET purchase_unit = 'liter' 
        WHERE purchase_unit = 'L'
    """)
    
    # Step 2: Remove 'L' from enum by recreating it
    # Create temp columns
    op.execute("ALTER TABLE inventory ADD COLUMN unit_temp VARCHAR(50)")
    op.execute("ALTER TABLE inventory ADD COLUMN purchase_unit_temp VARCHAR(50)")
    
    # Copy current values to temp
    op.execute("""
        UPDATE inventory 
        SET unit_temp = unit::text,
            purchase_unit_temp = purchase_unit::text
    """)
    
    # Drop enum columns
    op.execute("ALTER TABLE inventory DROP COLUMN unit")
    op.execute("ALTER TABLE inventory DROP COLUMN purchase_unit")
    
    # Drop and recreate enum WITHOUT 'L'
    op.execute("DROP TYPE unittype")
    op.execute("""
        CREATE TYPE unittype AS ENUM (
            'kg', 'gm', 'mg', 
            'liter', 'ml'
        )
    """)
    
    # Recreate columns with new enum
    op.execute("ALTER TABLE inventory ADD COLUMN unit unittype")
    op.execute("ALTER TABLE inventory ADD COLUMN purchase_unit unittype")
    
    # Copy values back from temp
    op.execute("""
        UPDATE inventory 
        SET unit = unit_temp::unittype,
            purchase_unit = purchase_unit_temp::unittype
    """)
    
    # Set NOT NULL constraint
    op.execute("ALTER TABLE inventory ALTER COLUMN unit SET NOT NULL")
    op.execute("ALTER TABLE inventory ALTER COLUMN purchase_unit SET NOT NULL")
    
    # Drop temp columns
    op.execute("ALTER TABLE inventory DROP COLUMN unit_temp")
    op.execute("ALTER TABLE inventory DROP COLUMN purchase_unit_temp")


def downgrade():
    """Revert to 'L'"""
    
    # Add 'L' back to enum
    op.execute("ALTER TYPE unittype ADD VALUE IF NOT EXISTS 'L'")
    
    # Update data back to 'L'
    op.execute("UPDATE inventory SET unit = 'L' WHERE unit = 'liter'")
    op.execute("UPDATE inventory SET purchase_unit = 'L' WHERE purchase_unit = 'liter'")
    
    # Recreate enum with 'L' instead of 'liter'
    op.execute("ALTER TABLE inventory ADD COLUMN unit_temp VARCHAR(50)")
    op.execute("ALTER TABLE inventory ADD COLUMN purchase_unit_temp VARCHAR(50)")
    
    op.execute("""
        UPDATE inventory 
        SET unit_temp = unit::text,
            purchase_unit_temp = purchase_unit::text
    """)
    
    op.execute("ALTER TABLE inventory DROP COLUMN unit")
    op.execute("ALTER TABLE inventory DROP COLUMN purchase_unit")
    
    op.execute("DROP TYPE unittype")
    op.execute("""
        CREATE TYPE unittype AS ENUM (
            'kg', 'gm', 'mg', 
            'L', 'ml'
        )
    """)
    
    op.execute("ALTER TABLE inventory ADD COLUMN unit unittype")
    op.execute("ALTER TABLE inventory ADD COLUMN purchase_unit unittype")
    
    op.execute("""
        UPDATE inventory 
        SET unit = unit_temp::unittype,
            purchase_unit = purchase_unit_temp::unittype
    """)
    
    op.execute("ALTER TABLE inventory ALTER COLUMN unit SET NOT NULL")
    op.execute("ALTER TABLE inventory ALTER COLUMN purchase_unit SET NOT NULL")
    
    op.execute("ALTER TABLE inventory DROP COLUMN unit_temp")
    op.execute("ALTER TABLE inventory DROP COLUMN purchase_unit_temp")