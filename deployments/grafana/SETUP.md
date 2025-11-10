# Grafana Integration Setup Guide

Complete guide for connecting Grafana to DevDiag PostgreSQL analytics warehouse.

---

## Quick Start (5 minutes)

### 1. Configure Grafana Datasource

**Option A: Auto-provision (recommended)**

Copy the datasource config:
```bash
cp deployments/grafana/provisioning/datasources/postgres-devdiag.yaml \
   /etc/grafana/provisioning/datasources/
```

Set environment variables:
```bash
export DEVDIAG_PG_HOST=localhost
export DEVDIAG_PG_USER=grafana
export DEVDIAG_PG_DB=devdiag
export DEVDIAG_PG_PASS='StrongGrafanaPass!'
```

Restart Grafana:
```bash
sudo systemctl restart grafana-server
# or for Docker:
docker restart grafana
```

**Option B: Manual UI setup**

1. Open Grafana → **Configuration** → **Data sources**
2. Click **Add data source**
3. Select **PostgreSQL**
4. Configure:
   - **Host:** `localhost:5432`
   - **Database:** `devdiag`
   - **User:** `grafana` (read-only user)
   - **Password:** `StrongGrafanaPass!`
   - **TLS/SSL Mode:** `disable` (use `require` for production)
   - **PostgreSQL Version:** `16.0+`
5. Click **Save & Test**

### 2. Import Dashboard

1. Navigate to **Dashboards** → **New** → **Import**
2. Upload: `deployments/grafana/dashboards/devdiag-analytics.json`
3. Select datasource: **DevDiag Postgres**
4. Click **Import**

You now have 8 panels:
- **Diagnostic Runs (24h)** - Total runs in last day
- **Distinct Problems (Today)** - Unique problem count
- **Problems Over Time** - Stacked time series
- **Top Problem Codes (7d)** - Horizontal bar chart
- **Fixes That Work** - Success table with confidence scores
- **Time to Remediation** - TTR bar gauge
- **Environment Diversity** - Unique environments per problem
- **Recent Activity** - Last 50 diagnostic runs

### 3. Set Up Alerts (15 minutes)

See [`ALERT_QUERIES.md`](./ALERT_QUERIES.md) for 5 pre-built alerts:
1. Top problem dominates (>20% of runs)
2. Diagnostic runs stalled (no data for 2h)
3. Median TTR regression (>2 days)
4. High problem diversity (>10 distinct problems)
5. Fix confidence dropping (<70%)

---

## Security: Read-Only Database User

Create a dedicated Grafana user with SELECT-only privileges:

```sql
-- Run in PostgreSQL
CREATE ROLE grafana LOGIN PASSWORD 'StrongGrafanaPass!';
GRANT USAGE ON SCHEMA devdiag TO grafana;
GRANT SELECT ON ALL TABLES IN SCHEMA devdiag TO grafana;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA devdiag TO grafana;
ALTER DEFAULT PRIVILEGES IN SCHEMA devdiag GRANT SELECT ON TABLES TO grafana;
```

Or use the provided script:
```bash
psql -U devdiag -d devdiag -f deployments/create-grafana-user.sql
```

Update datasource to use `user=grafana` instead of `user=devdiag`.

---

## Performance Optimization

### Recommended Indexes

Already created if you ran `postgres-init.sql`, but verify:

```sql
-- Time-based filtering (already exists)
CREATE INDEX IF NOT EXISTS idx_diag_run_ts ON devdiag.diag_run (ts);
CREATE INDEX IF NOT EXISTS idx_diag_run_tenant_ts ON devdiag.diag_run (tenant, ts);

-- JSONB problem queries (NEW - for Grafana filters)
CREATE INDEX IF NOT EXISTS idx_diag_run_problems_gin 
  ON devdiag.diag_run USING gin (problems jsonb_path_ops);
```

Run the GIN index manually:
```bash
docker exec -it devdiag-postgres psql -U devdiag -d devdiag \
  -c "CREATE INDEX IF NOT EXISTS idx_diag_run_problems_gin ON devdiag.diag_run USING gin (problems jsonb_path_ops);"
```

### Query Performance Tips

1. **Use time filters:** All panels should have `WHERE ts >= $__timeFrom()`
2. **Limit rows:** Add `LIMIT` to large result sets
3. **Aggregate early:** Use views (already optimized)
4. **Cache dashboards:** Set refresh interval to 5-15 minutes

---

## Data Retention & Maintenance

### Automated Cleanup (Daily Cron)

Run the retention script daily to keep 180 days of data:

**Linux/macOS:**
```bash
# Add to crontab: 0 2 * * *
crontab -e
# Add line:
0 2 * * * /path/to/deployments/retention-cleanup.sh
```

**Windows (Task Scheduler):**
- Use `deployments/retention-cleanup.sql` with pgAgent
- Or run manually weekly

### Manual Cleanup

```bash
psql -U devdiag -d devdiag -f deployments/retention-cleanup.sql
```

### Vacuum & Analyze

Run after cleanup to reclaim space:
```sql
VACUUM (ANALYZE) devdiag.diag_run;
VACUUM (ANALYZE) devdiag.fix_outcome;
```

---

## Backup & Restore

### Create Backup

**Using Docker container:**
```bash
# Linux/macOS
./deployments/backup.sh

# Windows PowerShell
.\deployments\backup.ps1
```

**Manual backup:**
```bash
docker exec devdiag-postgres pg_dump -U devdiag -d devdiag -Fc > devdiag_$(date +%F).dump
```

Backups are stored in compressed custom format (`.dump`).

### Restore from Backup

```bash
# Linux/macOS
./deployments/restore.sh /path/to/backup.dump

# Manual
docker exec -i devdiag-postgres pg_restore -U devdiag -d devdiag -c -1 < backup.dump
```

**⚠️ Warning:** Restore will overwrite current data!

### Automated Backups

**Cron job (daily at 3 AM):**
```bash
0 3 * * * /path/to/deployments/backup.sh
```

**Retention:** Backups older than 30 days are auto-deleted.

---

## Advanced Grafana Features

### Variable Templates

The dashboard includes a **$tenant** variable for filtering:
- Dropdown populated from `SELECT DISTINCT tenant FROM devdiag.diag_run`
- All panels respect `WHERE tenant = '$tenant'`
- Use `$__all` to show all tenants

### Annotations

Add deployment markers:
```sql
SELECT ts AS time, 'Deployment: ' || preset AS text
FROM devdiag.diag_run
WHERE preset = 'prod-deploy';
```

### Custom Panels

Example: Top 5 problems by environment:
```sql
SELECT 
  problem_code,
  env_fp,
  COUNT(*) AS occurrences
FROM devdiag.diag_run, jsonb_array_elements_text(problems) AS problem_code
WHERE ts >= $__timeFrom() AND ts <= $__timeTo()
GROUP BY 1, 2
ORDER BY occurrences DESC
LIMIT 5;
```

---

## Troubleshooting

### Connection Failed

**Error:** "Unable to connect to PostgreSQL"

**Solutions:**
1. Check PostgreSQL is running: `docker ps | grep devdiag-postgres`
2. Verify credentials: `psql "postgresql://grafana:PASSWORD@localhost:5432/devdiag"`
3. Check firewall: Port 5432 must be open
4. Verify SSL mode matches (disable for localhost)

### Dashboard Panels Empty

**Error:** "No data" on all panels

**Solutions:**
1. Check data exists: `SELECT COUNT(*) FROM devdiag.diag_run;`
2. Verify time range (default: last 7 days)
3. Check tenant filter (set to "All")
4. Review panel queries for errors

### Slow Queries

**Error:** Panels take >10s to load

**Solutions:**
1. Add indexes: `\di devdiag.*` (should see 9 indexes)
2. Reduce time range: Change from 30d to 7d
3. Add query limits: `LIMIT 100`
4. Check VACUUM stats: `SELECT * FROM pg_stat_user_tables WHERE schemaname = 'devdiag';`

### Permission Denied

**Error:** "permission denied for schema devdiag"

**Solutions:**
1. Re-run: `psql -f deployments/create-grafana-user.sql`
2. Verify grants: `\z devdiag.*`
3. Check user: `\du grafana`

---

## Production Deployment

### Use Managed PostgreSQL

For production, use:
- **AWS RDS** (PostgreSQL 16)
- **Google Cloud SQL**
- **Azure Database for PostgreSQL**
- **DigitalOcean Managed Database**

Update connection string in datasource:
```yaml
url: ${DEVDIAG_PG_HOST}:5432  # e.g., rds-instance.amazonaws.com
jsonData:
  sslmode: require            # Enable SSL for production
```

### Enable SSL/TLS

1. Download CA certificate from cloud provider
2. Configure Grafana datasource:
   - **SSL Mode:** `require` or `verify-full`
   - **TLS/SSL Root Certificate:** Upload CA cert
3. Test connection

### Multi-Tenant Setup

For multiple environments (dev/staging/prod):

1. Create separate databases or schemas
2. Add multiple datasources in Grafana
3. Use dashboard variables to switch environments

### High Availability

- **Connection pooling:** Use PgBouncer
- **Read replicas:** Point Grafana to replica for analytics
- **Failover:** Configure multiple hosts in connection string

---

## Next Steps

1. ✅ **Test queries** - Run validation queries from dashboard
2. 🔔 **Set up alerts** - Configure notification channels
3. 📊 **Customize dashboards** - Add panels for your use cases
4. 🔄 **Automate backups** - Schedule daily backups
5. 📈 **Monitor performance** - Track query times in Grafana

For more details, see:
- [ANALYTICS_WAREHOUSE.md](../../docs/ANALYTICS_WAREHOUSE.md) - PostgreSQL setup
- [ALERT_QUERIES.md](./ALERT_QUERIES.md) - Pre-built alerts
- [TABLEAU_DASHBOARDS.md](../../docs/TABLEAU_DASHBOARDS.md) - Tableau integration

---

## Support

- **Issues:** https://github.com/leok974/mcp-devdiag/issues
- **Discussions:** https://github.com/leok974/mcp-devdiag/discussions
- **Docs:** https://github.com/leok974/mcp-devdiag/tree/main/docs
