# Grafana Alert Queries for DevDiag Analytics

This document contains pre-built alert queries for Grafana Unified Alerting.
Use these with the DevDiag Postgres datasource.

## Alert 1: Top Problem Dominates (>20% of today's runs)

**Description:** Triggers when a single problem code accounts for more than 20% of diagnostic runs today.

**Use Case:** Detect when a specific issue suddenly affects many targets.

**Query:**
```sql
WITH today AS (
  SELECT COUNT(*)::float8 AS total
  FROM devdiag.diag_run
  WHERE ts::date = CURRENT_DATE
),
by_code AS (
  SELECT jsonb_array_elements_text(problems) AS problem_code, 
         COUNT(*)::float8 AS cnt
  FROM devdiag.diag_run
  WHERE ts::date = CURRENT_DATE
  GROUP BY 1
)
SELECT MAX(cnt / NULLIF((SELECT total FROM today),0)) AS top_share
FROM by_code;
```

**Alert Condition:** `top_share > 0.20` for 15 minutes

**Severity:** Warning

**Notification:** Slack/Email/PagerDuty

---

## Alert 2: Diagnostic Runs Stalled (No runs in last 2 hours)

**Description:** Triggers when no diagnostic runs have been recorded in the last 2 hours.

**Use Case:** Detect pipeline failures or integration issues.

**Query:**
```sql
SELECT COUNT(*) AS cnt
FROM devdiag.diag_run
WHERE ts >= NOW() - INTERVAL '2 hours';
```

**Alert Condition:** `cnt = 0` for 10 minutes

**Severity:** Critical

**Notification:** PagerDuty/Phone

---

## Alert 3: Median TTR Regressed (>2 days over 7d window)

**Description:** Triggers when median time-to-remediation exceeds 2 days over the last 7 days.

**Use Case:** Detect degradation in problem resolution speed.

**Query:**
```sql
SELECT PERCENTILE_DISC(0.5) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM ttr_days)/86400) AS median_ttr_days
FROM devdiag.v_ttr_days
WHERE first_seen_day >= CURRENT_DATE - INTERVAL '7 days';
```

**Alert Condition:** `median_ttr_days > 2` for 30 minutes

**Severity:** Warning

**Notification:** Slack/Email

---

## Alert 4: High Problem Diversity (>10 distinct problems today)

**Description:** Triggers when more than 10 distinct problem codes appear in one day.

**Use Case:** Detect widespread issues or system instability.

**Query:**
```sql
SELECT COUNT(DISTINCT problem_code) AS distinct_problems
FROM devdiag.v_problem_counts
WHERE day = CURRENT_DATE;
```

**Alert Condition:** `distinct_problems > 10` for 15 minutes

**Severity:** Warning

**Notification:** Slack

---

## Alert 5: Fix Success Rate Dropping (<70% confidence)

**Description:** Triggers when average fix confidence drops below 70%.

**Use Case:** Detect when learning model quality degrades.

**Query:**
```sql
SELECT AVG(avg_confidence) AS overall_fix_confidence
FROM devdiag.v_fix_success
WHERE last_success >= NOW() - INTERVAL '7 days';
```

**Alert Condition:** `overall_fix_confidence < 0.70` for 30 minutes

**Severity:** Warning

**Notification:** Email

---

## Setup Instructions

### 1. Create Alert in Grafana UI

1. Navigate to **Alerting** → **Alert rules**
2. Click **New alert rule**
3. Enter rule name (e.g., "DevDiag: Top Problem Dominates")
4. Set query:
   - **Datasource:** DevDiag Postgres
   - **Query:** Paste SQL from above
5. Set conditions:
   - **Threshold:** As specified above
   - **For:** Duration as specified
6. Add labels: `service=devdiag`, `severity=warning`
7. Save and test

### 2. Configure Contact Points

- **Slack:** Alerting → Contact points → Add Slack webhook
- **Email:** Add SMTP settings
- **PagerDuty:** Add PagerDuty integration key

### 3. Create Notification Policies

Map labels to contact points:
- `severity=critical` → PagerDuty
- `severity=warning` → Slack + Email
- `service=devdiag` → DevOps channel

---

## Testing Alerts

Manually trigger alerts by inserting test data:

```sql
-- Trigger "Runs Stalled" alert (insert old data)
INSERT INTO devdiag.diag_run (ts, tenant, target_hash, env_fp, problems, evidence, preset)
VALUES (NOW() - INTERVAL '3 hours', 'test', 'hash', 'env', '[]'::jsonb, '{}'::jsonb, 'test');

-- Trigger "Top Problem Dominates" (insert many runs with same problem)
DO $$
BEGIN
  FOR i IN 1..100 LOOP
    INSERT INTO devdiag.diag_run (ts, tenant, target_hash, env_fp, problems, evidence, preset)
    VALUES (NOW(), 'test', 'hash' || i, 'env', '["TEST_PROBLEM"]'::jsonb, '{}'::jsonb, 'test');
  END LOOP;
END $$;

-- Clean up test data
DELETE FROM devdiag.diag_run WHERE tenant = 'test';
```
