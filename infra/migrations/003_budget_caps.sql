-- Budget caps and usage accrual

CREATE TABLE IF NOT EXISTS org_budgets (
  org_id TEXT PRIMARY KEY,
  daily_budget_usd NUMERIC(12,4) NOT NULL DEFAULT 0.0,
  monthly_budget_usd NUMERIC(12,4) NOT NULL DEFAULT 0.0,
  alert_thresholds NUMERIC[] NOT NULL DEFAULT ARRAY[0.5,0.8,1.0],
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS org_usage_daily (
  org_id TEXT NOT NULL,
  usage_date DATE NOT NULL DEFAULT CURRENT_DATE,
  spend_usd NUMERIC(12,4) NOT NULL DEFAULT 0.0,
  PRIMARY KEY (org_id, usage_date)
);

CREATE INDEX IF NOT EXISTS idx_org_usage_daily_org_date ON org_usage_daily(org_id, usage_date);


