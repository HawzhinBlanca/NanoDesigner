"""Initial database schema

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial database schema."""
    
    # Create projects table
    op.create_table('projects',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('status', sa.String(50), server_default='active', nullable=False),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_projects_user_id', 'user_id'),
        sa.Index('idx_projects_status', 'status'),
        sa.Index('idx_projects_created_at', 'created_at')
    )
    
    # Create assets table
    op.create_table('assets',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('url', sa.String(2048), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_assets_project_id', 'project_id'),
        sa.Index('idx_assets_type', 'type'),
        sa.Index('idx_assets_created_at', 'created_at')
    )
    
    # Create renders table
    op.create_table('renders',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('constraints', postgresql.JSONB(), nullable=True),
        sa.Column('status', sa.String(50), server_default='pending', nullable=False),
        sa.Column('result', postgresql.JSONB(), nullable=True),
        sa.Column('cost_usd', sa.Numeric(10, 4), nullable=True),
        sa.Column('model_used', sa.String(255), nullable=True),
        sa.Column('trace_id', sa.String(255), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_renders_project_id', 'project_id'),
        sa.Index('idx_renders_status', 'status'),
        sa.Index('idx_renders_created_at', 'created_at'),
        sa.Index('idx_renders_trace_id', 'trace_id')
    )
    
    # Create brand_canons table
    op.create_table('brand_canons',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('brand_name', sa.String(255), nullable=False),
        sa.Column('canon_data', postgresql.JSONB(), nullable=False),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'version', name='uq_brand_canon_version'),
        sa.Index('idx_brand_canons_project_id', 'project_id'),
        sa.Index('idx_brand_canons_is_active', 'is_active')
    )
    
    # Create critiques table
    op.create_table('critiques',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('asset_id', sa.String(36), nullable=False),
        sa.Column('score', sa.Numeric(3, 1), nullable=False),
        sa.Column('feedback', sa.Text(), nullable=False),
        sa.Column('suggestions', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('criteria', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_critiques_asset_id', 'asset_id'),
        sa.Index('idx_critiques_score', 'score')
    )
    
    # Create audit_logs table for tracking all operations
    op.create_table('audit_logs',
        sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column('user_id', sa.String(255), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('resource_id', sa.String(36), nullable=True),
        sa.Column('request_data', postgresql.JSONB(), nullable=True),
        sa.Column('response_data', postgresql.JSONB(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_audit_logs_user_id', 'user_id'),
        sa.Index('idx_audit_logs_action', 'action'),
        sa.Index('idx_audit_logs_resource', 'resource_type', 'resource_id'),
        sa.Index('idx_audit_logs_created_at', 'created_at')
    )
    
    # Create job_queue table for async processing
    op.create_table('job_queue',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), server_default='pending', nullable=False),
        sa.Column('priority', sa.Integer(), server_default='5', nullable=False),
        sa.Column('payload', postgresql.JSONB(), nullable=False),
        sa.Column('result', postgresql.JSONB(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('attempts', sa.Integer(), server_default='0', nullable=False),
        sa.Column('max_attempts', sa.Integer(), server_default='3', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scheduled_for', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_job_queue_status', 'status'),
        sa.Index('idx_job_queue_type', 'type'),
        sa.Index('idx_job_queue_priority_scheduled', 'priority', 'scheduled_for'),
        sa.Index('idx_job_queue_created_at', 'created_at')
    )
    
    # Create function for updating updated_at timestamp
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    # Create triggers for auto-updating updated_at
    for table in ['projects', 'assets', 'brand_canons']:
        op.execute(f"""
            CREATE TRIGGER update_{table}_updated_at 
            BEFORE UPDATE ON {table}
            FOR EACH ROW 
            EXECUTE FUNCTION update_updated_at_column();
        """)


def downgrade() -> None:
    """Drop all tables and functions."""
    
    # Drop triggers
    for table in ['projects', 'assets', 'brand_canons']:
        op.execute(f"DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table};")
    
    # Drop function
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")
    
    # Drop tables in reverse order due to foreign keys
    op.drop_table('job_queue')
    op.drop_table('audit_logs')
    op.drop_table('critiques')
    op.drop_table('brand_canons')
    op.drop_table('renders')
    op.drop_table('assets')
    op.drop_table('projects')