# DevDiag Grafana Alerts

**Status:** Manual Import Required  
**Grafana Version:** 9.0+ (Unified Alerting)

---

## Overview

This directory contains 5 production-ready alert definitions for monitoring DevDiag's analytics pipeline and learning system.

**Alert Coverage:**
1. **Top Problem Dominates** - Detects when a single problem affects >20% of runs
2. **Runs Stalled** - Critical alert when no runs logged for 2+ hours
3. **TTR Regression** - Warns when median time-to-resolution exceeds 2 days
4. **Confidence Drop** - Monitors learning model quality (avg confidence <70%)
5. **High Diversity** - Identifies system instability (>10 unique problems/day)

---

## Current Status

**Automated Import:** ⚠️ Work in Progress

The alert JSON files in this directory use Grafana's dashboard export format, but the provisioning API requires a different structure. Automated import via `import-alerts.ps1` will be updated in a future commit.

**Workaround:** Manual import via Grafana UI (see instructions below)

---

## Manual Setup (Recommended for v0.3.0)

### Method 1: Create Alerts via Grafana UI

Instead of importing JSON, create alerts directly in Grafana:

1. **Open Grafana Alerting:**
   - Navigate to: http://localhost:3000/alerting/list
   - Click "New alert rule"

2. **Alert 1: Runs Stalled (CRITICAL)**
   
   **Query A (PostgreSQL):**
   ```sql
   SELECT
     ts AS time,
     1 AS value
   FROM devdiag.diag_run
   WHERE $__timeFilter(ts)
   ORDER BY ts DESC
   LIMIT 1;
   ```
   - Datasource: `DevDiag Postgres`
   - Relative time: Last 2 hours

   **Condition B (Expression):**
   - Type: Classic condition
   - WHEN: `last()` of `A`
   - IS: `no value`
   
   **Alert Details:**
   - Alert name: `DevDiag: Diagnostic runs stalled (2h)`
   - Folder: `DevDiag Alerts` (create if needed)
   - Evaluation group: `devdiag-health`
   - Evaluation interval: `5m`
   - Pending period: `5m`
   
   **Annotations:**
   - Summary: `Diagnostic pipeline has stalled`
   - Description: `No diagnostic runs have been recorded in the last 2 hours. This indicates a pipeline failure or integration issue.`
   - Runbook URL: `https://github.com/leok974/mcp-devdiag/blob/main/deployments/OPERATIONS.md#2-runs-stalled-severity-critical`
   
   **Labels:**
   - `severity`: `critical`
   - `team`: `devdiag`
   - `component`: `pipeline`

---

3. **Alert 2: Confidence Drop (WARNING)**
   
   **Query A (PostgreSQL):**
   ```sql
   SELECT
     NOW() AS time,
     AVG(avg_confidence) AS value
   FROM devdiag.v_fix_success
   WHERE last_success >= NOW() - INTERVAL '7 days';
   ```
   - Datasource: `DevDiag Postgres`
   
   **Condition B (Expression):**
   - Type: Classic condition
   - WHEN: `last()` of `A`
   - IS BELOW: `0.70`
   
   **Alert Details:**
   - Alert name: `DevDiag: Fix confidence <70% (7d)`
   - Folder: `DevDiag Alerts`
   - Evaluation group: `devdiag-learning`
   - Evaluation interval: `30m`
   - Pending period: `30m`
   
   **Annotations:**
   - Summary: `Learning model confidence has degraded`
   - Description: `Average fix confidence over the last 7 days has dropped below 70%, indicating reduced learning effectiveness.`
   - Runbook URL: `https://github.com/leok974/mcp-devdiag/blob/main/deployments/OPERATIONS.md#4-confidence-drop-severity-warning`
   
   **Labels:**
   - `severity`: `warning`
   - `team`: `devdiag`
   - `component`: `learning`

---

4. **Alert 3: High Diversity (WARNING)**
   
   **Query A (PostgreSQL):**
   ```sql
   SELECT
     NOW() AS time,
     COUNT(DISTINCT problem_code) AS value
   FROM devdiag.v_problem_counts
   WHERE day = CURRENT_DATE;
   ```
   - Datasource: `DevDiag Postgres`
   
   **Condition B (Expression):**
   - Type: Classic condition
   - WHEN: `last()` of `A`
   - IS ABOVE: `10`
   
   **Alert Details:**
   - Alert name: `DevDiag: High problem diversity (today)`
   - Folder: `DevDiag Alerts`
   - Evaluation group: `devdiag-health`
   - Evaluation interval: `15m`
   - Pending period: `15m`
   
   **Annotations:**
   - Summary: `System experiencing high problem diversity`
   - Description: `More than 10 distinct problems detected today, indicating potential system instability.`
   - Runbook URL: `https://github.com/leok974/mcp-devdiag/blob/main/deployments/OPERATIONS.md#5-high-diversity-severity-warning`
   
   **Labels:**
   - `severity`: `warning`
   - `team`: `devdiag`
   - `component`: `stability`

---

5. **Alert 4: TTR Regression (WARNING)**
   
   **Query A (PostgreSQL):**
   ```sql
   SELECT
     NOW() AS time,
     PERCENTILE_DISC(0.5) WITHIN GROUP (
       ORDER BY EXTRACT(EPOCH FROM ttr_days)/86400
     ) AS value
   FROM devdiag.v_ttr_days
   WHERE first_seen_day >= CURRENT_DATE - INTERVAL '7 days';
   ```
   - Datasource: `DevDiag Postgres`
   
   **Condition B (Expression):**
   - Type: Classic condition
   - WHEN: `last()` of `A`
   - IS ABOVE: `2`
   
   **Alert Details:**
   - Alert name: `DevDiag: Median TTR >2 days (7d)`
   - Folder: `DevDiag Alerts`
   - Evaluation group: `devdiag-learning`
   - Evaluation interval: `30m`
   - Pending period: `30m`
   
   **Annotations:**
   - Summary: `Problem resolution time has degraded`
   - Description: `Median time-to-resolution over the last 7 days exceeds 2 days, indicating slower problem resolution.`
   - Runbook URL: `https://github.com/leok974/mcp-devdiag/blob/main/deployments/OPERATIONS.md#3-ttr-regression-severity-warning`
   
   **Labels:**
   - `severity`: `warning`
   - `team`: `devdiag`
   - `component`: `learning`

---

6. **Alert 5: Top Problem Dominates (WARNING)**
   
   **Query A (PostgreSQL):**
   ```sql
   SELECT
     NOW() AS time,
     (max_cnt::float / NULLIF(total_cnt,0)) AS value
   FROM (
     SELECT MAX(cnt) AS max_cnt, SUM(cnt) AS total_cnt
     FROM (
       SELECT problem_code, SUM(runs) AS cnt
       FROM devdiag.v_problem_counts
       WHERE day >= NOW() - INTERVAL '7 days'
       GROUP BY problem_code
     ) s
   ) s2;
   ```
   - Datasource: `DevDiag Postgres`
   
   **Condition B (Expression):**
   - Type: Classic condition
   - WHEN: `last()` of `A`
   - IS ABOVE: `0.20` (20%)
   
   **Alert Details:**
   - Alert name: `DevDiag: Top problem >20% of runs (7d)`
   - Folder: `DevDiag Alerts`
   - Evaluation group: `devdiag-health`
   - Evaluation interval: `10m`
   - Pending period: `10m`
   
   **Annotations:**
   - Summary: `Single problem affecting majority of runs`
   - Description: `One problem code accounts for more than 20% of all diagnostic runs in the last 7 days, indicating a systemic issue.`
   - Runbook URL: `https://github.com/leok974/mcp-devdiag/blob/main/deployments/OPERATIONS.md#1-top-problem-dominates-severity-warning`
   
   **Labels:**
   - `severity`: `warning`
   - `team`: `devdiag`
   - `component`: `diagnostics`

---

### Method 2: Simplified Alert Setup (Quick Start)

If you need alerts immediately but want minimal setup, create one critical alert:

**"Pipeline Down" Alert:**

1. Navigate to Alerting → New alert rule
2. **Query:**
   ```sql
   SELECT ts AS time, 1 AS value
   FROM devdiag.diag_run
   WHERE ts >= NOW() - INTERVAL '2 hours'
   ORDER BY ts DESC LIMIT 1;
   ```
3. **Condition:** `WHEN last() of A IS no value`
4. **Evaluation:** Every 5 minutes, pending for 5 minutes
5. **Labels:** `severity=critical`
6. **NoData state:** `Alerting` (critical setting!)

This single alert will catch the most critical failure mode (pipeline stopped).

---

## Notification Setup

Once alerts are created, configure notification channels:

1. **Grafana UI → Alerting → Contact points**
2. Create contact point (e.g., email, Slack, PagerDuty)
3. **Alerting → Notification policies**
4. Add policy:
   - **Matcher:** `severity = critical`
   - **Contact point:** Your critical notification channel
   - **Group by:** `alertname`
   - **Repeat interval:** `4h` (re-notify every 4 hours if still firing)

---

## Testing Alerts

### Test "Runs Stalled" Alert

1. Stop the MCP server (close VS Code or kill process)
2. Wait 2 hours + 5 minutes (evaluation + pending)
3. Check Grafana → Alerting → Alert rules
4. Alert should transition from `Normal` → `Pending` → `Firing`

**Faster Test (Modify Alert):**
- Change `2 hours` to `5 minutes` in query
- Change pending period to `1m`
- Wait 6 minutes
- Reset to production values after test

### Test "Confidence Drop" Alert

Inject low-confidence data:

```sql
-- Simulate failed fixes (temporary test data)
INSERT INTO devdiag.diag_run (tenant_id, session_id, ts, problem_code, fix_suggestion, resolution, error_msg)
SELECT 
  'test-tenant',
  gen_random_uuid()::text,
  NOW() - (i || ' seconds')::interval,
  'TEST_PROBLEM',
  'Test fix suggestion',
  'manual',
  'Test error'
FROM generate_series(1, 50) i;

-- Wait 30 minutes for alert to evaluate
-- Alert should fire as confidence will be low

-- Clean up test data
DELETE FROM devdiag.diag_run WHERE tenant_id = 'test-tenant';
```

---

## Troubleshooting

### Alert Not Firing

**Check:**
1. **Query returns data:**
   - Go to Explore → Select DevDiag Postgres datasource
   - Paste alert query
   - Run → Should return numeric value

2. **Datasource UID is correct:**
   - Alerts → Edit alert → Query A
   - Datasource should show "DevDiag Postgres" (not missing/red)

3. **Evaluation is running:**
   - Alerts → Alert rule → State history
   - Should see regular evaluations every X minutes
   - If no history, check Grafana logs

4. **Threshold is appropriate:**
   - View query result in Explore
   - Compare to alert threshold
   - Adjust threshold if needed

### Alert Shows "Error"

**Common Causes:**
- **Query error:** SQL syntax issue or table doesn't exist
- **No data:** View is empty or query returns NULL
- **Datasource down:** PostgreSQL connection failed

**Fix:**
1. Test query in Explore view
2. Check datasource configuration (Settings → Data sources)
3. Review Grafana logs: `docker logs grafana` or `/var/log/grafana/grafana.log`

---

## Future Work

**Automated Import (v0.3.1):**
- Fix alert JSON structure for provisioning API compatibility
- Update `import-alerts.ps1` to use correct payload format
- Add CI tests to validate alert definitions

**Additional Alerts:**
- Database disk space usage >80%
- Backup failures (no backup in 7+ days)
- View refresh failures (stale materialized views)
- Anomaly detection (sudden spike in problem diversity)

---

## Reference

- **Grafana Alerting Docs:** https://grafana.com/docs/grafana/latest/alerting/
- **PostgreSQL Datasource:** https://grafana.com/docs/grafana/latest/datasources/postgres/
- **Alert Provisioning API:** https://grafana.com/docs/grafana/latest/developers/http_api/alerting_provisioning/
- **Operations Runbook:** `deployments/OPERATIONS.md`
- **Health Checks:** `deployments/health-checks.sql`
