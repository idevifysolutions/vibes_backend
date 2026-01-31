"""store lower case item categories

Revision ID: 7e52e8c6b4f6
Revises: 4f5ba34a5a72
Create Date: 2026-01-06 21:43:55.858347

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7e52e8c6b4f6'
down_revision: Union[str, Sequence[str], None] = '4f5ba34a5a72'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
