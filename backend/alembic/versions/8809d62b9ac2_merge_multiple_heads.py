"""merge multiple heads

Revision ID: 8809d62b9ac2
Revises: 003_korean_supabase_rls, ff58e72461b7
Create Date: 2025-12-03 16:56:34.503689

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8809d62b9ac2'
down_revision: Union[str, Sequence[str], None] = ('003_korean_supabase_rls', 'ff58e72461b7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
