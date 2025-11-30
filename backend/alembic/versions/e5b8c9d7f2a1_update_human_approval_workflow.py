"""Update human approval workflow

Revision ID: e5b8c9d7f2a1
Revises: c199e43193b6
Create Date: 2025-11-30 23:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e5b8c9d7f2a1'
down_revision = 'c199e43193b6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade the HumanApproval table to support enhanced approval workflow"""
    
    # First check if the table exists and has old schema
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Get current columns
    columns = inspector.get_columns('human_approvals')
    column_names = [col['name'] for col in columns]
    
    # Check if we have the old schema format
    if 'approver_name' in column_names:
        # Drop old schema columns that are being replaced
        op.drop_column('human_approvals', 'approver_name')
        op.drop_column('human_approvals', 'approver_email')
        op.drop_column('human_approvals', 'approver_role')
        op.drop_column('human_approvals', 'approved')
        op.drop_column('human_approvals', 'approval_comments')
        op.drop_column('human_approvals', 'conditions')
        if 'action_description' in column_names:
            op.drop_column('human_approvals', 'action_description')
    
    # Add new columns if they don't exist
    if 'action_type' not in column_names:
        op.add_column('human_approvals', sa.Column('action_type', sa.String(length=100), nullable=False, server_default='unknown'))
    
    if 'target' not in column_names:
        op.add_column('human_approvals', sa.Column('target', sa.String(length=500), nullable=True))
    
    if 'tool_name' not in column_names:
        op.add_column('human_approvals', sa.Column('tool_name', sa.String(length=100), nullable=True))
    
    if 'command' not in column_names:
        op.add_column('human_approvals', sa.Column('command', sa.Text(), nullable=True))
    
    if 'risk_score' not in column_names:
        op.add_column('human_approvals', sa.Column('risk_score', sa.Float(), nullable=False, server_default='0.0'))
    
    if 'risk_factors' not in column_names:
        op.add_column('human_approvals', sa.Column('risk_factors', sa.JSON(), nullable=True))
    
    if 'impact_assessment' not in column_names:
        op.add_column('human_approvals', sa.Column('impact_assessment', sa.Text(), nullable=True))
    
    if 'requested_by' not in column_names:
        op.add_column('human_approvals', sa.Column('requested_by', sa.String(length=255), nullable=False, server_default='unknown'))
    
    if 'justification' not in column_names:
        op.add_column('human_approvals', sa.Column('justification', sa.Text(), nullable=True))
    
    if 'required_approver_role' not in column_names:
        op.add_column('human_approvals', sa.Column('required_approver_role', sa.String(length=100), nullable=False, server_default='security_lead'))
    
    if 'approval_conditions' not in column_names:
        op.add_column('human_approvals', sa.Column('approval_conditions', sa.JSON(), nullable=True))
    
    if 'timeout_at' not in column_names:
        op.add_column('human_approvals', sa.Column('timeout_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW() + INTERVAL \'2 hours\'')))
    
    if 'status' not in column_names:
        op.add_column('human_approvals', sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'))
    
    if 'approver_id' not in column_names:
        op.add_column('human_approvals', sa.Column('approver_id', sa.String(length=255), nullable=True))
    
    if 'approved_at' not in column_names:
        op.add_column('human_approvals', sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True))
    
    if 'denial_reason' not in column_names:
        op.add_column('human_approvals', sa.Column('denial_reason', sa.Text(), nullable=True))
    
    if 'approval_conditions_accepted' not in column_names:
        op.add_column('human_approvals', sa.Column('approval_conditions_accepted', sa.JSON(), nullable=True))
    
    if 'reason' not in column_names:
        op.add_column('human_approvals', sa.Column('reason', sa.Text(), nullable=True))
    
    if 'created_at' not in column_names:
        op.add_column('human_approvals', sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')))
    
    if 'updated_at' not in column_names:
        op.add_column('human_approvals', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')))
    
    # Create index on action_id for faster lookups
    try:
        op.create_index('ix_human_approvals_action_id', 'human_approvals', ['action_id'])
    except:
        # Index might already exist
        pass
    
    # Create index on status for filtering
    try:
        op.create_index('ix_human_approvals_status', 'human_approvals', ['status'])
    except:
        # Index might already exist
        pass
    
    # Remove server defaults after adding columns
    op.alter_column('human_approvals', 'action_type', server_default=None)
    op.alter_column('human_approvals', 'risk_score', server_default=None)
    op.alter_column('human_approvals', 'requested_by', server_default=None)
    op.alter_column('human_approvals', 'required_approver_role', server_default=None)
    op.alter_column('human_approvals', 'timeout_at', server_default=None)
    op.alter_column('human_approvals', 'status', server_default=None)
    op.alter_column('human_approvals', 'created_at', server_default=None)
    op.alter_column('human_approvals', 'updated_at', server_default=None)


def downgrade() -> None:
    """Downgrade to previous HumanApproval schema"""
    
    # Remove new columns
    op.drop_column('human_approvals', 'approval_conditions_accepted')
    op.drop_column('human_approvals', 'denial_reason')
    op.drop_column('human_approvals', 'approved_at')
    op.drop_column('human_approvals', 'approver_id')
    op.drop_column('human_approvals', 'status')
    op.drop_column('human_approvals', 'timeout_at')
    op.drop_column('human_approvals', 'approval_conditions')
    op.drop_column('human_approvals', 'required_approver_role')
    op.drop_column('human_approvals', 'justification')
    op.drop_column('human_approvals', 'requested_by')
    op.drop_column('human_approvals', 'impact_assessment')
    op.drop_column('human_approvals', 'risk_factors')
    op.drop_column('human_approvals', 'risk_score')
    op.drop_column('human_approvals', 'command')
    op.drop_column('human_approvals', 'tool_name')
    op.drop_column('human_approvals', 'target')
    op.drop_column('human_approvals', 'action_type')
    op.drop_column('human_approvals', 'reason')
    op.drop_column('human_approvals', 'updated_at')
    op.drop_column('human_approvals', 'created_at')
    
    # Remove indexes
    try:
        op.drop_index('ix_human_approvals_action_id', table_name='human_approvals')
    except:
        pass
    
    try:
        op.drop_index('ix_human_approvals_status', table_name='human_approvals')
    except:
        pass
    
    # Restore old columns
    op.add_column('human_approvals', sa.Column('action_description', sa.Text(), nullable=False))
    op.add_column('human_approvals', sa.Column('approver_name', sa.String(length=255), nullable=False))
    op.add_column('human_approvals', sa.Column('approver_email', sa.String(length=255), nullable=True))
    op.add_column('human_approvals', sa.Column('approver_role', sa.String(length=100), nullable=True))
    op.add_column('human_approvals', sa.Column('approved', sa.Boolean(), nullable=False))
    op.add_column('human_approvals', sa.Column('approval_comments', sa.Text(), nullable=True))
    op.add_column('human_approvals', sa.Column('conditions', sa.JSON(), nullable=True))