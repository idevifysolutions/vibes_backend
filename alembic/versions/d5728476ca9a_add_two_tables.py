"""add two tables

Revision ID: d5728476ca9a
Revises: 8fc8e5c31f48
Create Date: 2026-02-02 10:31:15.495483

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd5728476ca9a'
down_revision: Union[str, Sequence[str], None] = '8fc8e5c31f48'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if table exists before creating
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    if 'alert_configurations' not in inspector.get_table_names():
        op.create_table(
            'alert_configurations',
            # ... rest of your table definition
        )
        
def downgrade() -> None:
    """Downgrade schema."""

    # Reverse changes to inventory_batches
    op.alter_column(
        'inventory_batches', 'unit',
        existing_type=postgresql.ENUM('kg', 'gm', 'mg', 'liter', 'ml', name='unittype'),
        nullable=True,
        server_default=None
    )

    op.alter_column(
        'inventory_alert', 'alert_type',
        existing_type=postgresql.ENUM('LOW_STOCK', 'OUT_OF_STOCK', 'EXPIRY_WARNING', name='alerttype'),
        nullable=False
    )

    op.alter_column(
        'inventory', 'purchase_unit',
        existing_type=postgresql.ENUM('kg', 'gm', 'mg', 'liter', 'ml', name='unittype'),
        nullable=False
    )

    # Drop the newly created tables
    op.drop_index(op.f('ix_alert_notifications_tenant_id'), table_name='alert_notifications')
    op.drop_table('alert_notifications')
    op.drop_index(op.f('ix_alert_configurations_tenant_id'), table_name='alert_configurations')
    op.drop_table('alert_configurations')
