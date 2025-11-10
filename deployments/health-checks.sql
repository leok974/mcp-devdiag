-- DevDiag Data Hygiene & Health Checks
-- Run these periodically to monitor database health and data quality

-- =============================================================================
-- 1) NEW ROWS TODAY
-- =============================================================================
-- Check that diagnostic runs are being ingested today
-- Expected: > 0 (depends on probe frequency)

SELECT 'new_rows_today' AS check_name,
       COUNT(*) AS value,
       CASE 
         WHEN COUNT(*) > 0 THEN 'PASS'
         ELSE 'FAIL - No data ingested today'
       END AS status
FROM devdiag.diag_run 
WHERE ts::date = CURRENT_DATE;

-- =============================================================================
-- 2) 7-DAY RUN VOLUME TREND
-- =============================================================================
-- Monitor daily diagnostic run counts to detect pipeline issues
-- Expected: Consistent daily volumes (varies by deployment)

SELECT ts::date AS day, 
       COUNT(*) AS runs,
       CASE 
         WHEN COUNT(*) = 0 THEN 'WARN - No runs this day'
         ELSE 'OK'
       END AS status
FROM devdiag.diag_run 
WHERE ts >= NOW() - INTERVAL '7 days'
GROUP BY 1 
ORDER BY 1;

-- =============================================================================
-- 3) UNLEARNED PROBLEMS (No Recorded Fixes)
-- =============================================================================
-- Identify problem codes that appear frequently but have no fix suggestions
-- These represent learning opportunities

SELECT r.problem_code, 
       SUM(r.runs) AS total_runs,
       COUNT(DISTINCT r.tenant) AS affected_tenants,
       'UNLEARNED - Consider adding fix patterns' AS status
FROM devdiag.v_problem_counts r
LEFT JOIN devdiag.v_fix_success f USING (problem_code)
WHERE f.problem_code IS NULL
  AND r.day >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY 1 
ORDER BY total_runs DESC;

-- =============================================================================
-- 4) DATA RETENTION CHECK
-- =============================================================================
-- Verify retention policy is working (should keep ~180 days)
-- Expected: oldest_record between 170-190 days old

SELECT 'retention_check' AS check_name,
       MIN(ts) AS oldest_record,
       MAX(ts) AS newest_record,
       EXTRACT(DAY FROM (NOW() - MIN(ts))) AS days_retained,
       CASE 
         WHEN EXTRACT(DAY FROM (NOW() - MIN(ts))) BETWEEN 170 AND 190 THEN 'PASS'
         WHEN EXTRACT(DAY FROM (NOW() - MIN(ts))) > 190 THEN 'WARN - Retention not running'
         ELSE 'OK - Still accumulating data'
       END AS status
FROM devdiag.diag_run;

-- =============================================================================
-- 5) FIX CONFIDENCE QUALITY
-- =============================================================================
-- Monitor average confidence scores to detect learning degradation
-- Expected: >= 0.70

SELECT 'fix_confidence' AS check_name,
       ROUND(AVG(avg_confidence)::numeric, 3) AS avg_confidence,
       COUNT(*) AS fix_count,
       CASE 
         WHEN AVG(avg_confidence) >= 0.70 THEN 'PASS'
         WHEN AVG(avg_confidence) >= 0.50 THEN 'WARN - Confidence degrading'
         ELSE 'FAIL - Poor learning quality'
       END AS status
FROM devdiag.v_fix_success
WHERE last_success >= NOW() - INTERVAL '30 days';

-- =============================================================================
-- 6) DATABASE SIZE MONITORING
-- =============================================================================
-- Track table sizes to plan capacity

SELECT schemaname,
       tablename,
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
       pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
       pg_size_pretty(pg_indexes_size(schemaname||'.'||tablename)) AS indexes_size
FROM pg_tables
WHERE schemaname = 'devdiag'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- =============================================================================
-- 7) VIEW DEPENDENCY CHECK
-- =============================================================================
-- Ensure all 6 analytics views exist
-- Expected: 6 views

SELECT 'view_count' AS check_name,
       COUNT(*) AS view_count,
       CASE 
         WHEN COUNT(*) = 6 THEN 'PASS'
         ELSE 'FAIL - Missing views'
       END AS status
FROM pg_views 
WHERE schemaname = 'devdiag' 
  AND viewname IN ('v_problem_counts', 'v_fix_success', 'v_ttr_days', 
                   'v_env_diversity', 'v_fix_ranking', 'v_recent_activity');

-- =============================================================================
-- 8) INDEX HEALTH CHECK
-- =============================================================================
-- Verify all performance indexes exist
-- Expected: 9 indexes (including GIN index on problems JSONB)

SELECT 'index_count' AS check_name,
       COUNT(*) AS index_count,
       CASE 
         WHEN COUNT(*) >= 9 THEN 'PASS'
         WHEN COUNT(*) >= 8 THEN 'WARN - Missing GIN index'
         ELSE 'FAIL - Critical indexes missing'
       END AS status
FROM pg_indexes 
WHERE schemaname = 'devdiag';

-- List all indexes with sizes
SELECT indexname,
       tablename,
       pg_size_pretty(pg_relation_size(schemaname||'.'||indexname)) AS index_size
FROM pg_indexes
WHERE schemaname = 'devdiag'
ORDER BY pg_relation_size(schemaname||'.'||indexname) DESC;

-- =============================================================================
-- 9) STALE DATA DETECTION
-- =============================================================================
-- Alert if no recent data (indicates pipeline failure)
-- Expected: Last run within last 2 hours

SELECT 'data_freshness' AS check_name,
       MAX(ts) AS last_run,
       EXTRACT(EPOCH FROM (NOW() - MAX(ts))) AS seconds_since_last_run,
       CASE 
         WHEN MAX(ts) >= NOW() - INTERVAL '2 hours' THEN 'PASS'
         WHEN MAX(ts) >= NOW() - INTERVAL '6 hours' THEN 'WARN - Data getting stale'
         ELSE 'FAIL - Pipeline may be down'
       END AS status
FROM devdiag.diag_run;

-- =============================================================================
-- 10) PROBLEM DIVERSITY TREND
-- =============================================================================
-- Track number of unique problems per day (detect instability)
-- Expected: < 10 distinct problems per day

SELECT ts::date AS day,
       COUNT(DISTINCT jsonb_array_elements_text(problems)) AS distinct_problems,
       COUNT(*) AS total_runs,
       CASE 
         WHEN COUNT(DISTINCT jsonb_array_elements_text(problems)) > 10 THEN 'WARN - High diversity'
         ELSE 'OK'
       END AS status
FROM devdiag.diag_run
WHERE ts >= NOW() - INTERVAL '7 days'
GROUP BY 1
ORDER BY 1 DESC;

-- =============================================================================
-- SUMMARY DASHBOARD QUERY
-- =============================================================================
-- Single query for health dashboard
-- Returns all key metrics

WITH health_metrics AS (
  SELECT 
    'Rows Today' AS metric,
    COUNT(*)::text AS value,
    CASE WHEN COUNT(*) > 0 THEN 'OK' ELSE 'FAIL' END AS status
  FROM devdiag.diag_run WHERE ts::date = CURRENT_DATE
  
  UNION ALL
  
  SELECT 
    'Data Freshness',
    EXTRACT(EPOCH FROM (NOW() - MAX(ts)))::int::text || ' seconds',
    CASE 
      WHEN MAX(ts) >= NOW() - INTERVAL '2 hours' THEN 'OK'
      ELSE 'FAIL'
    END
  FROM devdiag.diag_run
  
  UNION ALL
  
  SELECT 
    'Avg Fix Confidence',
    ROUND(AVG(avg_confidence)::numeric, 2)::text,
    CASE WHEN AVG(avg_confidence) >= 0.70 THEN 'OK' ELSE 'WARN' END
  FROM devdiag.v_fix_success
  WHERE last_success >= NOW() - INTERVAL '30 days'
  
  UNION ALL
  
  SELECT 
    'Views Present',
    COUNT(*)::text || '/6',
    CASE WHEN COUNT(*) = 6 THEN 'OK' ELSE 'FAIL' END
  FROM pg_views 
  WHERE schemaname = 'devdiag'
    AND viewname IN ('v_problem_counts', 'v_fix_success', 'v_ttr_days', 
                     'v_env_diversity', 'v_fix_ranking', 'v_recent_activity')
  
  UNION ALL
  
  SELECT 
    'Indexes Present',
    COUNT(*)::text || '/9',
    CASE WHEN COUNT(*) >= 9 THEN 'OK' ELSE 'WARN' END
  FROM pg_indexes 
  WHERE schemaname = 'devdiag'
)
SELECT * FROM health_metrics ORDER BY status DESC, metric;
