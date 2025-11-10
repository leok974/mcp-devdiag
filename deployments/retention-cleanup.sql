-- Data Retention Script for DevDiag PostgreSQL
-- Run this daily via cron, systemd timer, or container scheduler
-- Retains 180 days of data per devdiag.yaml configuration

-- Delete old diagnostic runs (180 days)
DELETE FROM devdiag.diag_run
WHERE ts < NOW() - INTERVAL '180 days';

-- Delete old fix outcomes (180 days based on last_seen, or use ts if last_seen doesn't exist)
-- Note: fix_outcome doesn't have last_seen in current schema, using ts as fallback
DELETE FROM devdiag.fix_outcome
WHERE ts < NOW() - INTERVAL '180 days';

-- Vacuum and analyze to reclaim space and update statistics
VACUUM (ANALYZE) devdiag.diag_run;
VACUUM (ANALYZE) devdiag.fix_outcome;

-- Optional: Report cleanup results
SELECT 
  'diag_run' AS table_name,
  COUNT(*) AS remaining_rows,
  MIN(ts) AS oldest_record,
  MAX(ts) AS newest_record
FROM devdiag.diag_run
UNION ALL
SELECT 
  'fix_outcome',
  COUNT(*),
  MIN(ts),
  MAX(ts)
FROM devdiag.fix_outcome;
