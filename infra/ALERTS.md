# Grafana/Prometheus Alerts for DevDiag HTTP

## Alert Rules Configuration

### Prometheus Alert Rules

Create `devdiag_alerts.yml` in your Prometheus config directory:

```yaml
groups:
  - name: devdiag_http_alerts
    interval: 30s
    rules:
      # Service Down Alert
      - alert: DevDiagServiceDown
        expr: devdiag_http_up == 0
        for: 5m
        labels:
          severity: critical
          service: devdiag-http
          component: availability
        annotations:
          summary: "DevDiag HTTP service is down"
          description: "DevDiag HTTP service has been unavailable for 5 minutes. No health checks passing."
          runbook_url: "https://github.com/leok974/mcp-devdiag/blob/main/infra/TROUBLESHOOTING.md#service-down"
          dashboard_url: "https://grafana.leoklemet.com/d/devdiag/devdiag-http"

      # High 503 Rate (Capacity Saturation)
      - alert: DevDiagCapacitySaturation
        expr: rate(devdiag_http_errors_total{code="503"}[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
          service: devdiag-http
          component: capacity
        annotations:
          summary: "DevDiag HTTP hitting capacity limits"
          description: "High rate of 503 responses ({{ $value | humanize }}/s) - service at capacity. Check MAX_CONCURRENT setting."
          query: 'rate(devdiag_http_errors_total{code="503"}[5m])'
          action: "Scale MAX_CONCURRENT or investigate slow requests"
          dashboard_url: "https://grafana.leoklemet.com/d/devdiag/devdiag-http?viewPanel=capacity"

      # High Latency (p95 > 120s)
      - alert: DevDiagHighLatency
        expr: histogram_quantile(0.95, rate(devdiag_http_duration_seconds_bucket{path="/diag/run"}[5m])) > 120
        for: 15m
        labels:
          severity: warning
          service: devdiag-http
          component: performance
        annotations:
          summary: "DevDiag HTTP p95 latency exceeds 120s"
          description: "95th percentile latency is {{ $value | humanize }}s (threshold: 120s). Diagnostic runs taking too long."
          query: 'histogram_quantile(0.95, rate(devdiag_http_duration_seconds_bucket{path="/diag/run"}[5m]))'
          action: "Check DEVDIAG_TIMEOUT_S, investigate slow target URLs, review Playwright performance"
          dashboard_url: "https://grafana.leoklemet.com/d/devdiag/devdiag-http?viewPanel=latency"

      # Rate Limit Saturation (429s spiking)
      - alert: DevDiagRateLimitSaturation
        expr: rate(devdiag_http_errors_total{code="429"}[5m]) > 0.5
        for: 5m
        labels:
          severity: info
          service: devdiag-http
          component: rate-limiting
        annotations:
          summary: "DevDiag HTTP rate limiting active"
          description: "High rate of 429 responses ({{ $value | humanize }}/s). Clients may need to back off or RATE_LIMIT_RPS needs increase."
          query: 'rate(devdiag_http_errors_total{code="429"}[5m])'
          action: "Review RATE_LIMIT_RPS setting or investigate aggressive clients"
          dashboard_url: "https://grafana.leoklemet.com/d/devdiag/devdiag-http?viewPanel=rate-limiting"

      # Error Rate Spike
      - alert: DevDiagErrorRateHigh
        expr: |
          (
            sum(rate(devdiag_http_errors_total[5m]))
            /
            sum(rate(devdiag_http_requests_total[5m]))
          ) > 0.05
        for: 10m
        labels:
          severity: warning
          service: devdiag-http
          component: errors
        annotations:
          summary: "DevDiag HTTP error rate exceeds 5%"
          description: "Error rate is {{ $value | humanizePercentage }} (threshold: 5%). Check logs for details."
          query: 'sum(rate(devdiag_http_errors_total[5m])) / sum(rate(devdiag_http_requests_total[5m]))'
          action: "Review structured logs, check JWT validation, verify target allowlists"
          dashboard_url: "https://grafana.leoklemet.com/d/devdiag/devdiag-http?viewPanel=errors"

      # JWT Validation Failures
      - alert: DevDiagJWTValidationFailures
        expr: rate(devdiag_http_errors_total{code="401"}[5m]) > 0.2
        for: 5m
        labels:
          severity: warning
          service: devdiag-http
          component: authentication
        annotations:
          summary: "High rate of JWT validation failures"
          description: "401 responses at {{ $value | humanize }}/s. Check JWKS availability and token expiration."
          query: 'rate(devdiag_http_errors_total{code="401"}[5m])'
          action: "Verify JWKS_URL accessibility, check for expired tokens, review JWT_AUD setting"
          dashboard_url: "https://grafana.leoklemet.com/d/devdiag/devdiag-http?viewPanel=auth"

      # Allowlist Rejections
      - alert: DevDiagAllowlistRejections
        expr: rate(devdiag_http_errors_total{code="422"}[5m]) > 0.1
        for: 5m
        labels:
          severity: info
          service: devdiag-http
          component: security
        annotations:
          summary: "Allowlist rejections detected"
          description: "422 validation errors at {{ $value | humanize }}/s. Clients attempting blocked hosts."
          query: 'rate(devdiag_http_errors_total{code="422"}[5m])'
          action: "Review ALLOW_TARGET_HOSTS and TENANT_ALLOW_HOSTS_JSON, check structured logs for rejected hosts"
          dashboard_url: "https://grafana.leoklemet.com/d/devdiag/devdiag-http?viewPanel=security"

      # No Requests (Dead Service)
      - alert: DevDiagNoTraffic
        expr: rate(devdiag_http_requests_total[15m]) == 0
        for: 1h
        labels:
          severity: info
          service: devdiag-http
          component: traffic
        annotations:
          summary: "DevDiag HTTP receiving no traffic"
          description: "No requests in past 15 minutes. Service may be unreachable or clients disabled."
          query: 'rate(devdiag_http_requests_total[15m])'
          action: "Verify Cloudflare Tunnel status, check client configurations"
          dashboard_url: "https://grafana.leoklemet.com/d/devdiag/devdiag-http"
```

### Prometheus Configuration

Add to `prometheus.yml`:

```yaml
# Prometheus scrape config
scrape_configs:
  - job_name: 'devdiag-http'
    scrape_interval: 15s
    scrape_timeout: 10s
    metrics_path: '/metrics'
    scheme: https
    static_configs:
      - targets: ['devdiag.leoklemet.com']
        labels:
          environment: 'production'
          service: 'devdiag-http'

# Alert rule files
rule_files:
  - '/etc/prometheus/alerts/devdiag_alerts.yml'

# Alertmanager configuration
alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']
```

## Grafana Dashboard

### Dashboard JSON (import to Grafana)

Create `devdiag_dashboard.json`:

```json
{
  "dashboard": {
    "title": "DevDiag HTTP Monitoring",
    "panels": [
      {
        "title": "Service Health",
        "targets": [
          {
            "expr": "devdiag_http_up",
            "legendFormat": "Service Up"
          }
        ],
        "type": "stat",
        "fieldConfig": {
          "defaults": {
            "thresholds": {
              "steps": [
                { "value": 0, "color": "red" },
                { "value": 1, "color": "green" }
              ]
            }
          }
        }
      },
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "sum(rate(devdiag_http_requests_total[5m])) by (path)",
            "legendFormat": "{{path}}"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "sum(rate(devdiag_http_errors_total[5m])) by (code)",
            "legendFormat": "{{code}}"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Latency Percentiles",
        "targets": [
          {
            "expr": "histogram_quantile(0.50, rate(devdiag_http_duration_seconds_bucket[5m]))",
            "legendFormat": "p50"
          },
          {
            "expr": "histogram_quantile(0.95, rate(devdiag_http_duration_seconds_bucket[5m]))",
            "legendFormat": "p95"
          },
          {
            "expr": "histogram_quantile(0.99, rate(devdiag_http_duration_seconds_bucket[5m]))",
            "legendFormat": "p99"
          }
        ],
        "type": "graph",
        "yaxes": [
          { "format": "s", "label": "Duration" }
        ]
      },
      {
        "title": "Capacity Saturation (503s)",
        "targets": [
          {
            "expr": "rate(devdiag_http_errors_total{code=\"503\"}[5m])",
            "legendFormat": "503 rate"
          }
        ],
        "type": "graph",
        "alert": {
          "name": "Capacity Saturation",
          "conditions": [
            {
              "query": { "params": ["A", "5m", "now"] },
              "reducer": { "type": "avg" },
              "evaluator": { "type": "gt", "params": [0.1] }
            }
          ]
        }
      },
      {
        "title": "Rate Limiting (429s with Retry-After)",
        "targets": [
          {
            "expr": "rate(devdiag_http_errors_total{code=\"429\"}[5m])",
            "legendFormat": "429 rate"
          }
        ],
        "type": "graph"
      },
      {
        "title": "JWT Auth Failures (401s)",
        "targets": [
          {
            "expr": "rate(devdiag_http_errors_total{code=\"401\"}[5m])",
            "legendFormat": "401 rate"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Allowlist Rejections (422s)",
        "targets": [
          {
            "expr": "rate(devdiag_http_errors_total{code=\"422\"}[5m])",
            "legendFormat": "422 rate"
          }
        ],
        "type": "graph"
      }
    ]
  }
}
```

### Creating Dashboard via UI

1. Navigate to Grafana → Dashboards → New Dashboard
2. Add panel for each metric (see queries above)
3. Configure thresholds and alerts
4. Save as "DevDiag HTTP Monitoring"

## Alert Notification Channels

### Slack Integration

```yaml
# alertmanager.yml
receivers:
  - name: 'devdiag-slack'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
        channel: '#devops-alerts'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
        send_resolved: true

route:
  receiver: 'devdiag-slack'
  group_by: ['alertname', 'severity']
  group_wait: 10s
  group_interval: 5m
  repeat_interval: 4h
  routes:
    - match:
        severity: critical
      receiver: 'devdiag-slack'
      repeat_interval: 30m
```

### Email Integration

```yaml
receivers:
  - name: 'devdiag-email'
    email_configs:
      - to: 'ops@leoklemet.com'
        from: 'alerts@leoklemet.com'
        smarthost: 'smtp.gmail.com:587'
        auth_username: 'alerts@leoklemet.com'
        auth_password: '$SMTP_PASSWORD'
        headers:
          Subject: '[{{ .Status }}] DevDiag Alert: {{ .GroupLabels.alertname }}'
```

### PagerDuty Integration

```yaml
receivers:
  - name: 'devdiag-pagerduty'
    pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_SERVICE_KEY'
        description: '{{ .CommonAnnotations.summary }}'
        severity: '{{ .CommonLabels.severity }}'
```

## Log Verification

### JSON Logs with x-request-id

**Expected Format:**
```json
{"event":"http_access","rid":"550e8400-e29b-41d4-a716-446655440000","path":"/diag/run","method":"POST","status":200,"ms":3456.78}
{"event":"http_error","rid":"550e8400-e29b-41d4-a716-446655440001","path":"/diag/run","method":"POST","status":429,"ms":12.34}
```

### Verification Commands

```bash
# Check logs for JSON format
docker logs infra-devdiag-http-1 --tail 100 | jq .

# Verify x-request-id present
docker logs infra-devdiag-http-1 --tail 100 | jq -r '.rid' | head -10

# Filter by request ID
docker logs infra-devdiag-http-1 | jq 'select(.rid=="550e8400-e29b-41d4-a716-446655440000")'

# Track request end-to-end
RID=$(uuidgen)
curl -s -D- -H "x-request-id: $RID" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://applylens.app","preset":"app","tenant":"applylens"}' \
  https://devdiag.leoklemet.com/diag/run

# Then search logs
docker logs infra-devdiag-http-1 | jq "select(.rid==\"$RID\")"
```

### Log Aggregation (Elasticsearch/Loki)

**Filebeat config for Elasticsearch:**
```yaml
filebeat.inputs:
  - type: docker
    containers.ids:
      - 'infra-devdiag-http-1'
    json.keys_under_root: true
    json.add_error_key: true

processors:
  - decode_json_fields:
      fields: ["message"]
      target: ""
      overwrite_keys: true

output.elasticsearch:
  hosts: ["localhost:9200"]
  index: "devdiag-http-%{+yyyy.MM.dd}"
```

**Loki config for Grafana:**
```yaml
# promtail.yml
scrape_configs:
  - job_name: devdiag-http
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
        refresh_interval: 5s
    relabel_configs:
      - source_labels: ['__meta_docker_container_name']
        regex: '/(infra-devdiag-http-1)'
        action: keep
    pipeline_stages:
      - json:
          expressions:
            event: event
            rid: rid
            path: path
            method: method
            status: status
            ms: ms
      - labels:
          event:
          path:
          method:
```

## Query Examples

### Prometheus Queries

```promql
# Request rate per path
sum(rate(devdiag_http_requests_total[5m])) by (path)

# Error rate by code
sum(rate(devdiag_http_errors_total[5m])) by (code)

# Overall error rate percentage
sum(rate(devdiag_http_errors_total[5m])) / sum(rate(devdiag_http_requests_total[5m])) * 100

# p50, p95, p99 latency
histogram_quantile(0.50, rate(devdiag_http_duration_seconds_bucket[5m]))
histogram_quantile(0.95, rate(devdiag_http_duration_seconds_bucket[5m]))
histogram_quantile(0.99, rate(devdiag_http_duration_seconds_bucket[5m]))

# 503 spike detection
delta(devdiag_http_errors_total{code="503"}[5m]) > 5

# Capacity utilization (requests vs limit)
sum(rate(devdiag_http_requests_total{path="/diag/run"}[1m])) / devdiag_http_max_concurrent
```

### LogQL Queries (Grafana Loki)

```logql
# All DevDiag logs
{container_name="infra-devdiag-http-1"}

# Errors only
{container_name="infra-devdiag-http-1"} | json | event="http_error"

# Specific request ID
{container_name="infra-devdiag-http-1"} | json | rid="550e8400-e29b-41d4-a716-446655440000"

# Slow requests (>10s)
{container_name="infra-devdiag-http-1"} | json | ms > 10000

# 429 rate limit hits
{container_name="infra-devdiag-http-1"} | json | status="429"

# Filter by tenant (via path inspection or custom logging)
{container_name="infra-devdiag-http-1"} | json | path="/diag/run"
```

## Runbook Links

- **Service Down**: [TROUBLESHOOTING.md#service-down](./TROUBLESHOOTING.md#service-down)
- **Capacity Issues**: [TROUBLESHOOTING.md#capacity-saturation](./TROUBLESHOOTING.md#capacity-saturation)
- **High Latency**: [TROUBLESHOOTING.md#high-latency](./TROUBLESHOOTING.md#high-latency)
- **JWT Errors**: [JWT_SETUP.md#troubleshooting](./JWT_SETUP.md#troubleshooting)

## Testing Alerts

### Manual Alert Trigger

```bash
# Stop service to trigger DevDiagServiceDown
docker compose -f infra/docker-compose.devdiag.yml stop

# Wait 5 minutes, verify alert fires

# Restart service
docker compose -f infra/docker-compose.devdiag.yml start

# Trigger rate limit (429) - rapid requests
for i in {1..100}; do
  curl -X POST https://devdiag.leoklemet.com/diag/run \
    -H "Authorization: Bearer $JWT" \
    -H "Content-Type: application/json" \
    -d '{"url":"https://applylens.app","preset":"app"}' &
done

# Trigger capacity (503) - saturate MAX_CONCURRENT
# Set MAX_CONCURRENT=1, then send 10 concurrent requests

# Trigger latency - use slow target with long timeout
curl -X POST https://devdiag.leoklemet.com/diag/run \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://extremely-slow-site.example.com","preset":"full"}'
```

## Next Steps

1. **Deploy Prometheus alerts**: Copy `devdiag_alerts.yml` to Prometheus
2. **Import Grafana dashboard**: Use JSON template or create via UI
3. **Configure notification channels**: Slack, email, or PagerDuty
4. **Verify log aggregation**: Ensure x-request-id present in all logs
5. **Test alert triggers**: Manually trigger each alert to verify routing
6. **Document runbooks**: Create detailed troubleshooting guides
