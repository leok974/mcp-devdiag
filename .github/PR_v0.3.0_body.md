# v0.3.0 — Learning Loop, PostgreSQL Analytics, Grafana, Alerts

## 🎯 Overview

This release transforms DevDiag from a diagnostic tool into a **self-improving learning system** with:
- **Closed-loop learning** from successful fixes
- **PostgreSQL analytics warehouse** with 6 materialized views
- **Grafana dashboards** for real-time monitoring
- **Production alerting suite** with 5 critical alerts
- **Operational excellence** with runbooks and health checks

## 📊 Major Features

### 1. Closed-Loop Learning (Phase 20)
- **Automatic fix suggestion** based on historical success patterns
- **Context-aware ranking** (environment, problem, tenant similarity)
- **Confidence scoring** for fix recommendations
- **SQLite storage** for learning data with schema versioning

**Key Commits:**
- `3a56937` - Closed-loop learning from successful fixes (SQLite)

### 2. PostgreSQL Analytics Warehouse (Phase 20)
**Migration from SQLite to PostgreSQL for production scale:**
- 6 materialized views for analytics queries
- Row-level security with dedicated users (`devdiag_writer`, `grafana`)
- Automated backup scripts (daily compressed dumps)
- Retention policy scripts (180-day rolling window)

**Views Created:**
- `v_problem_counts` - Daily problem occurrence trends
- `v_fix_success` - Learning effectiveness metrics
- `v_ttr_days` - Time-to-resolution analytics
- `v_env_diversity` - Environment combination tracking
- `v_fix_ranking` - Context-aware fix recommendations
- `v_recent_activity` - Latest diagnostic runs

**Key Commits:**
- `27a927c` - Fix v_ttr_days view and deploy PostgreSQL warehouse
- `0337fef` - PostgreSQL warehouse with Tableau dashboards

### 3. Grafana Integration Suite (Phase 20)
**Complete observability stack:**
- **Dashboard:** 8-panel DevDiag Analytics dashboard
  - Problem occurrence trends (7d)
  - Fix success rate
  - Time to resolution (median)
  - Environment diversity
  - Recent activity log
  - Top problems
  - Learning effectiveness
  - Fix ranking

- **Automated Import Scripts:**
  - `import-datasource.ps1` / `import-datasource.sh`
  - `import-dashboard.ps1` / `import-dashboard.sh`
  - Idempotent (safe to re-run)
  - GitHub Actions workflow for CI/CD

**Key Commits:**
- `8be9a22` - Complete Grafana integration suite
- `b8eeb4b` - Automated import scripts and CI/CD workflow

### 4. Production Alerting & Monitoring (Phase 21)
**5 Production-Ready Alerts:**
1. **Runs Stalled** (Critical) - Pipeline failure detection (2h threshold)
2. **Confidence Drop** (Warning) - Learning quality <70%
3. **TTR Regression** (Warning) - Median resolution time >2 days
4. **High Diversity** (Warning) - >10 distinct problems/day
5. **Top Problem Dominates** (Warning) - Single problem >20% of runs

**10 Health Checks (`deployments/health-checks.sql`):**
- Data freshness (< 2h)
- Schema integrity (6 views, 9 indexes)
- Fix confidence quality (>= 0.70)
- Retention policy (170-190 days)
- Problem diversity trends
- Database size monitoring
- Volume trends
- Unlearned problems
- Stale data detection
- Summary dashboard query

**Key Commits:**
- `e25e4d5` - Production alerting and monitoring suite
- `94d2d81` - Manual alert setup guide

### 5. Operational Excellence (Phase 21)
**Complete operations runbook (`deployments/OPERATIONS.md`):**
- Daily health check procedures
- Alert response playbooks (all 5 alerts)
- Maintenance schedules (weekly/monthly/quarterly)
- Disaster recovery procedures (RTO: <2h, RPO: <24h)
- Troubleshooting guides

**CI/CD Guardrails:**
- PostgreSQL schema validation
- Data freshness smoke tests
- Prevents broken dashboard imports

---

## 📦 What's Included

### New Files (30+)
**PostgreSQL Schema:**
- `scripts/postgres/schema.sql` - Database schema with 6 views
- `scripts/postgres/setup.sql` - User creation and permissions
- `scripts/postgres/backup.sh` - Automated backup script
- `scripts/postgres/retention-cleanup.sql` - 180-day retention policy

**Grafana Dashboards:**
- `deployments/grafana/dashboards/devdiag-analytics.json` - 8-panel dashboard
- `deployments/grafana/datasources/devdiag-postgres.json` - PostgreSQL datasource

**Grafana Scripts:**
- `scripts/grafana/import-datasource.{ps1,sh}` - Datasource import
- `scripts/grafana/import-dashboard.{ps1,sh}` - Dashboard import
- `scripts/grafana/import-alerts.{ps1,sh}` - Alert import (v0.3.1)

**Alerts:**
- `deployments/grafana/alerts/*.json` - 5 alert definitions
- `deployments/grafana/alerts/README.md` - Manual setup guide

**Operations:**
- `deployments/health-checks.sql` - 10 health checks
- `deployments/OPERATIONS.md` - Complete runbook
- `deployments/PHASE_21_SUMMARY.md` - Detailed delivery summary

**CI/CD:**
- `.github/workflows/grafana-import.yml` - Automated Grafana import
- Schema validation steps
- Data freshness checks

### Modified Files
- `mcp_devdiag/analyzer.py` - Learning logic (fix suggestions)
- `mcp_devdiag/schema.py` - Extended schema for learning
- `.github/workflows/grafana-import.yml` - Added validation

---

## 🧪 Testing & Validation

### Live Testing Results
**Grafana Integration:**
- ✅ Datasource created: `DevDiag Postgres` (ID: 1)
- ✅ Dashboard imported: `DevDiag Analytics`
- ✅ Alert folder created: `DevDiag Alerts`
- ✅ Idempotent imports verified
- ✅ All queries returning data

### Health Checks
- ✅ 10 health checks operational
- ✅ Summary dashboard query validated
- ✅ Cron-ready for automation

### Import Scripts
- ✅ Datasource import: SUCCESS (idempotent)
- ✅ Dashboard import: SUCCESS (idempotent)
- ⚠️ Alert import: Deferred to v0.3.1 (manual guide provided)

---

## 🚀 Migration Guide

### For Existing Users

**1. Install PostgreSQL 16:**
```bash
# Ubuntu/Debian
sudo apt-get install postgresql-16

# macOS
brew install postgresql@16
```

**2. Set up database:**
```bash
cd scripts/postgres
psql -U postgres -f setup.sql
psql -U postgres -d devdiag -f schema.sql
```

**3. Configure MCP server:**
Update `.vscode/mcp.json`:
```json
{
  "mcpServers": {
    "devdiag": {
      "env": {
        "DEVDIAG_PG_HOST": "localhost:5432",
        "DEVDIAG_PG_USER": "devdiag_writer",
        "DEVDIAG_PG_PASS": "your-password",
        "DEVDIAG_PG_DB": "devdiag"
      }
    }
  }
}
```

**4. Import Grafana resources (optional):**
```bash
export GRAFANA_URL="http://localhost:3000"
export GRAFANA_API_KEY="your-api-key"

./scripts/grafana/import-datasource.sh
./scripts/grafana/import-dashboard.sh
```

**5. Set up daily health checks:**
```bash
# Add to crontab -e
0 8 * * * psql "postgresql://..." -f /path/to/deployments/health-checks.sql
```

---

## 📚 Documentation

**Quick Start:**
- `deployments/grafana/alerts/README.md` - Alert setup guide
- `deployments/OPERATIONS.md` - Complete operational runbook
- `deployments/PHASE_21_SUMMARY.md` - Detailed delivery summary

**Scripts:**
- `scripts/grafana/README.md` - Grafana import scripts
- `scripts/postgres/README.md` - PostgreSQL setup

**Health & Monitoring:**
- `deployments/health-checks.sql` - Database health validation
- `deployments/grafana/dashboards/` - Grafana dashboards
- `deployments/grafana/alerts/` - Alert definitions

---

## ⚠️ Known Limitations

### Alert Import (Deferred to v0.3.1)
**Issue:** Grafana provisioning API requires different JSON format than dashboard export  
**Workaround:** Manual alert setup guide with copy/paste SQL queries  
**Impact:** Alerts must be created manually via Grafana UI  
**Timeline:** Fix planned for v0.3.1

**Manual Setup Guide:** `deployments/grafana/alerts/README.md`

---

## 🔄 Breaking Changes

### Environment Variables
**New Required Variables:**
- `DEVDIAG_PG_HOST` - PostgreSQL host:port (e.g., `localhost:5432`)
- `DEVDIAG_PG_USER` - Database user (e.g., `devdiag_writer`)
- `DEVDIAG_PG_PASS` - Database password
- `DEVDIAG_PG_DB` - Database name (e.g., `devdiag`)

**Migration:** Update `.vscode/mcp.json` with PostgreSQL credentials

### Data Storage
**Changed:** SQLite → PostgreSQL  
**Impact:** Historical data must be migrated manually if needed  
**Reason:** Production scalability, analytics performance, concurrent writes

---

## 🎯 Success Metrics

**Learning Effectiveness:**
- Fix suggestions based on historical patterns
- Context-aware ranking (environment, problem, tenant)
- Confidence scoring for recommendations

**Observability:**
- 8-panel Grafana dashboard with real-time data
- 5 production alerts covering critical scenarios
- 10 health checks for data quality

**Operational Excellence:**
- Complete runbook with disaster recovery procedures
- Automated backup and retention scripts
- CI/CD validation for dashboard imports

**Production Readiness:**
- ✅ Real Grafana instance tested
- ✅ Datasource connection verified
- ✅ Dashboard rendering confirmed
- ✅ Idempotent import scripts
- ✅ No data loss scenarios documented

---

## 🔮 Next Steps (v0.3.1)

**Planned Improvements:**
1. Fix alert JSON format for automated import
2. Add additional alerts (disk space, backup failures)
3. Implement anomaly detection (ML-based)
4. Add Slack/email notification templates
5. PagerDuty integration guide

---

## 📈 Commit History

**Learning Loop:**
- `3a56937` - feat(learn): closed-loop learning from successful fixes (SQLite)

**PostgreSQL Analytics:**
- `27a927c` - feat(analytics): fix v_ttr_days view and deploy PostgreSQL warehouse
- `0337fef` - feat(analytics): PostgreSQL warehouse with Tableau dashboards

**Grafana Integration:**
- `8be9a22` - feat(grafana): add complete Grafana integration suite
- `b8eeb4b` - feat(grafana): add automated import scripts and CI/CD workflow

**Operational Excellence:**
- `e25e4d5` - feat(ops): production alerting and monitoring suite
- `94d2d81` - docs(alerts): add manual setup guide for Grafana alerts
- `f8b4dcb` - docs: Phase 21 operational excellence completion summary

---

## 🙏 Review Checklist

- [ ] Review learning logic (`mcp_devdiag/analyzer.py`)
- [ ] Verify PostgreSQL schema (`scripts/postgres/schema.sql`)
- [ ] Test Grafana dashboard import
- [ ] Review operations runbook
- [ ] Validate health check queries
- [ ] Check alert definitions
- [ ] Verify CI/CD workflow changes

---

**Ready for merge** ✅

/cc @leok974
