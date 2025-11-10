# DevDiag Operations Runbook

**Version:** 0.3.0  
**Last Updated:** 2024  
**Status:** Production-ready

---

## Table of Contents

1. [Daily Operations](#daily-operations)
2. [Alert Response](#alert-response)
3. [Health Monitoring](#health-monitoring)
4. [Maintenance Tasks](#maintenance-tasks)
5. [Troubleshooting](#troubleshooting)
6. [Disaster Recovery](#disaster-recovery)

---

## Daily Operations

### Morning Health Check (5 minutes)

Run the automated health checks:

```bash
psql "postgresql://${DEVDIAG_PG_USER}:${DEVDIAG_PG_PASS}@${DEVDIAG_PG_HOST}/${DEVDIAG_PG_DB}" -f deployments/health-checks.sql
```

**Expected Results:**
- ✅ New rows today: > 0
- ✅ Data freshness: < 2 hours since last run
- ✅ Fix confidence (30d avg): >= 0.70
- ✅ Views present: 6/6
- ✅ Indexes present: 9/9
- ✅ Retention: 170-190 days

**Red Flags:**
- 🚨 Zero new rows → Check if MCP server is running
- 🚨 Stale data (>6h) → Pipeline is down
- 🚨 Missing views → Schema migration failed
- ⚠️  High diversity (>10 problems/day) → System instability

---

## Alert Response

### 1. Top Problem Dominates (Severity: Warning)

**Trigger:** Single problem affects >20% of diagnostic runs (7-day window)

**Immediate Actions:**
1. Identify the dominant problem:
   ```sql
   SELECT problem_code, cnt, 
          (cnt::float / SUM(cnt) OVER ()) AS pct
   FROM devdiag.v_problem_counts 
   WHERE day >= CURRENT_DATE - 7
   ORDER BY cnt DESC LIMIT 1;
   ```

2. Check if fix exists:
   ```sql
   SELECT problem_code, fix_suggestion, avg_confidence
   FROM devdiag.v_fix_success
   WHERE problem_code = '<PROBLEM_CODE>';
   ```

3. Review recent occurrences:
   ```sql
   SELECT tenant_id, environment, ts, resolution
   FROM devdiag.diag_run
   WHERE problem_code = '<PROBLEM_CODE>'
     AND ts >= NOW() - INTERVAL '24 hours'
   ORDER BY ts DESC LIMIT 10;
   ```

**Root Cause Analysis:**
- Is this a new widespread issue (systemic bug)?
- Is the learned fix ineffective (low confidence)?
- Has the environment changed (new deployment)?

**Resolution:**
- If fix exists with >0.80 confidence → Communicate fix to users
- If no fix or low confidence → Escalate to engineering team
- If systemic → Consider temporary documentation/workaround

**Close Alert:**
Alert auto-resolves when dominance drops below 20% for 10 minutes.

---

### 2. Runs Stalled (Severity: Critical)

**Trigger:** No diagnostic runs in last 2 hours

**Immediate Actions:**
1. Check MCP server status:
   ```bash
   # Check if server is running
   ps aux | grep mcp-devdiag
   
   # Check VS Code is using MCP server
   # In VS Code: Ctrl+Shift+P → "MCP: Show Logs"
   ```

2. Check database connectivity:
   ```bash
   psql "postgresql://${DEVDIAG_PG_USER}:${DEVDIAG_PG_PASS}@${DEVDIAG_PG_HOST}/${DEVDIAG_PG_DB}" -c "\conninfo"
   ```

3. Review recent errors:
   ```sql
   SELECT ts, problem_code, error_msg
   FROM devdiag.diag_run
   WHERE ts >= NOW() - INTERVAL '6 hours'
     AND error_msg IS NOT NULL
   ORDER BY ts DESC LIMIT 20;
   ```

**Root Cause Analysis:**
- Is PostgreSQL running? (`systemctl status postgresql` or `pg_isready`)
- Are credentials valid? (Check connection string)
- Is MCP server installed? (`pip list | grep mcp-devdiag`)
- Is VS Code configured? (Check `.vscode/mcp.json`)

**Resolution:**
- Restart MCP server if process crashed
- Restart PostgreSQL if database is down
- Fix credentials if authentication failed
- Reinstall server if package is corrupted

**Close Alert:**
Alert auto-resolves when new run is recorded within 2 hours.

---

### 3. TTR Regression (Severity: Warning)

**Trigger:** Median time-to-resolution >2 days (7-day window)

**Immediate Actions:**
1. Calculate current TTR distribution:
   ```sql
   SELECT 
     PERCENTILE_DISC(0.25) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM ttr_days)/86400) AS p25,
     PERCENTILE_DISC(0.50) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM ttr_days)/86400) AS p50,
     PERCENTILE_DISC(0.75) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM ttr_days)/86400) AS p75,
     AVG(EXTRACT(EPOCH FROM ttr_days)/86400) AS avg_ttr_days
   FROM devdiag.v_ttr_days
   WHERE first_seen_day >= CURRENT_DATE - INTERVAL '7 days';
   ```

2. Identify slow-to-resolve problems:
   ```sql
   SELECT problem_code, 
          AVG(EXTRACT(EPOCH FROM ttr_days)/86400) AS avg_ttr_days,
          COUNT(*) AS occurrences
   FROM devdiag.v_ttr_days
   WHERE first_seen_day >= CURRENT_DATE - INTERVAL '7 days'
   GROUP BY problem_code
   HAVING AVG(EXTRACT(EPOCH FROM ttr_days)/86400) > 2
   ORDER BY avg_ttr_days DESC;
   ```

3. Check if new complex problems emerged:
   ```sql
   SELECT problem_code, MIN(first_seen_day) AS first_seen
   FROM devdiag.v_ttr_days
   WHERE first_seen_day >= CURRENT_DATE - INTERVAL '7 days'
   GROUP BY problem_code
   ORDER BY first_seen DESC;
   ```

**Root Cause Analysis:**
- Are new, harder problems appearing? (Check first_seen dates)
- Are fixes less effective? (Check avg_confidence in v_fix_success)
- Is manual intervention required? (Check resolution='manual')

**Resolution:**
- Improve fix suggestions for slow problems
- Add documentation for manual intervention steps
- Consider proactive monitoring for recurring issues

**Close Alert:**
Alert auto-resolves when median TTR drops below 2 days for 30 minutes.

---

### 4. Confidence Drop (Severity: Warning)

**Trigger:** Average fix confidence <70% (7-day window)

**Immediate Actions:**
1. Check current confidence distribution:
   ```sql
   SELECT 
     AVG(avg_confidence) AS avg_conf,
     PERCENTILE_DISC(0.50) WITHIN GROUP (ORDER BY avg_confidence) AS median_conf,
     COUNT(*) AS problems_with_fixes
   FROM devdiag.v_fix_success
   WHERE last_success >= NOW() - INTERVAL '7 days';
   ```

2. Identify low-confidence fixes:
   ```sql
   SELECT problem_code, fix_suggestion, 
          avg_confidence, successful_fixes, total_attempts
   FROM devdiag.v_fix_success
   WHERE avg_confidence < 0.70
     AND last_success >= NOW() - INTERVAL '7 days'
   ORDER BY total_attempts DESC;
   ```

3. Review recent fix outcomes:
   ```sql
   SELECT problem_code, fix_suggestion, resolution,
          COUNT(*) AS occurrences
   FROM devdiag.diag_run
   WHERE fix_suggestion IS NOT NULL
     AND ts >= NOW() - INTERVAL '7 days'
   GROUP BY problem_code, fix_suggestion, resolution
   ORDER BY occurrences DESC;
   ```

**Root Cause Analysis:**
- Are users rejecting valid fixes? (Check resolution='manual')
- Are fix suggestions outdated? (Environment changes)
- Is learning logic miscalculating confidence? (Bug in analyzer.py)

**Resolution:**
- Review fix logic in `mcp_devdiag/analyzer.py`
- Update fix suggestions based on recent resolutions
- Retrain learning model with corrected data

**Close Alert:**
Alert auto-resolves when confidence returns above 70% for 30 minutes.

---

### 5. High Diversity (Severity: Warning)

**Trigger:** >10 distinct problems in a single day

**Immediate Actions:**
1. List today's unique problems:
   ```sql
   SELECT problem_code, COUNT(*) AS occurrences
   FROM devdiag.v_problem_counts
   WHERE day = CURRENT_DATE
   GROUP BY problem_code
   ORDER BY occurrences DESC;
   ```

2. Check if problems are related:
   ```sql
   SELECT DISTINCT environment, COUNT(DISTINCT problem_code) AS problem_variety
   FROM devdiag.diag_run
   WHERE ts::date = CURRENT_DATE
   GROUP BY environment
   ORDER BY problem_variety DESC;
   ```

3. Review tenant distribution:
   ```sql
   SELECT tenant_id, COUNT(DISTINCT problem_code) AS unique_problems
   FROM devdiag.diag_run
   WHERE ts::date = CURRENT_DATE
   GROUP BY tenant_id
   HAVING COUNT(DISTINCT problem_code) > 3
   ORDER BY unique_problems DESC;
   ```

**Root Cause Analysis:**
- Is this widespread system instability? (Many environments affected)
- Is this isolated to specific tenant? (Tenant-level issue)
- Did a recent deployment introduce regressions? (Check deployment times)

**Resolution:**
- If systemic → Escalate to engineering (possible rollback)
- If isolated → Investigate tenant-specific configuration
- If deployment-related → Consider rollback or hotfix

**Close Alert:**
Alert auto-resolves when daily diversity drops below 10 for 15 minutes.

---

## Health Monitoring

### Automated Daily Checks

**Schedule:** Run every 24 hours (recommended: 8am UTC)

**Cron Job Setup:**
```bash
# Add to crontab -e
0 8 * * * psql "postgresql://${DEVDIAG_PG_USER}:${DEVDIAG_PG_PASS}@${DEVDIAG_PG_HOST}/${DEVDIAG_PG_DB}" -f /path/to/deployments/health-checks.sql >> /var/log/devdiag/health-checks.log 2>&1
```

**What Gets Checked:**
1. **Data freshness** - Stale data indicates pipeline failure
2. **Schema integrity** - Missing views/indexes indicate migration issues
3. **Data quality** - Low confidence indicates learning degradation
4. **Retention policy** - Excessive retention indicates cleanup failure
5. **Problem diversity** - High diversity indicates system instability

**Alert Thresholds:**
- **Critical:** Stale data >6h, missing views, zero new rows
- **Warning:** Low confidence <0.70, retention >190 days, high diversity >10

---

### Manual Weekly Review (15 minutes)

**Every Monday, review:**

1. **Learning Effectiveness:**
   ```sql
   SELECT 
     COUNT(DISTINCT problem_code) AS problems_with_fixes,
     AVG(avg_confidence) AS overall_confidence,
     SUM(successful_fixes) AS total_successes
   FROM devdiag.v_fix_success;
   ```

2. **Top Problems (Last 7 Days):**
   ```sql
   SELECT problem_code, SUM(cnt) AS total_occurrences
   FROM devdiag.v_problem_counts
   WHERE day >= CURRENT_DATE - 7
   GROUP BY problem_code
   ORDER BY total_occurrences DESC LIMIT 10;
   ```

3. **Environment Diversity:**
   ```sql
   SELECT * FROM devdiag.v_env_diversity
   WHERE first_seen >= NOW() - INTERVAL '7 days'
   ORDER BY environment_combos DESC LIMIT 10;
   ```

4. **Recent Activity Summary:**
   ```sql
   SELECT * FROM devdiag.v_recent_activity LIMIT 50;
   ```

---

## Maintenance Tasks

### Weekly Tasks

#### 1. Database Backup (Every Sunday, 2am)

Run automated backup:
```bash
./scripts/postgres/backup.sh
```

**What it does:**
- Creates compressed dump of `devdiag` database
- Saves to `backups/devdiag-YYYY-MM-DD.sql.gz`
- Removes backups older than 30 days

**Verification:**
```bash
ls -lh backups/devdiag-*.sql.gz
# Should see at least 4 backups (last 4 weeks)
```

**Recovery Test (Monthly):**
```bash
# Restore to test database
gunzip -c backups/devdiag-2024-01-14.sql.gz | \
  psql "postgresql://${DEVDIAG_PG_USER}:${DEVDIAG_PG_PASS}@${DEVDIAG_PG_HOST}/devdiag_test"
```

---

#### 2. Retention Cleanup (Every Sunday, 3am)

Run retention policy:
```bash
psql "postgresql://${DEVDIAG_PG_USER}:${DEVDIAG_PG_PASS}@${DEVDIAG_PG_HOST}/${DEVDIAG_PG_DB}" -f scripts/postgres/retention-cleanup.sql
```

**What it does:**
- Deletes rows older than 180 days from `devdiag.diag_run`
- Preserves first/last occurrence of each problem
- Runs VACUUM ANALYZE to reclaim space

**Expected Output:**
```
DELETE xxxxx  -- Number of rows deleted
VACUUM
```

**Verification:**
```sql
SELECT 
  MIN(ts) AS oldest_data,
  MAX(ts) AS newest_data,
  EXTRACT(DAY FROM (NOW() - MIN(ts))) AS retention_days
FROM devdiag.diag_run;
-- retention_days should be ~170-190 days
```

---

### Monthly Tasks

#### 1. Grafana Token Rotation (First Monday)

**Steps:**
1. Generate new token in Grafana UI:
   - Settings → Service Accounts → Create service account
   - Add role: Editor
   - Generate token → Copy token

2. Update GitHub Secrets:
   - Repository → Settings → Secrets → Actions
   - Update `GRAFANA_API_KEY` with new token

3. Test new token:
   ```bash
   export GRAFANA_API_KEY="new-token"
   curl -H "Authorization: Bearer $GRAFANA_API_KEY" \
     "${GRAFANA_URL}/api/org"
   # Should return: {"id":1,"name":"Main Org."}
   ```

4. Revoke old token in Grafana UI

---

#### 2. Database Performance Review

**Check table sizes:**
```sql
SELECT 
  schemaname || '.' || tablename AS table_name,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
  pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
  pg_size_pretty(pg_indexes_size(schemaname||'.'||tablename)) AS indexes_size
FROM pg_tables
WHERE schemaname = 'devdiag'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

**Check slow queries (if enabled):**
```sql
SELECT 
  query,
  calls,
  total_exec_time,
  mean_exec_time,
  max_exec_time
FROM pg_stat_statements
WHERE query LIKE '%devdiag%'
ORDER BY mean_exec_time DESC LIMIT 10;
```

**Index usage:**
```sql
SELECT 
  schemaname || '.' || tablename AS table_name,
  indexname,
  idx_scan,
  idx_tup_read,
  idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'devdiag'
ORDER BY idx_scan ASC;
-- Low idx_scan = unused index (consider dropping)
```

---

### Quarterly Tasks

#### 1. Capacity Planning Review

**Analyze growth trends:**
```sql
-- Monthly row growth
SELECT 
  DATE_TRUNC('month', ts) AS month,
  COUNT(*) AS rows_added
FROM devdiag.diag_run
GROUP BY month
ORDER BY month DESC LIMIT 12;

-- Current database size
SELECT 
  pg_size_pretty(pg_database_size('devdiag')) AS db_size;

-- Extrapolate 12-month capacity
-- Formula: (current_size / retention_days) * 365
```

**Thresholds:**
- **Warning:** Database >5GB (consider archiving)
- **Critical:** Database >10GB (investigate data explosion)

---

#### 2. Disaster Recovery Drill

**Full recovery test:**

1. **Backup current database:**
   ```bash
   ./scripts/postgres/backup.sh
   ```

2. **Simulate disaster (DROP DATABASE):**
   ```sql
   -- ⚠️ ONLY ON TEST SYSTEM
   DROP DATABASE devdiag;
   CREATE DATABASE devdiag;
   ```

3. **Restore from backup:**
   ```bash
   gunzip -c backups/devdiag-YYYY-MM-DD.sql.gz | \
     psql "postgresql://${DEVDIAG_PG_USER}:${DEVDIAG_PG_PASS}@${DEVDIAG_PG_HOST}/devdiag"
   ```

4. **Verify data integrity:**
   ```sql
   SELECT COUNT(*) FROM devdiag.diag_run;
   SELECT * FROM devdiag.v_fix_success LIMIT 5;
   ```

5. **Re-import Grafana dashboards:**
   ```bash
   ./scripts/grafana/import-datasource.sh
   ./scripts/grafana/import-dashboard.sh
   ./scripts/grafana/import-alerts.sh
   ```

**Document:**
- Time to restore (target: <30 minutes)
- Any data loss (should be 0 rows if backup is recent)
- Issues encountered

---

## Troubleshooting

### Issue: Grafana Dashboard Shows "No Data"

**Symptoms:**
- Dashboard panels empty
- Query inspector shows "no data points"

**Diagnosis:**
1. Check datasource connection:
   ```bash
   curl -H "Authorization: Bearer $GRAFANA_API_KEY" \
     "${GRAFANA_URL}/api/datasources/uid/devdiag-postgres"
   ```

2. Test raw query in Grafana Explore:
   ```sql
   SELECT COUNT(*) FROM devdiag.diag_run WHERE ts >= NOW() - INTERVAL '7 days';
   ```

**Fixes:**
- **Datasource not found:** Re-import datasource (`./scripts/grafana/import-datasource.sh`)
- **Authentication failed:** Check `grafana` user password in PostgreSQL
- **Empty table:** Verify MCP server is running and logging data
- **Time range issue:** Adjust dashboard time picker (top-right)

---

### Issue: Alerts Not Firing

**Symptoms:**
- Expected alert not triggered
- Alert shows "Normal" state in Grafana

**Diagnosis:**
1. Check alert exists:
   ```bash
   curl -H "Authorization: Bearer $GRAFANA_API_KEY" \
     "${GRAFANA_URL}/api/v1/provisioning/alert-rules" | jq .
   ```

2. Check alert evaluation history:
   - Grafana → Alerting → Alert rules → [alert name] → State history

3. Test alert query manually:
   ```sql
   -- Example: runs-stalled alert
   SELECT EXTRACT(EPOCH FROM (NOW() - MAX(ts))) AS seconds_since
   FROM devdiag.diag_run;
   -- If > 7200, alert should fire
   ```

**Fixes:**
- **Alert not imported:** Run `./scripts/grafana/import-alerts.sh`
- **Query returns no data:** Check datasource UID in alert JSON
- **Evaluation interval too long:** Alerts evaluate every 5-30 minutes (by design)
- **"For" duration not met:** Alert must exceed threshold for configured duration (5m-30m)

---

### Issue: High Database CPU Usage

**Symptoms:**
- PostgreSQL using >50% CPU
- Slow query performance

**Diagnosis:**
1. Check active queries:
   ```sql
   SELECT pid, usename, state, query
   FROM pg_stat_activity
   WHERE state = 'active' AND query NOT LIKE '%pg_stat_activity%';
   ```

2. Identify slow queries:
   ```sql
   SELECT pid, now() - query_start AS duration, query
   FROM pg_stat_activity
   WHERE state = 'active' AND query NOT LIKE '%pg_stat_activity%'
   ORDER BY duration DESC;
   ```

3. Kill long-running query (if stuck):
   ```sql
   SELECT pg_terminate_backend(12345);  -- Replace 12345 with pid
   ```

**Fixes:**
- **Missing indexes:** Run index health check (deployments/health-checks.sql, Check 8)
- **Large retention window:** Run retention cleanup (scripts/postgres/retention-cleanup.sql)
- **Inefficient query:** Review query in Grafana dashboard, optimize SQL

---

### Issue: MCP Server Not Responding

**Symptoms:**
- VS Code shows "MCP server not responding"
- No new diagnostic runs logged

**Diagnosis:**
1. Check MCP server logs:
   - VS Code → Ctrl+Shift+P → "MCP: Show Logs"

2. Verify installation:
   ```bash
   pip show mcp-devdiag
   # Version: 0.3.0
   ```

3. Check VS Code configuration:
   ```json
   // .vscode/mcp.json
   {
     "mcpServers": {
       "devdiag": {
         "command": "python",
         "args": ["-m", "mcp_devdiag"],
         "env": {
           "DEVDIAG_PG_HOST": "localhost:5432",
           "DEVDIAG_PG_USER": "devdiag_writer",
           "DEVDIAG_PG_PASS": "...",
           "DEVDIAG_PG_DB": "devdiag"
         }
       }
     }
   }
   ```

**Fixes:**
- **Not installed:** `pip install mcp-devdiag`
- **Wrong version:** `pip install --upgrade mcp-devdiag`
- **Config missing:** Add `.vscode/mcp.json` with correct credentials
- **Restart required:** Reload VS Code window (Ctrl+Shift+P → "Developer: Reload Window")

---

## Disaster Recovery

### Scenario 1: Database Corruption

**Symptoms:**
- PostgreSQL errors: "invalid page header"
- Cannot query tables

**Recovery Steps:**

1. **Stop writes immediately:**
   - Stop MCP server (kill process or restart VS Code)

2. **Assess corruption extent:**
   ```sql
   -- Try to read recent data
   SELECT COUNT(*) FROM devdiag.diag_run WHERE ts >= NOW() - INTERVAL '7 days';
   ```

3. **Restore from backup:**
   ```bash
   # Create recovery database
   createdb devdiag_recovery
   
   # Restore latest backup
   gunzip -c backups/devdiag-$(date -d "yesterday" +%Y-%m-%d).sql.gz | \
     psql "postgresql://${DEVDIAG_PG_USER}:${DEVDIAG_PG_PASS}@${DEVDIAG_PG_HOST}/devdiag_recovery"
   
   # Verify recovery
   psql "postgresql://${DEVDIAG_PG_USER}:${DEVDIAG_PG_PASS}@${DEVDIAG_PG_HOST}/devdiag_recovery" \
     -c "SELECT MIN(ts), MAX(ts), COUNT(*) FROM devdiag.diag_run;"
   ```

4. **Switch to recovery database:**
   ```sql
   -- Rename databases
   ALTER DATABASE devdiag RENAME TO devdiag_corrupted;
   ALTER DATABASE devdiag_recovery RENAME TO devdiag;
   ```

5. **Update Grafana datasource:**
   ```bash
   # Should auto-reconnect, but force refresh:
   ./scripts/grafana/import-datasource.sh
   ```

6. **Resume operations:**
   - Restart MCP server (reload VS Code)
   - Verify new data is being logged

**Data Loss:**
- **Typical:** < 24 hours (if daily backups are running)
- **Worst case:** Up to 7 days (if weekly backups only)

---

### Scenario 2: Grafana Instance Lost

**Symptoms:**
- Grafana unreachable (connection refused)
- Dashboard URLs return 404

**Recovery Steps:**

1. **Reinstall Grafana:**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install -y grafana
   sudo systemctl start grafana-server
   sudo systemctl enable grafana-server
   ```

2. **Create service account:**
   - Grafana UI → Settings → Service Accounts → Create
   - Name: "DevDiag Automation"
   - Role: Editor
   - Generate token → Save to `GRAFANA_API_KEY`

3. **Re-import all resources:**
   ```bash
   export GRAFANA_URL="http://localhost:3000"
   export GRAFANA_API_KEY="your-new-token"
   
   ./scripts/grafana/import-datasource.sh
   ./scripts/grafana/import-dashboard.sh
   ./scripts/grafana/import-alerts.sh
   ```

4. **Verify dashboards:**
   - Open: http://localhost:3000/dashboards
   - Should see "DevDiag Analytics"
   - Check panels have data (not "No Data")

5. **Verify alerts:**
   - Open: http://localhost:3000/alerting/list
   - Should see 5 alerts in "devdiag-alerts" folder
   - Check alert state (should be "Normal" if system is healthy)

**Data Loss:**
- **None** (all configuration is in Git)

---

### Scenario 3: Complete Server Failure

**Symptoms:**
- Server hardware failure
- Operating system unbootable

**Recovery Steps:**

1. **Provision new server:**
   - Install PostgreSQL 16
   - Install Grafana
   - Install Python 3.12+

2. **Restore database from backup:**
   ```bash
   # Copy latest backup from old server (or backup storage)
   scp old-server:/path/to/backups/devdiag-YYYY-MM-DD.sql.gz /tmp/

   # Create database
   createdb devdiag
   
   # Restore data
   gunzip -c /tmp/devdiag-YYYY-MM-DD.sql.gz | \
     psql "postgresql://devdiag_writer:password@localhost:5432/devdiag"
   ```

3. **Recreate users:**
   ```sql
   -- Run: scripts/postgres/setup.sql
   CREATE USER devdiag_writer WITH PASSWORD '...';
   CREATE USER grafana WITH PASSWORD '...';
   GRANT INSERT, UPDATE, SELECT ON ALL TABLES IN SCHEMA devdiag TO devdiag_writer;
   GRANT SELECT ON ALL TABLES IN SCHEMA devdiag TO grafana;
   ```

4. **Import Grafana resources:**
   ```bash
   # Clone repository
   git clone https://github.com/your-org/mcp-devdiag.git
   cd mcp-devdiag
   
   # Import datasource, dashboard, alerts
   ./scripts/grafana/import-datasource.sh
   ./scripts/grafana/import-dashboard.sh
   ./scripts/grafana/import-alerts.sh
   ```

5. **Reinstall MCP server on client machines:**
   ```bash
   pip install mcp-devdiag
   ```

6. **Update connection strings:**
   - Update `DEVDIAG_PG_HOST` to new server IP in `.vscode/mcp.json`

**RTO (Recovery Time Objective):** < 2 hours  
**RPO (Recovery Point Objective):** < 24 hours (daily backups)

---

## Appendix: Contact Information

**Primary Contacts:**
- **DevOps Lead:** [Name], [Email], [Phone]
- **Database Admin:** [Name], [Email], [Phone]
- **Development Team:** [Slack Channel]

**Escalation Path:**
1. Check this runbook first
2. Review recent changes in Git history
3. Search Grafana alert history
4. Post in Slack #devdiag-ops
5. Escalate to DevOps Lead if critical

**External Resources:**
- Grafana Documentation: https://grafana.com/docs/grafana/latest/
- PostgreSQL Documentation: https://www.postgresql.org/docs/16/
- MCP Protocol Spec: https://github.com/modelcontextprotocol/specification

---

## Change Log

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2024-01-14 | 0.3.0 | Initial operations runbook | DevDiag Team |

---

**Document Status:** Living document  
**Next Review:** 2024-04-14 (Quarterly)
