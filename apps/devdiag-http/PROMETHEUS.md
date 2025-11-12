# Prometheus Scrape Configuration for DevDiag HTTP

## Add to your prometheus.yml

```yaml
scrape_configs:
  - job_name: devdiag-http
    static_configs:
      - targets: ["devdiag-http.prod:443"]
    scheme: https
    metrics_path: /metrics
    scrape_interval: 30s
    scrape_timeout: 10s
```

## For local development (Docker Compose)

```yaml
scrape_configs:
  - job_name: devdiag-http-local
    static_configs:
      - targets: ["localhost:8080"]
    scheme: http
    metrics_path: /metrics
    scrape_interval: 15s
```

## Alert Rules

Add to your alerting rules file:

```yaml
groups:
  - name: devdiag
    rules:
      - alert: DevDiagDown
        expr: devdiag_http_up == 0
        for: 5m
        labels:
          severity: page
        annotations:
          summary: "DevDiag HTTP down"
          description: "No metrics reported for 5 minutes."
      
      - alert: DevDiagHighErrorRate
        expr: rate(devdiag_http_errors_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "DevDiag HTTP high error rate"
          description: "Error rate is {{ $value }} errors/sec over 5 minutes."
      
      - alert: DevDiagConcurrencyLimit
        expr: devdiag_http_concurrent_runs >= devdiag_http_max_concurrent
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "DevDiag HTTP at concurrency limit"
          description: "Server is at max concurrent runs ({{ $value }}). Consider scaling or increasing MAX_CONCURRENT."
```

## Grafana Dashboard Queries

### Request Rate
```promql
rate(devdiag_http_requests_total[5m])
```

### Error Rate
```promql
rate(devdiag_http_errors_total[5m])
```

### Availability (uptime %)
```promql
avg_over_time(devdiag_http_up[24h]) * 100
```

### Current Concurrency
```promql
devdiag_http_concurrent_runs
```

### Rate Limit Utilization
```promql
rate(devdiag_http_rate_limited_total[5m]) / devdiag_http_rate_limit_rps
```

## Current Metrics Exposed

The `/metrics` endpoint exposes:

- `devdiag_http_up` - 1 if server is healthy
- `devdiag_http_rate_limit_rps` - Configured rate limit (RPS)
- `devdiag_http_max_concurrent` - Max concurrent diagnostic runs

### Suggested Additional Metrics

If you want to extend metrics, add to `main.py`:

```python
from prometheus_client import Counter, Gauge, Histogram

# Request counter
requests_total = Counter('devdiag_http_requests_total', 'Total requests')
errors_total = Counter('devdiag_http_errors_total', 'Total errors')
rate_limited_total = Counter('devdiag_http_rate_limited_total', 'Total rate limited')

# Concurrent runs gauge
concurrent_runs = Gauge('devdiag_http_concurrent_runs', 'Current concurrent runs')

# Response time histogram
response_time = Histogram('devdiag_http_response_seconds', 'Response time')
```
