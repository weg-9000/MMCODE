"""merge multiple heads

Revision ID: ff58e72461b7
Revises: 002_rls_security_simple, a60bb7c58fe9
Create Date: 2025-12-03 16:39:16.801169

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ff58e72461b7'
down_revision: Union[str, Sequence[str], None] = ('002_rls_security_simple', 'a60bb7c58fe9')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
