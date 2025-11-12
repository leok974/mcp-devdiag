# DevDiag HTTP Server - Troubleshooting Guide

## Quick Diagnostics

> **Quick Rule**: If `/healthz` is OK but `/diag/run` returns 502, check `/selfcheck` and `ALLOW_TARGET_HOSTS`.

### 1. Check Server Health

```bash
curl -s http://YOUR-SERVER:8080/healthz | jq .
```

**Expected**: `{"ok": true, "service": "devdiag-http", "version": "0.1.0"}`

**If it fails**: Server is down or unreachable

### 2. Check CLI Availability

```bash
curl -s http://YOUR-SERVER:8080/selfcheck | jq .
```

**Expected**: `{"ok": true, "cli": "mcp-devdiag", "version": "0.2.1"}`

**If `ok: false`**: 
- CLI not installed in container
- CLI not in PATH
- Wrong CLI name (check `DEVDIAG_CLI` env var)

**Fix**:
- Verify Dockerfile has `RUN pip install mcp-devdiag[playwright,export]`
- Check CLI name: `docker exec <container> which mcp-devdiag`
- Set `DEVDIAG_CLI` env var if using different binary name

### 3. Check Readiness (Production)

```bash
curl -s http://YOUR-SERVER:8080/ready | jq .
```

**Expected**: `{"ok": true}`

**If `ok: false`**:
- `"reason": "cli_missing"` - CLI not found (see selfcheck)
- `"reason": "allowlist_empty"` - `ALLOW_TARGET_HOSTS` not configured
- `"reason": "jwks_unreachable"` - Can't fetch JWKS from `JWKS_URL`

**Use case**: Use `/ready` for K8s readinessProbe to prevent traffic before server is fully configured.

## Common Errors

### 502 "DevDiag error" or "Non-JSON output"

**Symptom**: `/diag/run` returns 502

**Possible causes**:

1. **CLI not found**
   ```bash
   curl -s http://YOUR-SERVER:8080/selfcheck | jq .
   # {"ok": false, "message": "CLI not found in PATH"}
   ```
   **Fix**: Install CLI in container, verify PATH

2. **CLI crashes or times out**
   ```bash
   # Check logs for stderr output
   docker logs <container>
   ```
   **Fix**: Increase `DEVDIAG_TIMEOUT_S`, check target URL accessibility

3. **CLI returns non-JSON**
   ```bash
   # The error message will contain first 4000 chars of output
   ```
   **Fix**: Check CLI version compatibility, verify `--format json` works

### 504 "DevDiag timed out"

**Symptom**: Request takes >180s (default timeout)

**Causes**:
- Target URL is slow or unresponsive
- Complex preset (`full` preset is slower than `app`)
- Playwright browser launch overhead (first run)

**Fix**:
```bash
# Increase timeout
DEVDIAG_TIMEOUT_S=300

# Or use faster preset
{"url": "...", "preset": "chat"}  # lighter than "full"

# Pre-install browsers (add to Dockerfile):
RUN python -m playwright install --with-deps chromium
```

### 503 "Busy: concurrent runs at capacity"

**Symptom**: Too many simultaneous requests

**Cause**: `MAX_CONCURRENT` limit reached (default: 2)

**Fix**:
```bash
# Increase concurrency
MAX_CONCURRENT=5

# Or add delay between requests
```

### 400 "target host not allowed by server ALLOW_TARGET_HOSTS"

**Symptom**: URL rejected by server-side allowlist

**Cause**: Target URL hostname not in `ALLOW_TARGET_HOSTS`

**Fix**:
```bash
# Add exact host
ALLOW_TARGET_HOSTS=app.example.com

# Or subdomain wildcard
ALLOW_TARGET_HOSTS=.example.com

# Or glob pattern
ALLOW_TARGET_HOSTS=pr-*.example.com

# Multiple patterns
ALLOW_TARGET_HOSTS=.ledger-mind.org,app.example.com,pr-*.example.com
```

**Patterns**:
- `.example.com` - allows `example.com` and all `*.example.com`
- `app.example.com` - exact match only
- `pr-*.example.com` - glob match (e.g., `pr-123.example.com`)

### 400 "Refusing private/loopback/unknown host"

**Symptom**: SSRF protection blocking private IPs

**Cause**: Target URL resolves to private IP (10.x, 192.168.x, 127.x, etc.)

**Fix (local dev only)**:
```bash
ALLOW_PRIVATE_IP=1
```

**⚠️ Never set `ALLOW_PRIVATE_IP=1` in production** - this disables SSRF protection

### 429 "Rate limit exceeded"

**Symptom**: Too many requests from single client

**Cause**: Token bucket rate limiting (default: 2 RPS)

**Fix**:
```bash
# Increase rate limit
RATE_LIMIT_RPS=10

# Or add delay between requests (recommended)
```

### 401 "Invalid or expired token"

**Symptom**: JWT authentication failed

**Causes**:
1. **JWKS_URL not set or unreachable**
   ```bash
   # Check if JWKS is accessible
   curl -s $JWKS_URL
   ```

2. **JWT audience mismatch**
   ```bash
   # JWT has different audience than JWT_AUD
   JWT_AUD=your-audience-claim
   ```

3. **Expired JWT**
   - Check token expiration (`exp` claim)
   - Refresh token

**Fix**:
- Set `JWKS_URL` correctly
- Verify `JWT_AUD` matches token audience
- Disable auth for local dev: `JWKS_URL=`

## Debugging Checklist

**Step 1: Basic connectivity**
- [ ] `curl http://YOUR-SERVER:8080/healthz` returns 200
- [ ] Server logs show no errors

**Step 2: CLI availability**
- [ ] `curl http://YOUR-SERVER:8080/selfcheck` returns `{"ok": true}`
- [ ] CLI version matches expected version

**Step 3: Configuration**
- [ ] `ALLOW_TARGET_HOSTS` includes your target domain
- [ ] `DEVDIAG_TIMEOUT_S` is sufficient (180s default)
- [ ] `MAX_CONCURRENT` allows enough parallel requests
- [ ] `JWKS_URL` and `JWT_AUD` are correct (if using auth)

**Step 4: Test with known-good URL**
```bash
curl -s -X POST http://YOUR-SERVER:8080/diag/run \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com","preset":"chat"}' | jq .
```

**Step 5: Check logs**
```bash
docker logs <container> --tail 100 -f
```

Look for:
- CLI execution errors
- JSON parsing errors
- Rate limiting messages
- SSRF protection blocks

## Environment Variables Quick Reference

| Variable | Default | Purpose |
|----------|---------|---------|
| `JWKS_URL` | empty | JWT validation endpoint |
| `JWT_AUD` | `mcp-devdiag` | JWT audience claim |
| `RATE_LIMIT_RPS` | `2` | Requests per second |
| `ALLOW_PRIVATE_IP` | `0` | Allow private IPs (SSRF) |
| `ALLOWED_ORIGINS` | localhost | CORS origins |
| `ALLOW_TARGET_HOSTS` | empty | Server-side URL allowlist |
| `DEVDIAG_CLI` | `mcp-devdiag` | CLI binary name |
| `DEVDIAG_TIMEOUT_S` | `180` | CLI timeout (seconds) |
| `MAX_CONCURRENT` | `2` | Max parallel runs |

## Production Checklist

- [ ] `JWKS_URL` set to production IdP
- [ ] `JWT_AUD` matches your JWT audience
- [ ] `ALLOW_TARGET_HOSTS` restrictive (NOT empty or wildcard)
- [ ] `ALLOW_PRIVATE_IP=0` (SSRF protection enabled)
- [ ] `RATE_LIMIT_RPS` appropriate for traffic
- [ ] `MAX_CONCURRENT` tuned for server resources
- [ ] Health checks configured: `/healthz` (GET/HEAD)
- [ ] Monitoring enabled: `/metrics` endpoint
- [ ] Logs collected and searchable
- [ ] Browsers pre-installed (Dockerfile): `RUN python -m playwright install --with-deps chromium`

## Getting Help

1. **Check `/selfcheck` endpoint first** - most 502 errors are CLI-related
2. **Review logs** for detailed error messages
3. **Test with minimal config** - disable auth, use `chat` preset, test `example.com`
4. **Verify allowlists** - both `ALLOW_TARGET_HOSTS` (server) and backend proxy allowlists
5. **Check GitHub issues**: https://github.com/leok974/mcp-devdiag/issues
