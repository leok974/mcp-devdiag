-- Create read-only Grafana user for DevDiag PostgreSQL
-- Run this as the devdiag user or a superuser

-- Create the grafana role
CREATE ROLE grafana LOGIN PASSWORD 'StrongGrafanaPass!';

-- Grant schema usage
GRANT USAGE ON SCHEMA devdiag TO grafana;

-- Grant SELECT on all existing tables and views
GRANT SELECT ON ALL TABLES IN SCHEMA devdiag TO grafana;

-- Grant SELECT on sequences (for future-proofing)
GRANT SELECT ON ALL SEQUENCES IN SCHEMA devdiag TO grafana;

-- Ensure future tables are also readable
ALTER DEFAULT PRIVILEGES IN SCHEMA devdiag GRANT SELECT ON TABLES TO grafana;

-- Verify grants
\du grafana
\z devdiag.*

-- To use this user in Grafana:
-- Update datasource configuration with:
--   user: grafana
--   password: StrongGrafanaPass!
