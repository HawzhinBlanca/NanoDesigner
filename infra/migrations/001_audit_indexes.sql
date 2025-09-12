-- Database indexes for performance optimization
-- These indexes support the audit and query patterns in the application

-- Create render_audit table if it doesn't exist
CREATE TABLE IF NOT EXISTS render_audit (
    id SERIAL PRIMARY KEY,
    org_id VARCHAR(128) NOT NULL,
    project_id VARCHAR(128) NOT NULL,
    trace_id VARCHAR(128) NOT NULL UNIQUE,
    model_route VARCHAR(256) NOT NULL,
    cost_usd DECIMAL(10,6) NOT NULL DEFAULT 0.0,
    guardrails_ok BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for render_audit table
-- Primary lookup by org_id (most common query pattern)
CREATE INDEX IF NOT EXISTS idx_render_audit_org_id ON render_audit(org_id);

-- Lookup by org_id and created_at for time-based queries
CREATE INDEX IF NOT EXISTS idx_render_audit_org_created ON render_audit(org_id, created_at DESC);

-- Lookup by trace_id for debugging and correlation
CREATE INDEX IF NOT EXISTS idx_render_audit_trace_id ON render_audit(trace_id);

-- Lookup by project_id for project-specific reports
CREATE INDEX IF NOT EXISTS idx_render_audit_project_id ON render_audit(project_id);

-- Composite index for cost analysis queries
CREATE INDEX IF NOT EXISTS idx_render_audit_cost_analysis ON render_audit(org_id, model_route, created_at DESC);

-- Index for guardrails monitoring
CREATE INDEX IF NOT EXISTS idx_render_audit_guardrails ON render_audit(guardrails_ok, created_at DESC);

-- Partial index for failed renders (assuming guardrails_ok=false indicates issues)
CREATE INDEX IF NOT EXISTS idx_render_audit_failed ON render_audit(org_id, created_at DESC) 
WHERE guardrails_ok = false;

-- Create cost_tracking table for budget controls
CREATE TABLE IF NOT EXISTS cost_tracking (
    id SERIAL PRIMARY KEY,
    org_id VARCHAR(128) NOT NULL,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    model VARCHAR(256) NOT NULL,
    task_type VARCHAR(128) NOT NULL,
    total_cost_usd DECIMAL(10,6) NOT NULL DEFAULT 0.0,
    request_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(org_id, date, model, task_type)
);

-- Indexes for cost_tracking table
-- Primary lookup by org_id and date
CREATE INDEX IF NOT EXISTS idx_cost_tracking_org_date ON cost_tracking(org_id, date DESC);

-- Lookup for budget enforcement
CREATE INDEX IF NOT EXISTS idx_cost_tracking_budget ON cost_tracking(org_id, date, total_cost_usd DESC);

-- Model usage analysis
CREATE INDEX IF NOT EXISTS idx_cost_tracking_model ON cost_tracking(model, date DESC);

-- Create brand_canon table for storing brand guidelines
CREATE TABLE IF NOT EXISTS brand_canon (
    id SERIAL PRIMARY KEY,
    org_id VARCHAR(128) NOT NULL,
    project_id VARCHAR(128) NOT NULL,
    canon_data JSONB NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(org_id, project_id, version)
);

-- Indexes for brand_canon table
-- Primary lookup by org_id and project_id
CREATE INDEX IF NOT EXISTS idx_brand_canon_org_project ON brand_canon(org_id, project_id);

-- Active canon lookup
CREATE INDEX IF NOT EXISTS idx_brand_canon_active ON brand_canon(org_id, project_id, is_active, version DESC);

-- JSONB search capabilities for canon_data
CREATE INDEX IF NOT EXISTS idx_brand_canon_data ON brand_canon USING GIN (canon_data);

-- Create user_sessions table for session management
CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(128) NOT NULL UNIQUE,
    user_id VARCHAR(128) NOT NULL,
    org_id VARCHAR(128) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_activity TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for user_sessions table
-- Session lookup
CREATE INDEX IF NOT EXISTS idx_user_sessions_session_id ON user_sessions(session_id);

-- User activity lookup
CREATE INDEX IF NOT EXISTS idx_user_sessions_user ON user_sessions(user_id, last_activity DESC);

-- Cleanup expired sessions
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires ON user_sessions(expires_at) WHERE expires_at > NOW();

-- Row Level Security (RLS) policies for multi-tenant isolation
ALTER TABLE render_audit ENABLE ROW LEVEL SECURITY;
ALTER TABLE cost_tracking ENABLE ROW LEVEL SECURITY;
ALTER TABLE brand_canon ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;

-- RLS policy for render_audit
DROP POLICY IF EXISTS render_audit_tenant_isolation ON render_audit;
CREATE POLICY render_audit_tenant_isolation ON render_audit
    USING (org_id = current_setting('app.org_id', true));

-- RLS policy for cost_tracking
DROP POLICY IF EXISTS cost_tracking_tenant_isolation ON cost_tracking;
CREATE POLICY cost_tracking_tenant_isolation ON cost_tracking
    USING (org_id = current_setting('app.org_id', true));

-- RLS policy for brand_canon
DROP POLICY IF EXISTS brand_canon_tenant_isolation ON brand_canon;
CREATE POLICY brand_canon_tenant_isolation ON brand_canon
    USING (org_id = current_setting('app.org_id', true));

-- RLS policy for user_sessions
DROP POLICY IF EXISTS user_sessions_tenant_isolation ON user_sessions;
CREATE POLICY user_sessions_tenant_isolation ON user_sessions
    USING (org_id = current_setting('app.org_id', true));

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add triggers for updated_at columns
DROP TRIGGER IF EXISTS update_render_audit_updated_at ON render_audit;
CREATE TRIGGER update_render_audit_updated_at
    BEFORE UPDATE ON render_audit
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_cost_tracking_updated_at ON cost_tracking;
CREATE TRIGGER update_cost_tracking_updated_at
    BEFORE UPDATE ON cost_tracking
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_brand_canon_updated_at ON brand_canon;
CREATE TRIGGER update_brand_canon_updated_at
    BEFORE UPDATE ON brand_canon
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create indexes for better performance
-- Vacuum and analyze tables for optimal performance
VACUUM ANALYZE render_audit;
VACUUM ANALYZE cost_tracking;
VACUUM ANALYZE brand_canon;
VACUUM ANALYZE user_sessions;