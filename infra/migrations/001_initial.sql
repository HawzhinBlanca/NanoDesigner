-- Initial database schema for Smart Graphic Designer
-- Postgres 16+

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Projects table
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    organization_id VARCHAR(255) NOT NULL,
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT true
);

CREATE INDEX idx_projects_org_id ON projects(organization_id);
CREATE INDEX idx_projects_created_by ON projects(created_by);

-- Brand canon table
CREATE TABLE IF NOT EXISTS brand_canons (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    version INTEGER NOT NULL DEFAULT 1,
    canon_data JSONB NOT NULL,
    derived_from TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true,
    UNIQUE(project_id, version)
);

CREATE INDEX idx_brand_canons_project_id ON brand_canons(project_id);
CREATE INDEX idx_brand_canons_active ON brand_canons(is_active);

-- Render jobs table
CREATE TABLE IF NOT EXISTS render_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    request_data JSONB NOT NULL,
    response_data JSONB,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    trace_id VARCHAR(255),
    cost_usd DECIMAL(10, 4),
    model_route VARCHAR(255),
    guardrails_ok BOOLEAN
);

CREATE INDEX idx_render_jobs_project_id ON render_jobs(project_id);
CREATE INDEX idx_render_jobs_status ON render_jobs(status);
CREATE INDEX idx_render_jobs_created_at ON render_jobs(created_at);
CREATE INDEX idx_render_jobs_trace_id ON render_jobs(trace_id);

-- Assets table
CREATE TABLE IF NOT EXISTS assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    render_job_id UUID REFERENCES render_jobs(id) ON DELETE SET NULL,
    asset_type VARCHAR(50) NOT NULL,
    r2_key VARCHAR(500) NOT NULL,
    url TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    synthid_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    is_public BOOLEAN DEFAULT false
);

CREATE INDEX idx_assets_project_id ON assets(project_id);
CREATE INDEX idx_assets_render_job_id ON assets(render_job_id);
CREATE INDEX idx_assets_r2_key ON assets(r2_key);
CREATE INDEX idx_assets_type ON assets(asset_type);

-- Ingested documents table
CREATE TABLE IF NOT EXISTS ingested_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    document_name VARCHAR(500) NOT NULL,
    document_type VARCHAR(50),
    r2_key VARCHAR(500),
    qdrant_ids TEXT[],
    extracted_data JSONB,
    processing_status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT
);

CREATE INDEX idx_ingested_documents_project_id ON ingested_documents(project_id);
CREATE INDEX idx_ingested_documents_status ON ingested_documents(processing_status);

-- Critique results table
CREATE TABLE IF NOT EXISTS critique_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    asset_ids TEXT[],
    score DECIMAL(3, 2),
    violations JSONB DEFAULT '[]'::jsonb,
    repair_suggestions JSONB DEFAULT '[]'::jsonb,
    trace_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_critique_results_project_id ON critique_results(project_id);
CREATE INDEX idx_critique_results_created_at ON critique_results(created_at);

-- Audit log table (append-only)
CREATE TABLE IF NOT EXISTS audit_log (
    id BIGSERIAL PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    user_id VARCHAR(255),
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    action VARCHAR(50),
    metadata JSONB DEFAULT '{}'::jsonb,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_audit_log_project_id ON audit_log(project_id);
CREATE INDEX idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at);
CREATE INDEX idx_audit_log_event_type ON audit_log(event_type);

-- API keys table (for service-to-service auth)
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key_hash VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    organization_id VARCHAR(255) NOT NULL,
    permissions JSONB DEFAULT '[]'::jsonb,
    rate_limit_per_minute INTEGER DEFAULT 100,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true
);

CREATE INDEX idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX idx_api_keys_org_id ON api_keys(organization_id);
CREATE INDEX idx_api_keys_active ON api_keys(is_active);

-- Rate limiting table
CREATE TABLE IF NOT EXISTS rate_limits (
    id BIGSERIAL PRIMARY KEY,
    key_identifier VARCHAR(255) NOT NULL,
    window_start TIMESTAMP WITH TIME ZONE NOT NULL,
    request_count INTEGER DEFAULT 1,
    UNIQUE(key_identifier, window_start)
);

CREATE INDEX idx_rate_limits_key_window ON rate_limits(key_identifier, window_start);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add updated_at triggers
CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_brand_canons_updated_at BEFORE UPDATE ON brand_canons
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE projects IS 'Projects/workspaces for brand asset management';
COMMENT ON TABLE brand_canons IS 'Brand guidelines and canonical styles per project';
COMMENT ON TABLE render_jobs IS 'Image generation job tracking';
COMMENT ON TABLE assets IS 'Generated and uploaded assets';
COMMENT ON TABLE ingested_documents IS 'Documents processed for brand extraction';
COMMENT ON TABLE critique_results IS 'Asset evaluation against brand canon';
COMMENT ON TABLE audit_log IS 'Append-only audit trail for compliance';
COMMENT ON TABLE api_keys IS 'Service-to-service authentication keys';
COMMENT ON TABLE rate_limits IS 'API rate limiting tracking';