"""add_json_column_size_constraints

Revision ID: 14a8b9fe4122
Revises: baf67a04783a
Create Date: 2025-12-04 01:32:58.623301

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '14a8b9fe4122'
down_revision: Union[str, Sequence[str], None] = 'baf67a04783a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add JSON column size constraints to prevent performance issues
    # Based on security report recommendations for optimizing JSON column performance
    
    # 1. Security audit logs - context column (audit events, context data)
    op.execute("""
        ALTER TABLE security_audit_logs
        ADD CONSTRAINT check_context_size 
        CHECK (pg_column_size(context) < 65536)
    """)
    
    # 2. Security audit logs - risk_factors column (risk assessment data)
    op.execute("""
        ALTER TABLE security_audit_logs
        ADD CONSTRAINT check_risk_factors_size 
        CHECK (pg_column_size(risk_factors) < 32768)
    """)
    
    # 3. Security audit logs - evidence_data column (evidence and artifacts)
    op.execute("""
        ALTER TABLE security_audit_logs
        ADD CONSTRAINT check_evidence_data_size 
        CHECK (pg_column_size(evidence_data) < 131072)
    """)
    
    # 4. Sessions - metadata column (session configuration)
    op.execute("""
        ALTER TABLE sessions
        ADD CONSTRAINT check_metadata_size 
        CHECK (pg_column_size(metadata) < 32768)
    """)
    
    # 5. Tasks - metadata column (task configuration)
    op.execute("""
        ALTER TABLE tasks
        ADD CONSTRAINT check_task_metadata_size 
        CHECK (pg_column_size(metadata) < 32768)
    """)
    
    # 6. Tools - configuration column (tool settings)
    op.execute("""
        ALTER TABLE tools
        ADD CONSTRAINT check_configuration_size 
        CHECK (pg_column_size(configuration) < 65536)
    """)
    
    # 7. Human approvals - approval_conditions column (approval conditions)
    op.execute("""
        ALTER TABLE human_approvals
        ADD CONSTRAINT check_approval_conditions_size 
        CHECK (pg_column_size(approval_conditions) < 16384)
    """)
    
    # 8. Human approvals - risk_factors column (risk factors)
    op.execute("""
        ALTER TABLE human_approvals
        ADD CONSTRAINT check_approval_risk_factors_size 
        CHECK (pg_column_size(risk_factors) < 32768)
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Remove JSON column size constraints
    
    op.execute("ALTER TABLE security_audit_logs DROP CONSTRAINT IF EXISTS check_context_size")
    op.execute("ALTER TABLE security_audit_logs DROP CONSTRAINT IF EXISTS check_risk_factors_size")
    op.execute("ALTER TABLE security_audit_logs DROP CONSTRAINT IF EXISTS check_evidence_data_size")
    op.execute("ALTER TABLE sessions DROP CONSTRAINT IF EXISTS check_metadata_size")
    op.execute("ALTER TABLE tasks DROP CONSTRAINT IF EXISTS check_task_metadata_size")
    op.execute("ALTER TABLE tools DROP CONSTRAINT IF EXISTS check_configuration_size")
    op.execute("ALTER TABLE human_approvals DROP CONSTRAINT IF EXISTS check_approval_conditions_size")
    op.execute("ALTER TABLE human_approvals DROP CONSTRAINT IF EXISTS check_approval_risk_factors_size")
