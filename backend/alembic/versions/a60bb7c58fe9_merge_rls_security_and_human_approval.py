"""merge_rls_security_and_human_approval

Revision ID: a60bb7c58fe9
Revises: 001_rls_security, e5b8c9d7f2a1
Create Date: 2025-12-03 16:24:19.354612

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a60bb7c58fe9'
down_revision: Union[str, Sequence[str], None] = ('001_rls_security', 'e5b8c9d7f2a1')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
