"""add_timezone_support_to_agents_table

Revision ID: deddb1747453
Revises: 14a4a0a5329b
Create Date: 2025-11-24 14:01:10.059314

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'deddb1747453'
down_revision: Union[str, Sequence[str], None] = '14a4a0a5329b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.alter_column('agents', 'created_at',
               existing_type=sa.TIMESTAMP(),
               type_=sa.TIMESTAMP(timezone=True),
               existing_nullable=True)
    # agents 테이블의 last_seen 컬럼 타입을 TIMESTAMPTZ로 변경
    op.alter_column('agents', 'last_seen',
               existing_type=sa.TIMESTAMP(),
               type_=sa.TIMESTAMP(timezone=True),
               existing_nullable=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    op.alter_column('agents', 'last_seen',
               existing_type=sa.TIMESTAMP(timezone=True),
               type_=sa.TIMESTAMP(),
               existing_nullable=True)
    op.alter_column('agents', 'created_at',
               existing_type=sa.TIMESTAMP(timezone=True),
               type_=sa.TIMESTAMP(),
               existing_nullable=True)