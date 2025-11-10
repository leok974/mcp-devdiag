-- DevDiag Analytics Schema for PostgreSQL
-- Run once to initialize the database structure and views

CREATE SCHEMA IF NOT EXISTS devdiag;

-- Diagnostic runs table
CREATE TABLE IF NOT EXISTS devdiag.diag_run(
  id BIGSERIAL PRIMARY KEY,
  ts TIMESTAMP NOT NULL,
  tenant TEXT NOT NULL,
  target_hash TEXT NOT NULL,
  env_fp TEXT NOT NULL,
  problems JSONB NOT NULL,
  evidence JSONB NOT NULL,
  preset TEXT
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_diag_run_tenant_ts ON devdiag.diag_run(tenant, ts DESC);
CREATE INDEX IF NOT EXISTS idx_diag_run_target_ts ON devdiag.diag_run(target_hash, ts DESC);
CREATE INDEX IF NOT EXISTS idx_diag_run_ts ON devdiag.diag_run(ts DESC);

-- Fix outcomes table
CREATE TABLE IF NOT EXISTS devdiag.fix_outcome(
  id BIGSERIAL PRIMARY KEY,
  ts TIMESTAMP NOT NULL,
  tenant TEXT NOT NULL,
  problem_code TEXT NOT NULL,
  fix_code TEXT NOT NULL,
  confidence DOUBLE PRECISION NOT NULL,
  support INTEGER NOT NULL,
  env_fp TEXT NOT NULL,
  notes TEXT,
  UNIQUE (tenant, problem_code, fix_code, env_fp)
);

-- Indexes for fix outcomes
CREATE INDEX IF NOT EXISTS idx_fix_outcome_tenant_problem ON devdiag.fix_outcome(tenant, problem_code);
CREATE INDEX IF NOT EXISTS idx_fix_outcome_support ON devdiag.fix_outcome(support DESC);

-- =============================================================================
-- ANALYTICS VIEWS (Tableau-ready)
-- =============================================================================

-- View: Problem counts over time
CREATE OR REPLACE VIEW devdiag.v_problem_counts AS
SELECT
  date_trunc('day', ts) AS day,
  tenant,
  jsonb_array_elements_text(problems) AS problem_code,
  count(*) AS runs
FROM devdiag.diag_run
GROUP BY 1, 2, 3;

COMMENT ON VIEW devdiag.v_problem_counts IS 'Daily problem occurrence counts by tenant and problem code';

-- View: Fix success metrics
CREATE OR REPLACE VIEW devdiag.v_fix_success AS
SELECT
  tenant,
  problem_code,
  fix_code,
  sum(support) AS successes,
  avg(confidence) AS avg_confidence,
  max(ts) AS last_success
FROM devdiag.fix_outcome
GROUP BY 1, 2, 3;

COMMENT ON VIEW devdiag.v_fix_success IS 'Aggregated fix success rates with confidence scores';

-- View: Time-to-Remediation (TTR) estimation
CREATE OR REPLACE VIEW devdiag.v_ttr_days AS
WITH seen AS (
  SELECT
    tenant,
    target_hash,
    jsonb_array_elements_text(problems) AS problem_code,
    min(ts) AS first_seen
  FROM devdiag.diag_run
  GROUP BY 1, 2, 3
),
series AS (
  SELECT
    s.tenant,
    s.target_hash,
    s.problem_code,
    s.first_seen::date AS start_day,
    generate_series(s.first_seen::date, current_date, '1 day'::interval) AS d
  FROM seen s
),
daily_problems AS (
  SELECT
    r.tenant,
    r.target_hash,
    r.ts::date AS d,
    jsonb_array_elements_text(r.problems) AS problem_code
  FROM devdiag.diag_run r
),
counts AS (
  SELECT
    sr.tenant,
    sr.target_hash,
    sr.problem_code,
    sr.d,
    sr.start_day,
    count(dp.problem_code) AS hits
  FROM series sr
  LEFT JOIN daily_problems dp
    ON dp.tenant = sr.tenant
    AND dp.target_hash = sr.target_hash
    AND dp.d = sr.d
    AND dp.problem_code = sr.problem_code
  GROUP BY 1, 2, 3, 4, 5
),
first_zero AS (
  SELECT
    tenant,
    target_hash,
    problem_code,
    min(d) FILTER (WHERE hits = 0 AND d > start_day) AS first_zero_day,
    min(start_day) AS first_seen_day
  FROM counts
  GROUP BY 1, 2, 3
)
SELECT
  tenant,
  problem_code,
  target_hash,
  first_seen_day,
  first_zero_day,
  (first_zero_day - first_seen_day) AS ttr_days
FROM first_zero
WHERE first_zero_day IS NOT NULL;

COMMENT ON VIEW devdiag.v_ttr_days IS 'Time-to-remediation estimates (first seen to first day gone)';

-- View: Environment fingerprint analysis
CREATE OR REPLACE VIEW devdiag.v_env_diversity AS
SELECT
  tenant,
  jsonb_array_elements_text(problems) AS problem_code,
  count(DISTINCT env_fp) AS unique_environments,
  count(*) AS total_runs
FROM devdiag.diag_run
GROUP BY 1, 2;

COMMENT ON VIEW devdiag.v_env_diversity IS 'Environment diversity per problem (how many unique environments see each problem)';

-- View: Recent diagnostic activity
CREATE OR REPLACE VIEW devdiag.v_recent_activity AS
SELECT
  tenant,
  target_hash,
  ts,
  jsonb_array_length(problems) AS problem_count,
  problems,
  preset
FROM devdiag.diag_run
WHERE ts > now() - interval '7 days'
ORDER BY ts DESC;

COMMENT ON VIEW devdiag.v_recent_activity IS 'Recent diagnostic runs (last 7 days)';

-- View: Fix effectiveness ranking
CREATE OR REPLACE VIEW devdiag.v_fix_ranking AS
SELECT
  problem_code,
  fix_code,
  successes,
  avg_confidence,
  rank() OVER (PARTITION BY problem_code ORDER BY successes DESC, avg_confidence DESC) AS rank
FROM devdiag.v_fix_success;

COMMENT ON VIEW devdiag.v_fix_ranking IS 'Ranked fixes per problem by success count and confidence';

-- Grant permissions (adjust as needed for your security model)
GRANT USAGE ON SCHEMA devdiag TO devdiag;
GRANT SELECT ON ALL TABLES IN SCHEMA devdiag TO devdiag;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA devdiag TO devdiag;
