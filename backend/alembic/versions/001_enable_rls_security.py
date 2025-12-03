"""Enable Row Level Security and implement comprehensive security policies

Revision ID: 001_rls_security
Revises: c199e43193b6
Create Date: 2025-12-03 12:00:00.000000

Critical security enhancement implementing:
- Row Level Security (RLS) on all tables
- User authentication framework
- Multi-tenant data isolation
- Comprehensive security policies
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision: str = '001_rls_security'
down_revision: Union[str, Sequence[str], None] = 'c199e43193b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Enable RLS and implement security policies"""
    
    # 1. Add user_id columns to all tables for multi-tenant support
    print("Adding user_id columns for multi-tenant support...")
    
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
    # Check if requested_by column already exists from other migration
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = inspector.get_columns('human_approvals')
    column_names = [col['name'] for col in columns]
    
    if 'requested_by' not in column_names:
        op.add_column('human_approvals', sa.Column('requested_by_user_id', sa.String(255), nullable=True))
    # If requested_by exists, we'll use it for user context instead of adding a new column
    
    # Add indexes for performance
    op.create_index('ix_sessions_user_id', 'sessions', ['user_id'])
    op.create_index('ix_tasks_user_id', 'tasks', ['user_id'])
    op.create_index('ix_artifacts_user_id', 'artifacts', ['user_id'])
    # Create GIN index for JSON column with proper operator class
    try:
        connection.execute(text("""
            CREATE INDEX ix_pentesting_sessions_authorized_users 
            ON pentesting_sessions USING gin (authorized_users jsonb_path_ops)
        """))
    except Exception as e:
        # If jsonb_path_ops doesn't work, try without it
        try:
            connection.execute(text("""
                CREATE INDEX ix_pentesting_sessions_authorized_users 
                ON pentesting_sessions USING btree ((authorized_users::text))
            """))
        except Exception:
            # Skip index creation if both fail
            pass
    
    # 2. Create database roles for different access levels
    print("Creating database roles...")
    
    connection = op.get_bind()
    
    # Create roles with appropriate permissions
    connection.execute(text("""
        DO $$
        BEGIN
            -- Application roles
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_admin') THEN
                CREATE ROLE app_admin NOLOGIN;
            END IF;
            
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_user') THEN
                CREATE ROLE app_user NOLOGIN;
            END IF;
            
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_readonly') THEN
                CREATE ROLE app_readonly NOLOGIN;
            END IF;
            
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'security_analyst') THEN
                CREATE ROLE security_analyst NOLOGIN;
            END IF;
            
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'audit_reviewer') THEN
                CREATE ROLE audit_reviewer NOLOGIN;
            END IF;
        END
        $$;
    """))
    
    # 3. Enable Row Level Security on all tables
    print("Enabling Row Level Security...")
    
    tables_to_secure = [
        'sessions', 'agents', 'tasks', 'artifacts', 'knowledge_entries',
        'engagement_scopes', 'pentesting_sessions', 'pentesting_tasks',
        'security_findings', 'security_audit_logs', 'human_approvals'
    ]
    
    for table in tables_to_secure:
        connection.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
    
    # 4. Create comprehensive RLS policies
    print("Creating Row Level Security policies...")
    
    # Sessions table policies
    connection.execute(text("""
        -- Sessions: Users can only access their own sessions
        CREATE POLICY session_user_policy ON sessions
            FOR ALL TO app_user
            USING (user_id = current_setting('app.current_user_id', true))
            WITH CHECK (user_id = current_setting('app.current_user_id', true));
        
        CREATE POLICY session_admin_policy ON sessions
            FOR ALL TO app_admin
            USING (true);
    """))
    
    # Agents table policies  
    connection.execute(text("""
        -- Agents: Read access for users, full access for admins
        CREATE POLICY agent_read_policy ON agents
            FOR SELECT TO app_user
            USING (true);
            
        CREATE POLICY agent_admin_policy ON agents
            FOR ALL TO app_admin
            USING (true);
            
        CREATE POLICY agent_creator_policy ON agents
            FOR UPDATE TO app_user
            USING (created_by = current_setting('app.current_user_id', true));
    """))
    
    # Tasks table policies
    connection.execute(text("""
        -- Tasks: Users can access tasks in their sessions
        CREATE POLICY task_user_policy ON tasks
            FOR ALL TO app_user
            USING (
                user_id = current_setting('app.current_user_id', true) OR
                session_id IN (
                    SELECT id FROM sessions 
                    WHERE user_id = current_setting('app.current_user_id', true)
                )
            )
            WITH CHECK (
                user_id = current_setting('app.current_user_id', true) OR
                session_id IN (
                    SELECT id FROM sessions 
                    WHERE user_id = current_setting('app.current_user_id', true)
                )
            );
        
        CREATE POLICY task_admin_policy ON tasks
            FOR ALL TO app_admin
            USING (true);
    """))
    
    # Artifacts table policies
    connection.execute(text("""
        -- Artifacts: Users can access artifacts from their sessions
        CREATE POLICY artifact_user_policy ON artifacts
            FOR ALL TO app_user
            USING (
                user_id = current_setting('app.current_user_id', true) OR
                session_id IN (
                    SELECT id FROM sessions 
                    WHERE user_id = current_setting('app.current_user_id', true)
                )
            )
            WITH CHECK (
                user_id = current_setting('app.current_user_id', true) OR
                session_id IN (
                    SELECT id FROM sessions 
                    WHERE user_id = current_setting('app.current_user_id', true)
                )
            );
        
        CREATE POLICY artifact_admin_policy ON artifacts
            FOR ALL TO app_admin
            USING (true);
    """))
    
    # Knowledge entries policies
    connection.execute(text("""
        -- Knowledge entries: Read for all users, create/update by creator or admin
        CREATE POLICY knowledge_read_policy ON knowledge_entries
            FOR SELECT TO app_user
            USING (true);
            
        CREATE POLICY knowledge_create_policy ON knowledge_entries
            FOR INSERT TO app_user
            WITH CHECK (created_by = current_setting('app.current_user_id', true));
            
        CREATE POLICY knowledge_update_policy ON knowledge_entries
            FOR UPDATE TO app_user
            USING (created_by = current_setting('app.current_user_id', true));
            
        CREATE POLICY knowledge_admin_policy ON knowledge_entries
            FOR ALL TO app_admin
            USING (true);
    """))
    
    # Security platform policies - highly restrictive
    connection.execute(text("""
        -- Engagement scopes: Only security analysts and admins
        CREATE POLICY engagement_security_policy ON engagement_scopes
            FOR ALL TO security_analyst
            USING (created_by = current_setting('app.current_user_id', true))
            WITH CHECK (created_by = current_setting('app.current_user_id', true));
        
        CREATE POLICY engagement_admin_policy ON engagement_scopes
            FOR ALL TO app_admin
            USING (true);
    """))
    
    connection.execute(text("""
        -- Pentesting sessions: Authorized users only
        CREATE POLICY pentest_session_auth_policy ON pentesting_sessions
            FOR ALL TO security_analyst
            USING (
                authorized_users ? current_setting('app.current_user_id', true) OR
                scope_id IN (
                    SELECT id FROM engagement_scopes 
                    WHERE created_by = current_setting('app.current_user_id', true)
                )
            )
            WITH CHECK (
                authorized_users ? current_setting('app.current_user_id', true) OR
                scope_id IN (
                    SELECT id FROM engagement_scopes 
                    WHERE created_by = current_setting('app.current_user_id', true)
                )
            );
        
        CREATE POLICY pentest_session_admin_policy ON pentesting_sessions
            FOR ALL TO app_admin
            USING (true);
    """))
    
    connection.execute(text("""
        -- Pentesting tasks: Based on session authorization
        CREATE POLICY pentest_task_policy ON pentesting_tasks
            FOR ALL TO security_analyst
            USING (
                assigned_to = current_setting('app.current_user_id', true) OR
                session_id IN (
                    SELECT id FROM pentesting_sessions 
                    WHERE authorized_users ? current_setting('app.current_user_id', true)
                )
            )
            WITH CHECK (
                assigned_to = current_setting('app.current_user_id', true) OR
                session_id IN (
                    SELECT id FROM pentesting_sessions 
                    WHERE authorized_users ? current_setting('app.current_user_id', true)
                )
            );
        
        CREATE POLICY pentest_task_admin_policy ON pentesting_tasks
            FOR ALL TO app_admin
            USING (true);
    """))
    
    connection.execute(text("""
        -- Security findings: Discoverer and authorized session users
        CREATE POLICY finding_discovery_policy ON security_findings
            FOR ALL TO security_analyst
            USING (
                discovered_by = current_setting('app.current_user_id', true) OR
                session_id IN (
                    SELECT id FROM pentesting_sessions 
                    WHERE authorized_users ? current_setting('app.current_user_id', true)
                )
            )
            WITH CHECK (
                discovered_by = current_setting('app.current_user_id', true) OR
                session_id IN (
                    SELECT id FROM pentesting_sessions 
                    WHERE authorized_users ? current_setting('app.current_user_id', true)
                )
            );
        
        CREATE POLICY finding_admin_policy ON security_findings
            FOR ALL TO app_admin
            USING (true);
    """))
    
    connection.execute(text("""
        -- Security audit logs: Audit reviewers and involved users
        CREATE POLICY audit_log_review_policy ON security_audit_logs
            FOR SELECT TO audit_reviewer
            USING (true);
            
        CREATE POLICY audit_log_user_policy ON security_audit_logs
            FOR SELECT TO security_analyst
            USING (
                user_id = current_setting('app.current_user_id', true) OR
                session_id IN (
                    SELECT id FROM pentesting_sessions 
                    WHERE authorized_users ? current_setting('app.current_user_id', true)
                )
            );
        
        CREATE POLICY audit_log_admin_policy ON security_audit_logs
            FOR ALL TO app_admin
            USING (true);
    """))
    
    connection.execute(text("""
        -- Human approvals: Requesters and approvers  
        CREATE POLICY approval_requester_policy ON human_approvals
            FOR ALL TO app_user
            USING (
                COALESCE(requested_by, requested_by_user_id) = current_setting('app.current_user_id', true)
            )
            WITH CHECK (
                COALESCE(requested_by, requested_by_user_id) = current_setting('app.current_user_id', true)
            );
            
        CREATE POLICY approval_reviewer_policy ON human_approvals
            FOR SELECT TO security_analyst
            USING (true);
            
        CREATE POLICY approval_admin_policy ON human_approvals
            FOR ALL TO app_admin
            USING (true);
    """))
    
    # 5. Grant appropriate permissions to roles
    print("Setting up role permissions...")
    
    # Grant schema access
    connection.execute(text("""
        GRANT USAGE ON SCHEMA public TO app_user, app_admin, app_readonly, security_analyst, audit_reviewer;
    """))
    
    # Core application permissions
    connection.execute(text("""
        -- App user permissions
        GRANT SELECT, INSERT, UPDATE ON sessions, tasks, artifacts TO app_user;
        GRANT SELECT ON agents, knowledge_entries TO app_user;
        GRANT INSERT ON knowledge_entries TO app_user;
        
        -- Security analyst permissions
        GRANT SELECT, INSERT, UPDATE ON engagement_scopes, pentesting_sessions, 
              pentesting_tasks, security_findings TO security_analyst;
        GRANT INSERT ON security_audit_logs TO security_analyst;
        
        -- Audit reviewer permissions
        GRANT SELECT ON security_audit_logs, security_findings, pentesting_sessions TO audit_reviewer;
        
        -- Read-only permissions
        GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_readonly;
        
        -- Admin permissions
        GRANT ALL ON ALL TABLES IN SCHEMA public TO app_admin;
        GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO app_admin;
    """))
    
    print("Row Level Security policies successfully implemented!")


def downgrade() -> None:
    """Remove RLS and security policies"""
    
    connection = op.get_bind()
    
    # Drop all policies
    print("Dropping security policies...")
    
    tables = [
        'sessions', 'agents', 'tasks', 'artifacts', 'knowledge_entries',
        'engagement_scopes', 'pentesting_sessions', 'pentesting_tasks',
        'security_findings', 'security_audit_logs', 'human_approvals'
    ]
    
    for table in tables:
        connection.execute(text(f"DROP POLICY IF EXISTS {table}_user_policy ON {table}"))
        connection.execute(text(f"DROP POLICY IF EXISTS {table}_admin_policy ON {table}"))
        connection.execute(text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY"))
    
    # Drop specific policies
    policies_to_drop = [
        'session_user_policy', 'session_admin_policy',
        'agent_read_policy', 'agent_creator_policy',
        'task_user_policy', 'artifact_user_policy',
        'knowledge_read_policy', 'knowledge_create_policy', 'knowledge_update_policy',
        'engagement_security_policy', 'pentest_session_auth_policy', 'pentest_task_policy',
        'finding_discovery_policy', 'audit_log_review_policy', 'audit_log_user_policy',
        'approval_requester_policy', 'approval_reviewer_policy'
    ]
    
    for policy in policies_to_drop:
        for table in tables:
            connection.execute(text(f"DROP POLICY IF EXISTS {policy} ON {table}"))
    
    # Remove user_id columns
    print("Removing security columns...")
    
    op.drop_index('ix_sessions_user_id')
    op.drop_index('ix_tasks_user_id') 
    op.drop_index('ix_artifacts_user_id')
    try:
        op.drop_index('ix_pentesting_sessions_authorized_users')
    except Exception:
        pass
    
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
    # Only drop if we added it (not if requested_by exists)
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = inspector.get_columns('human_approvals')
    column_names = [col['name'] for col in columns]
    
    if 'requested_by_user_id' in column_names and 'requested_by' not in column_names:
        op.drop_column('human_approvals', 'requested_by_user_id')
    
    print("Security policies removed!")