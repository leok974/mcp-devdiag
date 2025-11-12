# Quick Rollout Checklist

Use this checklist to deploy the shared DevDiag infrastructure across all projects.

## Phase 1: Infrastructure Setup

- [ ] **Create network**
  ```bash
  docker network create infra_net
  ```

- [ ] **Copy env template**
  ```bash
  cd mcp-devdiag/infra
  cp .env.devdiag.infra.example .env.devdiag.infra
  ```

- [ ] **Configure .env.devdiag.infra**
  - [ ] Set `JWKS_URL` to your auth provider
  - [ ] Set `JWT_AUD` to `mcp-devdiag`
  - [ ] Verify `ALLOW_TARGET_HOSTS` includes all project domains
  - [ ] Verify `TENANT_ALLOW_HOSTS_JSON` tenant isolation

- [ ] **Deploy service**
  ```bash
  docker compose -f docker-compose.devdiag.yml up -d --pull always
  ```

- [ ] **Verify local access**
  ```bash
  curl -s http://127.0.0.1:8080/healthz | jq .
  curl -s http://127.0.0.1:8080/selfcheck | jq .
  curl -s http://127.0.0.1:8080/ready | jq .
  ```

## Phase 2: Cloudflare Tunnel

- [ ] **Add hostname to tunnel config**
  - Hostname: `devdiag.leoklemet.com`
  - Service: `http://devdiag-http:8080`
  - Network: `infra_net`

- [ ] **Restart tunnel**
  ```bash
  docker restart cloudflared  # or your tunnel container name
  ```

- [ ] **Verify external access**
  ```bash
  curl -s https://devdiag.leoklemet.com/healthz | jq .
  curl -s https://devdiag.leoklemet.com/selfcheck | jq .
  ```

## Phase 3: Observability

- [ ] **Add Prometheus scrape**
  - Target: `devdiag.leoklemet.com`
  - Path: `/metrics`
  - Interval: `30s`

- [ ] **Import Grafana dashboard**
  - Use template from `mcp-devdiag/dashboards/devdiag.json`
  - Or create custom panels for key metrics

- [ ] **Create alerts**
  - [ ] DevDiagDown (5min threshold)
  - [ ] DevDiagHighErrorRate (>0.5 req/s)
  - [ ] DevDiagConcurrencyLimit (>=MAX_CONCURRENT for 2min)

- [ ] **Test alerts**
  ```bash
  # Simulate down
  docker compose -f infra/docker-compose.devdiag.yml stop
  # Wait 5min, verify alert fires
  docker compose -f infra/docker-compose.devdiag.yml start
  ```

## Phase 4: ApplyLens Integration

- [ ] **Update backend .env**
  ```bash
  DEVDIAG_BASE=https://devdiag.leoklemet.com
  DEVDIAG_ENABLED=1
  DEVDIAG_TIMEOUT_S=120
  DEVDIAG_ALLOW_HOSTS=applylens.app,.applylens.app,api.applylens.app
  DEVDIAG_JWT=<service-account-jwt>
  ```

- [ ] **Create GitHub secret**
  - Secret name: `DEVDIAG_JWT`
  - Value: Service account JWT

- [ ] **Add CI workflow**
  - Copy from `infra/APPLYLENS_INTEGRATION.md`
  - Use HTTP path or MCP stdio path

- [ ] **Test backend proxy**
  ```bash
  curl -s -X POST http://localhost:8000/ops/diag \
    -H 'Content-Type: application/json' \
    -d '{"url":"https://applylens.app","preset":"app"}' | jq .
  ```

- [ ] **Trigger CI** - Create PR and verify workflow runs

## Phase 5: LedgerMind Integration

- [ ] **Update backend .env**
  ```bash
  DEVDIAG_BASE=https://devdiag.leoklemet.com
  DEVDIAG_ENABLED=1
  DEVDIAG_TIMEOUT_S=120
  DEVDIAG_ALLOW_HOSTS=.ledger-mind.org,app.ledger-mind.org,api.ledger-mind.org
  DEVDIAG_JWT=<service-account-jwt>
  ```

- [ ] **Create GitHub secret** (`DEVDIAG_JWT`)

- [ ] **Add CI workflow**

- [ ] **Test backend proxy**
  ```bash
  curl -s -X POST http://localhost:8000/ops/diag \
    -H 'Content-Type: application/json' \
    -d '{"url":"https://app.ledger-mind.org","preset":"app"}' | jq .
  ```

- [ ] **Trigger CI**

## Phase 6: Portfolio Integration

- [ ] **Update backend .env**
  ```bash
  DEVDIAG_BASE=https://devdiag.leoklemet.com
  DEVDIAG_ENABLED=1
  DEVDIAG_TIMEOUT_S=120
  DEVDIAG_ALLOW_HOSTS=.leoklemet.com,www.leoklemet.com
  DEVDIAG_JWT=<service-account-jwt>
  ```

- [ ] **Create GitHub secret** (`DEVDIAG_JWT`)

- [ ] **Add CI workflow**

- [ ] **Test backend proxy**
  ```bash
  curl -s -X POST http://localhost:8000/ops/diag \
    -H 'Content-Type: application/json' \
    -d '{"url":"https://www.leoklemet.com","preset":"app"}' | jq .
  ```

- [ ] **Trigger CI**

## Phase 7: End-to-End Testing

- [ ] **Test all tenants**
  ```bash
  export JWT="your-jwt-token"
  
  # ApplyLens
  curl -X POST https://devdiag.leoklemet.com/diag/run \
    -H "Authorization: Bearer $JWT" \
    -H "Content-Type: application/json" \
    -d '{"url":"https://applylens.app","preset":"app","tenant":"applylens"}' | jq .
  
  # LedgerMind
  curl -X POST https://devdiag.leoklemet.com/diag/run \
    -H "Authorization: Bearer $JWT" \
    -H "Content-Type: application/json" \
    -d '{"url":"https://app.ledger-mind.org","preset":"app","tenant":"ledgermind"}' | jq .
  
  # Portfolio
  curl -X POST https://devdiag.leoklemet.com/diag/run \
    -H "Authorization: Bearer $JWT" \
    -H "Content-Type: application/json" \
    -d '{"url":"https://www.leoklemet.com","preset":"app","tenant":"portfolio"}' | jq .
  ```

- [ ] **Verify tenant isolation**
  ```bash
  # This should fail (wrong tenant for URL)
  curl -X POST https://devdiag.leoklemet.com/diag/run \
    -H "Authorization: Bearer $JWT" \
    -H "Content-Type: application/json" \
    -d '{"url":"https://app.ledger-mind.org","tenant":"applylens"}' | jq .
  ```

- [ ] **Check Prometheus metrics**
  ```bash
  curl -s https://devdiag.leoklemet.com/metrics | grep devdiag_http
  ```

- [ ] **Verify Grafana dashboard** - Confirm data flowing

## Phase 8: Monitoring (24h Burn-In)

- [ ] **Monitor for 24 hours**
  - [ ] No alerts fired
  - [ ] Metrics stable
  - [ ] All CI workflows passing

- [ ] **Check logs for errors**
  ```bash
  docker compose -f infra/docker-compose.devdiag.yml logs --tail=100 devdiag-http | grep -i error
  ```

- [ ] **Review usage patterns**
  - Average requests/day
  - Peak concurrency
  - Error rate (<1%)

## Phase 9: Documentation

- [ ] **Update project READMEs**
  - [ ] ApplyLens - Link to DevDiag integration docs
  - [ ] LedgerMind - Link to DevDiag integration docs
  - [ ] Portfolio - Link to DevDiag integration docs

- [ ] **Create runbook**
  - Common issues & solutions
  - Rollback procedure
  - Capacity planning notes

- [ ] **Share knowledge**
  - Team notification
  - Slack/Discord announcement
  - Update onboarding docs

## Phase 10: Optimization (Optional)

- [ ] **Fine-tune capacity**
  - Adjust `MAX_CONCURRENT` based on usage
  - Adjust `RATE_LIMIT_RPS` if needed
  - Optimize `DEVDIAG_TIMEOUT_S`

- [ ] **Add caching** (if high volume)
  - Cache probe results for 1h
  - Reduce redundant probes

- [ ] **Enable autoscaling** (if needed)
  - Horizontal pod autoscaling (K8s)
  - Or multiple containers + load balancer

## Rollback Plan

If issues arise:

1. **Disable DevDiag in projects**
   ```bash
   # Set in each project's .env
   DEVDIAG_ENABLED=0
   ```

2. **Stop infrastructure service**
   ```bash
   docker compose -f infra/docker-compose.devdiag.yml down
   ```

3. **Revert CI workflows** - Remove or disable workflows

4. **Investigate & Fix** - Check logs, metrics, configs

5. **Re-deploy** when ready

## Success Criteria

✅ **Infrastructure:**
- Service running and healthy for 24h+
- No alerts fired
- Metrics flowing to Prometheus

✅ **Projects:**
- All backend proxies configured
- All CI workflows passing
- No port conflicts (MCP stdio usage unaffected)

✅ **Security:**
- Tenant isolation working
- Allowlists enforced
- Rate limits functional

✅ **Observability:**
- Dashboard populated with data
- Alerts configured and tested
- Logs accessible and searchable

## Post-Rollout

- [ ] **Monitor weekly** for first month
- [ ] **Review metrics monthly** for optimization
- [ ] **Update allowlists** as new domains added
- [ ] **Rotate JWT** quarterly (security best practice)
- [ ] **Keep service updated** - Pull new images monthly

## Questions?

- GitHub Issues: https://github.com/leok974/mcp-devdiag/issues
- Documentation: https://github.com/leok974/mcp-devdiag#readme
- Infrastructure README: `mcp-devdiag/infra/README.md`
