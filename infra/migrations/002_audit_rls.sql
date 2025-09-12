-- Audit table with RLS for per-org isolation
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE TABLE IF NOT EXISTS render_audit (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id TEXT NOT NULL,
  project_id TEXT NOT NULL,
  trace_id TEXT NOT NULL,
  model_route TEXT NOT NULL,
  cost_usd NUMERIC(10,4) NOT NULL DEFAULT 0.0,
  guardrails_ok BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_render_audit_org_created ON render_audit(org_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_render_audit_project ON render_audit(project_id);

-- Enable RLS
ALTER TABLE render_audit ENABLE ROW LEVEL SECURITY;

-- Policy: tenants can only read/write their own rows
DROP POLICY IF EXISTS render_audit_tenant_rw ON render_audit;
CREATE POLICY render_audit_tenant_rw ON render_audit
USING (org_id = current_setting('app.org_id', true))
WITH CHECK (org_id = current_setting('app.org_id', true));


