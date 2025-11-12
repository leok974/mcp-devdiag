# Kubernetes Deployment for DevDiag HTTP

## Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: devdiag-http
  namespace: ops
  labels:
    app: devdiag-http
spec:
  replicas: 2
  selector:
    matchLabels:
      app: devdiag-http
  template:
    metadata:
      labels:
        app: devdiag-http
    spec:
      containers:
        - name: devdiag-http
          image: ghcr.io/leok974/mcp-devdiag/devdiag-http:latest
          ports:
            - name: http
              containerPort: 8080
              protocol: TCP
          env:
            - name: JWKS_URL
              value: "https://your-idp.com/.well-known/jwks.json"
            - name: JWT_AUD
              value: "mcp-devdiag"
            - name: RATE_LIMIT_RPS
              value: "5"
            - name: ALLOW_PRIVATE_IP
              value: "0"
            - name: ALLOWED_ORIGINS
              value: "https://evalforge.app,https://app.ledger-mind.org"
            - name: ALLOW_TARGET_HOSTS
              value: ".ledger-mind.org,app.example.com"
            - name: DEVDIAG_CLI
              value: "mcp-devdiag"
            - name: DEVDIAG_TIMEOUT_S
              value: "180"
            - name: MAX_CONCURRENT
              value: "3"
          resources:
            requests:
              cpu: "200m"
              memory: "512Mi"
            limits:
              cpu: "1000m"
              memory: "2Gi"
          livenessProbe:
            httpGet:
              path: /healthz
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 30
            timeoutSeconds: 5
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /ready
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 3
          startupProbe:
            httpGet:
              path: /ready
              port: 8080
            initialDelaySeconds: 0
            periodSeconds: 5
            timeoutSeconds: 5
            failureThreshold: 12
---
apiVersion: v1
kind: Service
metadata:
  name: devdiag-http
  namespace: ops
  labels:
    app: devdiag-http
spec:
  type: ClusterIP
  ports:
    - port: 80
      targetPort: 8080
      protocol: TCP
      name: http
  selector:
    app: devdiag-http
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: devdiag-http
  namespace: ops
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/rate-limit: "10"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - devdiag.example.com
      secretName: devdiag-http-tls
  rules:
    - host: devdiag.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: devdiag-http
                port:
                  number: 80
```

## ConfigMap for Environment Variables

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: devdiag-http-config
  namespace: ops
data:
  JWKS_URL: "https://your-idp.com/.well-known/jwks.json"
  JWT_AUD: "mcp-devdiag"
  RATE_LIMIT_RPS: "5"
  ALLOW_PRIVATE_IP: "0"
  ALLOWED_ORIGINS: "https://evalforge.app,https://app.ledger-mind.org"
  ALLOW_TARGET_HOSTS: ".ledger-mind.org,app.example.com"
  DEVDIAG_CLI: "mcp-devdiag"
  DEVDIAG_TIMEOUT_S: "180"
  MAX_CONCURRENT: "3"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: devdiag-http
  namespace: ops
spec:
  # ... (same as above)
  template:
    spec:
      containers:
        - name: devdiag-http
          # ... (same as above)
          envFrom:
            - configMapRef:
                name: devdiag-http-config
```

## Horizontal Pod Autoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: devdiag-http
  namespace: ops
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: devdiag-http
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

## ServiceMonitor (Prometheus Operator)

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: devdiag-http
  namespace: ops
  labels:
    app: devdiag-http
spec:
  selector:
    matchLabels:
      app: devdiag-http
  endpoints:
    - port: http
      path: /metrics
      interval: 30s
      scrapeTimeout: 10s
```

## PrometheusRule (Alerts)

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: devdiag-http-alerts
  namespace: ops
spec:
  groups:
    - name: devdiag
      interval: 30s
      rules:
        - alert: DevDiagDown
          expr: devdiag_http_up == 0
          for: 5m
          labels:
            severity: critical
          annotations:
            summary: "DevDiag HTTP is down"
            description: "DevDiag HTTP has been down for more than 5 minutes."
        
        - alert: DevDiagNotReady
          expr: up{job="devdiag-http"} == 0
          for: 2m
          labels:
            severity: warning
          annotations:
            summary: "DevDiag HTTP not ready"
            description: "DevDiag HTTP readiness probe failing."
        
        - alert: DevDiagHighConcurrency
          expr: devdiag_http_concurrent_runs >= devdiag_http_max_concurrent * 0.9
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "DevDiag HTTP high concurrency"
            description: "DevDiag HTTP at {{ $value }} concurrent runs (limit: {{ devdiag_http_max_concurrent }})."
```

## Network Policy (Optional)

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: devdiag-http
  namespace: ops
spec:
  podSelector:
    matchLabels:
      app: devdiag-http
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: ingress-nginx
      ports:
        - protocol: TCP
          port: 8080
  egress:
    # Allow DNS
    - to:
        - namespaceSelector:
            matchLabels:
              name: kube-system
      ports:
        - protocol: UDP
          port: 53
    # Allow HTTPS to JWKS endpoint and target URLs
    - to:
        - podSelector: {}
      ports:
        - protocol: TCP
          port: 443
        - protocol: TCP
          port: 80
```

## Deployment Commands

```bash
# Apply all resources
kubectl apply -f devdiag-http-k8s.yaml

# Check deployment status
kubectl -n ops get pods -l app=devdiag-http

# Check readiness
kubectl -n ops get pods -l app=devdiag-http -o jsonpath='{.items[*].status.conditions[?(@.type=="Ready")].status}'

# Test endpoints
kubectl -n ops port-forward svc/devdiag-http 8080:80
curl http://localhost:8080/healthz
curl http://localhost:8080/selfcheck
curl http://localhost:8080/ready

# View logs
kubectl -n ops logs -l app=devdiag-http -f

# Scale manually
kubectl -n ops scale deployment devdiag-http --replicas=5
```

## Troubleshooting

**Pods not ready:**
```bash
# Check readiness probe
kubectl -n ops describe pod <pod-name> | grep -A 10 Readiness

# Check /ready endpoint
kubectl -n ops exec <pod-name> -- curl -s http://localhost:8080/ready | jq .
```

**502 errors:**
```bash
# Check /selfcheck
kubectl -n ops exec <pod-name> -- curl -s http://localhost:8080/selfcheck | jq .
```

**High memory usage:**
```bash
# Check if Playwright browsers are installed
kubectl -n ops exec <pod-name> -- du -sh /root/.cache/ms-playwright

# Increase memory limits if needed
```
