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
    """Upgrade schema."""

    # -----------------------------
    # Fix ENUM issue
    # -----------------------------
    alerttype = postgresql.ENUM(
        'LOW_STOCK', 'OUT_OF_STOCK', 'EXPIRY_WARNING',
        name='alerttype',
        create_type=False  # Don't try to recreate the type
    )

    # -----------------------------
    # Create new tables
    # -----------------------------
    op.create_table(
        'alert_configurations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('item_category_id', sa.Integer(), nullable=True),
        sa.Column('alert_type', alerttype, nullable=True),
        sa.Column('threshold_value', sa.Integer(), nullable=True),
        sa.Column('lead_time_days', sa.Integer(), nullable=True),
        sa.Column('notification_channels', sa.String(), nullable=True),
        sa.Column('recipient_user_ids', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['item_category_id'], ['item_categories.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_alert_configurations_tenant_id'), 'alert_configurations', ['tenant_id'], unique=False)

    op.create_table(
        'alert_notifications',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('alert_id', sa.UUID(), nullable=True),
        sa.Column('channel', sa.String(length=20), nullable=True),
        sa.Column('recipient_user_id', sa.Integer(), nullable=True),
        sa.Column('recipient_contact', sa.String(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['alert_id'], ['inventory_alert.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['recipient_user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_alert_notifications_tenant_id'), 'alert_notifications', ['tenant_id'], unique=False)

    # -----------------------------
    # Alter existing columns safely
    # -----------------------------
    op.alter_column(
        'inventory', 'purchase_unit',
        existing_type=postgresql.ENUM('kg', 'gm', 'mg', 'liter', 'ml', name='unittype'),
        nullable=True
    )

    op.alter_column(
        'inventory_alert', 'alert_type',
        existing_type=postgresql.ENUM('LOW_STOCK', 'OUT_OF_STOCK', 'EXPIRY_WARNING', name='alerttype'),
        nullable=True
    )

    # Fix NULLs in inventory_batches.unit before setting NOT NULL
    op.execute("UPDATE inventory_batches SET unit='kg' WHERE unit IS NULL")

    op.alter_column(
        'inventory_batches', 'unit',
        existing_type=postgresql.ENUM('kg', 'gm', 'mg', 'liter', 'ml', name='unittype'),
        nullable=False,
        server_default='kg'  # optional, sets default for future inserts
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
