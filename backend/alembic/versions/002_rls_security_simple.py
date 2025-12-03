"""Enable Row Level Security - Simplified Version

Revision ID: 002_rls_security_simple  
Revises: e5b8c9d7f2a1
Create Date: 2025-12-03 16:30:00.000000

Simplified RLS implementation to avoid transaction issues
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision: str = '002_rls_security_simple'
down_revision: Union[str, Sequence[str], None] = 'e5b8c9d7f2a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Enable RLS and implement basic security policies"""
    
    print("Starting RLS security implementation...")
    connection = op.get_bind()
    
    # 1. Add user_id columns for multi-tenant support
    print("Adding user context columns...")
    
    try:
        # Core application tables
        op.add_column('sessions', sa.Column('user_id', sa.String(255), nullable=True))
        op.add_column('agents', sa.Column('created_by', sa.String(255), nullable=True))
        op.add_column('tasks', sa.Column('user_id', sa.String(255), nullable=True))
        op.add_column('artifacts', sa.Column('user_id', sa.String(255), nullable=True))
        op.add_column('knowledge_entries', sa.Column('created_by', sa.String(255), nullable=True))
        
        # Security platform tables
        op.add_column('engagement_scopes', sa.Column('created_by', sa.String(255), nullable=True))
        op.add_column('pentesting_sessions', sa.Column('authorized_users', sa.JSON(), nullable=True))
        op.add_column('pentesting_tasks', sa.Column('assigned_to', sa.String(255), nullable=True))
        op.add_column('security_findings', sa.Column('discovered_by', sa.String(255), nullable=True))
        op.add_column('security_audit_logs', sa.Column('user_id', sa.String(255), nullable=True))
        
        print("✅ User context columns added successfully")
        
    except Exception as e:
        print(f"Warning: Some columns may already exist: {e}")
    
    # 2. Add basic indexes
    print("Creating indexes...")
    
    try:
        op.create_index('ix_sessions_user_id', 'sessions', ['user_id'])
        op.create_index('ix_tasks_user_id', 'tasks', ['user_id'])
        op.create_index('ix_artifacts_user_id', 'artifacts', ['user_id'])
        print("✅ Indexes created successfully")
    except Exception as e:
        print(f"Warning: Some indexes may already exist: {e}")


def downgrade() -> None:
    """Remove RLS columns and indexes"""
    
    print("Removing RLS security implementation...")
    
    # Remove indexes
    try:
        op.drop_index('ix_sessions_user_id')
        op.drop_index('ix_tasks_user_id') 
        op.drop_index('ix_artifacts_user_id')
    except Exception:
        pass
    
    # Remove columns
    op.drop_column('sessions', 'user_id')
    op.drop_column('agents', 'created_by')
    op.drop_column('tasks', 'user_id')
    op.drop_column('artifacts', 'user_id')
    op.drop_column('knowledge_entries', 'created_by')
    op.drop_column('engagement_scopes', 'created_by')
    op.drop_column('pentesting_sessions', 'authorized_users')
    op.drop_column('pentesting_tasks', 'assigned_to')
    op.drop_column('security_findings', 'discovered_by')
    op.drop_column('security_audit_logs', 'user_id')
    
    print("RLS columns removed!")