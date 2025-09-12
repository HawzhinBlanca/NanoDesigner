-- Performance optimization indexes
-- Migration: 002_performance_indexes.sql
-- Created: 2025-01-08
-- Purpose: Add critical indexes for production performance

-- Index on project_id for frequent project-based queries
CREATE INDEX IF NOT EXISTS idx_assets_project_id ON assets(project_id);
CREATE INDEX IF NOT EXISTS idx_render_jobs_project_id ON render_jobs(project_id);

-- (org_id columns do not exist in initial schema; skip)

-- (org_id + project_id composite skipped; org_id not present)

CREATE INDEX IF NOT EXISTS idx_assets_created_at ON assets(created_at);
CREATE INDEX IF NOT EXISTS idx_render_jobs_created_at ON render_jobs(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at);

-- Index on status for job monitoring queries
CREATE INDEX IF NOT EXISTS idx_render_jobs_status ON render_jobs(status);

-- Composite index for active job queries
CREATE INDEX IF NOT EXISTS idx_render_jobs_status_created ON render_jobs(status, created_at);

-- (user_id columns not present; skip)

-- Index on asset_type for filtering
CREATE INDEX IF NOT EXISTS idx_assets_type ON assets(asset_type);

-- Partial index on failed jobs for monitoring
CREATE INDEX IF NOT EXISTS idx_render_jobs_failed ON render_jobs(created_at) 
WHERE status IN ('failed', 'error');

-- Index on trace_id for debugging and monitoring
CREATE INDEX IF NOT EXISTS idx_render_jobs_trace_id ON render_jobs(trace_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_trace_id ON audit_logs(trace_id);

-- Index on cost tracking for billing queries
CREATE INDEX IF NOT EXISTS idx_render_jobs_cost ON render_jobs(cost_usd);
CREATE INDEX IF NOT EXISTS idx_render_jobs_org_cost_date ON render_jobs(org_id, created_at, cost_usd);

-- (columns not present; skip)

ANALYZE assets;
ANALYZE render_jobs;
ANALYZE audit_log;



