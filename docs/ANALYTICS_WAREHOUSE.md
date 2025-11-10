# DevDiag Analytics Warehouse Setup

Complete guide for setting up PostgreSQL analytics warehouse and Tableau dashboards for DevDiag closed-loop learning.

## Overview

This setup enables:
- **Long-term storage** of diagnostic runs and fix outcomes
- **Analytics views** optimized for Tableau
- **Time-to-remediation** tracking
- **Fix effectiveness** metrics
- **Environment diversity** analysis

## 1. PostgreSQL Setup

### Option A: Docker (Recommended for Development)

```bash
# Set database password
export DEVDIAG_DB_PASS="your-strong-password-here"

# Start Postgres
docker compose -f deployments/postgres.devdiag.yml up -d

# Verify it's running
docker compose -f deployments/postgres.devdiag.yml ps
```

The database will be initialized automatically with the schema from `deployments/postgres-init.sql`.

### Option B: Managed Postgres (Production)

For production, use managed PostgreSQL from:
- **AWS RDS** (Postgres 16)
- **Google Cloud SQL** (Postgres 16)
- **Azure Database for PostgreSQL**
- **DigitalOcean Managed Databases**

Then run the init script manually:

```bash
psql -h your-host -U devdiag -d devdiag -f deployments/postgres-init.sql
```

## 2. Configure DevDiag

Update your production `devdiag.yaml`:

```yaml
learn:
  enabled: true
  # Use PostgreSQL instead of SQLite for production
  store: "postgresql+psycopg://devdiag:STRONGPASS@postgres:5432/devdiag"
  privacy:
    hash_targets: true
    keep_evidence_keys: ["csp", "xfo", "framework", "server", "routes"]
  retention_days: 180
  min_support: 2
  alpha: 0.6
  beta: 0.7
```

**Connection string format:**
```
postgresql+psycopg://[user]:[password]@[host]:[port]/[database]
```

## 3. Database Schema

### Tables

**`devdiag.diag_run`** - Diagnostic run records
- `id` (BIGSERIAL) - Primary key
- `ts` (TIMESTAMP) - Run timestamp
- `tenant` (TEXT) - Tenant identifier
- `target_hash` (TEXT) - Hashed target URL
- `env_fp` (TEXT) - Environment fingerprint
- `problems` (JSONB) - Array of problem codes
- `evidence` (JSONB) - Safe evidence data
- `preset` (TEXT) - Preset used (chat/embed/app/full)

**`devdiag.fix_outcome`** - Learned fix successes
- `id` (BIGSERIAL) - Primary key
- `ts` (TIMESTAMP) - Learning timestamp
- `tenant` (TEXT) - Tenant identifier
- `problem_code` (TEXT) - Problem code
- `fix_code` (TEXT) - Fix code that worked
- `confidence` (DOUBLE PRECISION) - Confidence score
- `support` (INTEGER) - Number of successes
- `env_fp` (TEXT) - Environment fingerprint
- `notes` (TEXT) - Optional notes

### Analytics Views

**`v_problem_counts`** - Daily problem occurrence by tenant
```sql
SELECT * FROM devdiag.v_problem_counts
WHERE day >= now() - interval '30 days';
```

**`v_fix_success`** - Aggregated fix success metrics
```sql
SELECT * FROM devdiag.v_fix_success
ORDER BY successes DESC;
```

**`v_ttr_days`** - Time-to-remediation estimates
```sql
SELECT problem_code, avg(ttr_days) AS avg_ttr
FROM devdiag.v_ttr_days
GROUP BY 1;
```

**`v_env_diversity`** - Environment diversity per problem
```sql
SELECT * FROM devdiag.v_env_diversity
WHERE unique_environments > 1;
```

**`v_fix_ranking`** - Ranked fixes per problem
```sql
SELECT * FROM devdiag.v_fix_ranking
WHERE rank <= 3;
```

## 4. SQLite to Postgres Sync (Hybrid Mode)

If you're using SQLite locally but want to sync to Postgres for analytics:

### Install Dependencies

```bash
pip install psycopg2-binary
```

### Run Sync Script

```bash
# Set environment variables
export SQLITE_PATH="devdiag.db"
export PG_DSN="postgresql://devdiag:password@localhost:5432/devdiag"

# Run sync
python scripts/sync_sqlite_to_pg.py
```

### Automated Sync (Cron)

```bash
# Add to crontab (runs every hour)
0 * * * * cd /path/to/mcp-devdiag && python scripts/sync_sqlite_to_pg.py >> /var/log/devdiag-sync.log 2>&1
```

### Automated Sync (GitHub Actions)

```yaml
# .github/workflows/sync-analytics.yml
name: Sync Analytics
on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours
  workflow_dispatch:

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install psycopg2-binary
      - run: python scripts/sync_sqlite_to_pg.py
        env:
          SQLITE_PATH: ${{ secrets.SQLITE_PATH }}
          PG_DSN: ${{ secrets.PG_DSN }}
```

## 5. Tableau Connection

### Tableau Desktop Setup

1. **Open Tableau Desktop**
2. **Connect** → **PostgreSQL**
3. **Enter connection details:**
   - Server: `localhost` (or your host)
   - Port: `5432`
   - Database: `devdiag`
   - Authentication: Username and Password
   - Username: `devdiag`
   - Password: `[DEVDIAG_DB_PASS]`

4. **Select schema:** `devdiag`
5. **Drag tables/views** to canvas:
   - `v_problem_counts` (for time series)
   - `v_fix_success` (for success metrics)
   - `v_ttr_days` (for remediation analysis)
   - `diag_run` (for raw data)
   - `fix_outcome` (for raw outcomes)

### Suggested Dashboards

#### Dashboard 1: Problem Overview
- **Chart Type:** Line chart
- **Data:** `v_problem_counts`
- **X-axis:** `day`
- **Y-axis:** `runs` (sum)
- **Color:** `problem_code`
- **Filters:** `tenant`, date range (last 30 days)

#### Dashboard 2: Fix Effectiveness
- **Chart Type:** Horizontal bar chart
- **Data:** `v_fix_success`
- **Rows:** `fix_code`
- **Columns:** `successes` (sum)
- **Color:** `avg_confidence` (gradient)
- **Filters:** `problem_code`
- **Sort:** Descending by successes

#### Dashboard 3: Time to Remediation
- **Chart Type:** Histogram
- **Data:** `v_ttr_days`
- **X-axis:** `ttr_days` (bins)
- **Y-axis:** Count
- **Filters:** `tenant`, `problem_code`

#### Dashboard 4: Tenant Health
- **Chart Type:** Multi-metric summary
- **Metrics:**
  - Total runs (last 7 days)
  - Active problems (distinct count)
  - Fix success rate (%)
  - Avg TTR (days)
- **Filters:** `tenant` (dropdown)

### Calculated Fields

**Fix Success Rate:**
```
SUM([successes]) / SUM([runs])
```

**Problem Recurrence:**
```
WINDOW_AVG(SUM([runs]), -6, 0)
```

**Confidence Tier:**
```
IF [avg_confidence] >= 0.8 THEN "High"
ELSEIF [avg_confidence] >= 0.6 THEN "Medium"
ELSE "Low"
END
```

## 6. Quick Validation Queries

### Top 10 Problems (Last 30 Days)
```sql
SELECT problem_code, sum(runs) AS cnt
FROM devdiag.v_problem_counts
WHERE day >= now() - interval '30 days'
GROUP BY 1
ORDER BY cnt DESC
LIMIT 10;
```

### Best Fixes by Success Count
```sql
SELECT problem_code, fix_code, successes, round(avg_confidence::numeric, 3)
FROM devdiag.v_fix_success
ORDER BY successes DESC
LIMIT 15;
```

### TTR Distribution
```sql
SELECT ttr_days, count(*) AS frequency
FROM devdiag.v_ttr_days
GROUP BY 1
ORDER BY 1;
```

### Recent Activity (Last 24h)
```sql
SELECT tenant, ts, jsonb_array_length(problems) AS problem_count, problems
FROM devdiag.diag_run
WHERE ts > now() - interval '24 hours'
ORDER BY ts DESC
LIMIT 20;
```

### Environment Diversity Leaders
```sql
SELECT problem_code, unique_environments, total_runs
FROM devdiag.v_env_diversity
ORDER BY unique_environments DESC
LIMIT 10;
```

## 7. Governance & Privacy

### Data Stored
✅ **Stored:**
- Timestamps
- Problem codes
- Fix codes
- Safe evidence keys (CSP, framework, XFO)
- Hashed target URLs
- Environment fingerprints

❌ **NOT Stored:**
- Request/response bodies
- HTTP headers (except safe ones)
- Authentication tokens
- User data
- Secrets

### Row-Level Security (Optional)

For multi-tenant analytics, enable RLS:

```sql
-- Enable RLS
ALTER TABLE devdiag.diag_run ENABLE ROW LEVEL SECURITY;
ALTER TABLE devdiag.fix_outcome ENABLE ROW LEVEL SECURITY;

-- Create policy (example: user sees only their tenant)
CREATE POLICY tenant_isolation ON devdiag.diag_run
  FOR SELECT
  USING (tenant = current_setting('app.current_tenant', TRUE));

-- Set tenant context in Tableau connection
-- Use Custom SQL: SET app.current_tenant = 'your-tenant';
```

### Data Retention

Configure automatic cleanup for old data:

```sql
-- Delete runs older than retention period (180 days default)
DELETE FROM devdiag.diag_run
WHERE ts < now() - interval '180 days';

-- Archive instead of delete (recommended)
INSERT INTO devdiag.diag_run_archive
SELECT * FROM devdiag.diag_run
WHERE ts < now() - interval '180 days';

DELETE FROM devdiag.diag_run
WHERE id IN (SELECT id FROM devdiag.diag_run_archive);
```

## 8. Optional: dbt Integration

If you use dbt for data transformations:

### Project Structure
```
devdiag_dbt/
├── dbt_project.yml
├── models/
│   ├── staging/
│   │   ├── stg_diag_run.sql
│   │   └── stg_fix_outcome.sql
│   └── marts/
│       ├── fct_problem_counts.sql
│       ├── fct_fix_success.sql
│       └── fct_ttr.sql
└── tests/
    ├── schema.yml
    └── not_null_tenant.sql
```

### Example Model (`fct_problem_counts.sql`)
```sql
{{ config(materialized='table') }}

WITH daily_problems AS (
  SELECT
    date_trunc('day', ts) AS day,
    tenant,
    jsonb_array_elements_text(problems) AS problem_code
  FROM {{ source('devdiag', 'diag_run') }}
)

SELECT
  day,
  tenant,
  problem_code,
  count(*) AS runs
FROM daily_problems
GROUP BY 1, 2, 3
```

### Run dbt
```bash
cd devdiag_dbt
dbt run
dbt test
```

## 9. Monitoring & Alerts

### Prometheus Metrics (Optional)

Expose Postgres stats:

```yaml
# Add to your observability stack
scrape_configs:
  - job_name: 'postgres-devdiag'
    static_configs:
      - targets: ['postgres-exporter:9187']
```

### Alert Examples

**High Problem Rate:**
```sql
-- Alert if >100 problems/day for any tenant
SELECT tenant, sum(runs) AS daily_problems
FROM devdiag.v_problem_counts
WHERE day = current_date
GROUP BY 1
HAVING sum(runs) > 100;
```

**Low Fix Success Rate:**
```sql
-- Alert if any fix has <50% success rate
SELECT problem_code, fix_code, avg_confidence
FROM devdiag.v_fix_success
WHERE avg_confidence < 0.5 AND successes > 10;
```

## 10. Backup & Recovery

### Automated Backups

```bash
# Daily backup script
#!/bin/bash
BACKUP_DIR="/backups/devdiag"
DATE=$(date +%Y%m%d)

pg_dump -h localhost -U devdiag -d devdiag \
  -t devdiag.diag_run -t devdiag.fix_outcome \
  > "$BACKUP_DIR/devdiag_$DATE.sql"

# Keep last 30 days
find "$BACKUP_DIR" -name "devdiag_*.sql" -mtime +30 -delete
```

### Point-in-Time Recovery

Enable WAL archiving in `postgresql.conf`:

```conf
wal_level = replica
archive_mode = on
archive_command = 'cp %p /archive/%f'
```

## Next Steps

1. ✅ Start Postgres: `docker compose -f deployments/postgres.devdiag.yml up -d`
2. ✅ Update `devdiag.yaml` with Postgres connection string
3. ✅ Verify schema: `psql -h localhost -U devdiag -d devdiag -c "\dt devdiag.*"`
4. ✅ Run validation queries (section 6)
5. ✅ Connect Tableau Desktop
6. ✅ Build starter dashboards (section 5)
7. ✅ Schedule sync job if using SQLite (section 4)
8. ✅ Set up monitoring/alerts (section 9)

## Troubleshooting

**Connection refused:**
```bash
docker compose -f deployments/postgres.devdiag.yml logs postgres
```

**Schema not found:**
```bash
psql -h localhost -U devdiag -d devdiag -f deployments/postgres-init.sql
```

**Sync script fails:**
```bash
# Check SQLite path
ls -la devdiag.db

# Test Postgres connection
psql "$PG_DSN" -c "SELECT version();"
```

## Support

For issues or questions:
- GitHub Issues: https://github.com/leok974/mcp-devdiag/issues
- Documentation: https://github.com/leok974/mcp-devdiag/blob/main/README.md
