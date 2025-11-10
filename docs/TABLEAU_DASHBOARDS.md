# Tableau Dashboard Quick Reference

Pre-built dashboard templates for DevDiag analytics.

## Connection Setup

**Server:** localhost (or your Postgres host)  
**Port:** 5432  
**Database:** devdiag  
**Schema:** devdiag  
**User:** devdiag  

## Data Sources

### Primary Tables
- `diag_run` - Raw diagnostic runs
- `fix_outcome` - Learned fix outcomes

### Analytics Views (Recommended)
- `v_problem_counts` - Daily problem aggregates
- `v_fix_success` - Fix effectiveness metrics
- `v_ttr_days` - Time-to-remediation
- `v_env_diversity` - Environment diversity
- `v_fix_ranking` - Ranked fixes per problem

## Dashboard 1: Problem Trend Analysis

**Purpose:** Track problem occurrence over time

### Charts

**Line Chart: Problems Over Time**
- **Data Source:** `v_problem_counts`
- **Mark Type:** Line
- **Columns:** `day` (continuous date)
- **Rows:** `SUM(runs)`
- **Color:** `problem_code`
- **Filters:** 
  - Date range: Last 30 days
  - Tenant (optional)
  - Problem code (optional)

**Bar Chart: Top 10 Problems**
- **Data Source:** `v_problem_counts`
- **Mark Type:** Bar
- **Columns:** `SUM(runs)`
- **Rows:** `problem_code`
- **Filters:** Date range: Last 7 days
- **Sort:** Descending
- **Limit:** Top 10

## Dashboard 2: Fix Effectiveness

**Purpose:** Identify which fixes work best

### Charts

**Horizontal Bar: Fix Success Ranking**
- **Data Source:** `v_fix_success`
- **Mark Type:** Bar
- **Columns:** `SUM(successes)`
- **Rows:** `fix_code`
- **Color:** `avg_confidence` (gradient: Red → Yellow → Green)
- **Labels:** Show `successes` and `avg_confidence`
- **Sort:** Descending by successes

**Scatter Plot: Confidence vs Support**
- **Data Source:** `v_fix_success`
- **Mark Type:** Circle
- **Columns:** `SUM(successes)`
- **Rows:** `AVG(avg_confidence)`
- **Color:** `problem_code`
- **Size:** `SUM(successes)`
- **Labels:** `fix_code` (on hover)

**Heatmap: Problem-Fix Matrix**
- **Data Source:** `v_fix_ranking`
- **Mark Type:** Square
- **Columns:** `fix_code`
- **Rows:** `problem_code`
- **Color:** `rank` (gradient: Green → Red)
- **Filters:** `rank <= 5` (top 5 fixes only)

## Dashboard 3: Time to Remediation

**Purpose:** Measure how quickly problems get fixed

### Charts

**Histogram: TTR Distribution**
- **Data Source:** `v_ttr_days`
- **Mark Type:** Bar
- **Columns:** `ttr_days` (bins of 1 day)
- **Rows:** `CNT()`
- **Color:** Gradient by bin
- **Statistics Line:** Average TTR

**Box Plot: TTR by Problem**
- **Data Source:** `v_ttr_days`
- **Mark Type:** Box-and-whisker
- **Columns:** `problem_code`
- **Rows:** `ttr_days`
- **Reference Line:** Median TTR

**Trend: TTR Over Time**
- **Data Source:** `v_ttr_days`
- **Mark Type:** Line
- **Columns:** `MONTH(first_seen_day)`
- **Rows:** `AVG(ttr_days)`
- **Trend Line:** Show linear regression

## Dashboard 4: Tenant Health Overview

**Purpose:** Single-tenant monitoring dashboard

### Metrics (Big Number)

**Total Runs (7 Days)**
```
SUM(runs) WHERE [day] >= TODAY()-7
```

**Active Problems**
```
COUNTD([problem_code]) WHERE [day] >= TODAY()-7
```

**Fix Success Rate**
```
SUM([successes]) / SUM([runs]) * 100
```

**Avg TTR (Days)**
```
AVG([ttr_days])
```

### Charts

**Sparkline: Daily Runs**
- **Data Source:** `v_problem_counts`
- **Mark Type:** Line
- **Columns:** `day` (last 30 days)
- **Rows:** `SUM(runs)`
- **Axis:** Hide
- **Compact view**

**Table: Active Problems**
- **Data Source:** `v_problem_counts`
- **Columns:** `problem_code`, `SUM(runs)`, `% of Total`
- **Filters:** Date range: Last 7 days
- **Conditional Formatting:** Highlight high-frequency problems

## Calculated Fields

### Fix Success Rate
```
SUM([successes]) / SUM([runs])
```

### Confidence Tier
```
IF [avg_confidence] >= 0.8 THEN "High"
ELSEIF [avg_confidence] >= 0.6 THEN "Medium"
ELSE "Low"
END
```

### Problem Severity (by frequency)
```
IF SUM([runs]) > 100 THEN "Critical"
ELSEIF SUM([runs]) > 50 THEN "High"
ELSEIF SUM([runs]) > 10 THEN "Medium"
ELSE "Low"
END
```

### Week-over-Week Change
```
(SUM([runs]) - LOOKUP(SUM([runs]), -7)) / LOOKUP(SUM([runs]), -7)
```

### Rolling 7-Day Average
```
WINDOW_AVG(SUM([runs]), -6, 0)
```

### Days Since Last Occurrence
```
DATEDIFF('day', MAX([day]), TODAY())
```

## Filters

### Global Filters (Apply to All Dashboards)
- **Tenant** (dropdown, multi-select)
- **Date Range** (relative date: Last 7/30/90 days)
- **Problem Code** (dropdown, optional)

### Dashboard-Specific Filters
- **Fix Code** (for Fix Effectiveness dashboard)
- **Environment** (if you add env_fp decoding)
- **Confidence Threshold** (slider: 0.0 - 1.0)

## Actions

### Filter Action: Problem Drill-Down
- **Source:** Any chart showing `problem_code`
- **Target:** Fix Effectiveness dashboard
- **Action:** Filter by selected problem
- **Clear:** Show all fixes when unselected

### Highlight Action: Cross-Chart Selection
- **Source:** All charts
- **Target:** All charts
- **Action:** Highlight matching data points
- **Trigger:** Hover or select

## Color Palettes

### Confidence Colors
- High (>0.8): `#2ca02c` (green)
- Medium (0.6-0.8): `#ff7f0e` (orange)
- Low (<0.6): `#d62728` (red)

### Problem Severity
- Critical: `#8B0000` (dark red)
- High: `#FF4500` (red-orange)
- Medium: `#FFA500` (orange)
- Low: `#FFD700` (gold)

## Publishing

### Tableau Server/Cloud
1. **File** → **Publish Workbook**
2. Select **devdiag** project
3. Authentication: **Embed Password** or **Prompt User**
4. Refresh schedule: **Daily at 6 AM**

### Permissions
- **Viewer:** Can view dashboards
- **Explorer:** Can filter and interact
- **Creator:** Can edit dashboards

## Alerts

### Alert: High Problem Rate
- **Metric:** Total runs per day
- **Threshold:** > 100
- **Frequency:** Daily
- **Recipients:** ops-team@company.com

### Alert: Low Fix Success Rate
- **Metric:** Fix success rate
- **Threshold:** < 50%
- **Frequency:** Weekly
- **Recipients:** devops-team@company.com

## Tips

1. **Performance:** Use extracts for large datasets (>1M rows)
2. **Freshness:** Schedule daily extract refresh at 6 AM
3. **Drill-Down:** Add `target_hash` to detail for granular filtering
4. **Context:** Add tenant/environment filters to context for better performance
5. **Mobile:** Design for mobile with single-column layouts

## Troubleshooting

**Blank dashboard:**
- Check data source connection
- Verify schema: `devdiag`
- Refresh data source

**Slow performance:**
- Create extract instead of live connection
- Add indexes on `tenant`, `ts`, `problem_code`
- Limit date range to last 90 days

**Missing data:**
- Run sync script: `python scripts/sync_sqlite_to_pg.py`
- Check learning enabled: `learn.enabled: true`
- Verify database has data: `SELECT count(*) FROM devdiag.diag_run;`

## Next Steps

1. Import sample workbook: `tableau/devdiag_starter.twbx` (if provided)
2. Customize colors and branding
3. Add company logo
4. Publish to Tableau Server
5. Share dashboard URL with team
