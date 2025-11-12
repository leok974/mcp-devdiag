# JWT Service Tokens Setup

## Overview

Each tenant (applylens, ledgermind, portfolio) needs a service JWT for backend-to-DevDiag communication.

## Token Requirements

- **Audience (`aud`)**: `mcp-devdiag`
- **Subject (`sub`)**: `svc:<tenant>` (e.g., `svc:applylens`, `svc:ledgermind`, `svc:portfolio`)
- **Issuer (`iss`)**: Your auth domain (e.g., `https://auth.leoklemet.com`)
- **Expiration (`exp`)**: Short-lived (recommended: 1-7 days for rotation)
- **Algorithm**: RS256 (asymmetric signing)

## Minting Tokens

### Using jose CLI (Node.js)

```bash
npm install -g node-jose-tools

# Generate token for applylens
jose sign \
  --key private-key.pem \
  --alg RS256 \
  --iss https://auth.leoklemet.com \
  --aud mcp-devdiag \
  --sub svc:applylens \
  --exp $(date -d '+7 days' +%s)

# Generate token for ledgermind
jose sign \
  --key private-key.pem \
  --alg RS256 \
  --iss https://auth.leoklemet.com \
  --aud mcp-devdiag \
  --sub svc:ledgermind \
  --exp $(date -d '+7 days' +%s)

# Generate token for portfolio
jose sign \
  --key private-key.pem \
  --alg RS256 \
  --iss https://auth.leoklemet.com \
  --aud mcp-devdiag \
  --sub svc:portfolio \
  --exp $(date -d '+7 days' +%s)
```

### Using PyJWT (Python)

```python
import jwt
from datetime import datetime, timedelta
from pathlib import Path

# Load private key
private_key = Path("private-key.pem").read_text()

# Token payload
def generate_token(tenant: str, days: int = 7):
    payload = {
        "iss": "https://auth.leoklemet.com",
        "aud": "mcp-devdiag",
        "sub": f"svc:{tenant}",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(days=days)
    }
    
    token = jwt.encode(payload, private_key, algorithm="RS256")
    return token

# Generate tokens
applylens_token = generate_token("applylens")
ledgermind_token = generate_token("ledgermind")
portfolio_token = generate_token("portfolio")

print(f"APPLYLENS_DEVDIAG_JWT={applylens_token}")
print(f"LEDGERMIND_DEVDIAG_JWT={ledgermind_token}")
print(f"PORTFOLIO_DEVDIAG_JWT={portfolio_token}")
```

### Using Auth0 Management API

```bash
# Get M2M token for each tenant
curl -X POST https://auth.leoklemet.com/oauth/token \
  -H 'content-type: application/json' \
  -d '{
    "client_id": "APPLYLENS_CLIENT_ID",
    "client_secret": "APPLYLENS_CLIENT_SECRET",
    "audience": "mcp-devdiag",
    "grant_type": "client_credentials"
  }'
```

## Storing Tokens

### GitHub Actions Secrets (per repository)

For each tenant repository (applylens, ledger-mind, portfolio):

1. Navigate to **Settings → Secrets and variables → Actions**
2. Add repository secret:
   - **Name**: `DEVDIAG_JWT`
   - **Value**: `<generated_jwt_token>`

### Example GitHub Actions Workflow

```yaml
name: DevDiag Check
on: [pull_request]

jobs:
  devdiag:
    runs-on: ubuntu-latest
    steps:
      - name: Run DevDiag
        run: |
          curl -X POST https://devdiag.leoklemet.com/diag/run \
            -H "Authorization: Bearer ${{ secrets.DEVDIAG_JWT }}" \
            -H "Content-Type: application/json" \
            -d '{
              "url": "https://pr-${{ github.event.pull_request.number }}.applylens.app",
              "preset": "app",
              "tenant": "applylens"
            }'
```

### Environment Variables (local dev)

```bash
# .env.local (applylens backend)
DEVDIAG_JWT=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...

# .env.local (ledgermind backend)
DEVDIAG_JWT=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...

# .env.local (portfolio backend)
DEVDIAG_JWT=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Token Rotation

### Automated Rotation (Recommended)

Set up a cron job or scheduled GitHub Action to rotate tokens weekly:

```yaml
# .github/workflows/rotate-devdiag-jwt.yml
name: Rotate DevDiag JWT
on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sunday
  workflow_dispatch:

jobs:
  rotate:
    runs-on: ubuntu-latest
    steps:
      - name: Generate new token
        id: generate
        run: |
          # Use PyJWT or jose to generate token
          NEW_TOKEN=$(python generate_token.py applylens)
          echo "::add-mask::$NEW_TOKEN"
          echo "token=$NEW_TOKEN" >> $GITHUB_OUTPUT
      
      - name: Update secret
        uses: actions/github-script@v7
        with:
          script: |
            await github.rest.actions.createOrUpdateRepoSecret({
              owner: context.repo.owner,
              repo: context.repo.repo,
              secret_name: 'DEVDIAG_JWT',
              encrypted_value: '${{ steps.generate.outputs.token }}'
            })
```

### Manual Rotation

1. Generate new token (see above)
2. Update GitHub secret or env var
3. Old token expires automatically after 7 days

## Verification

### Test Token Validity

```bash
# Decode JWT to check claims (without verification)
echo "$DEVDIAG_JWT" | cut -d. -f2 | base64 -d | jq .

# Expected output:
{
  "iss": "https://auth.leoklemet.com",
  "aud": "mcp-devdiag",
  "sub": "svc:applylens",
  "iat": 1731427200,
  "exp": 1732032000
}
```

### Test API Call

```bash
# Set tenant-specific token
export DEVDIAG_JWT="eyJhbGci..."

# Test applylens
curl -X POST https://devdiag.leoklemet.com/diag/run \
  -H "Authorization: Bearer $DEVDIAG_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://applylens.app",
    "preset": "app",
    "tenant": "applylens"
  }' | jq .

# Test ledgermind
curl -X POST https://devdiag.leoklemet.com/diag/run \
  -H "Authorization: Bearer $DEVDIAG_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://app.ledger-mind.org",
    "preset": "app",
    "tenant": "ledgermind"
  }' | jq .
```

## Troubleshooting

### 401 Unauthorized

**Cause:** Invalid JWT signature or expired token

**Fix:**
1. Check token expiration: `echo "$TOKEN" | cut -d. -f2 | base64 -d | jq .exp`
2. Verify JWKS_URL is accessible: `curl -s https://auth.leoklemet.com/.well-known/jwks.json`
3. Ensure `kid` in JWT header matches JWKS key ID

### 422 Validation Error (host not allowed)

**Cause:** URL host doesn't match tenant allowlist

**Fix:**
1. Check TENANT_ALLOW_HOSTS_JSON in infra/.env.devdiag.infra
2. Verify tenant name matches (case-sensitive)
3. Ensure host pattern includes subdomain (use `.applylens.app` for wildcards)

### Token Claims Mismatch

**Required Claims:**
```json
{
  "aud": "mcp-devdiag",        // MUST match JWT_AUD env var
  "sub": "svc:applylens",      // MUST start with "svc:"
  "iss": "https://auth...",    // MUST match JWKS issuer
  "exp": 1732032000            // MUST be future timestamp
}
```

## Security Best Practices

1. **Short-lived tokens**: Max 7 days, ideally 1-3 days
2. **Automated rotation**: Use CI/CD to rotate weekly
3. **Separate tokens per tenant**: Never share tokens across tenants
4. **Secrets management**: Use GitHub Secrets, not .env files in repos
5. **HTTPS only**: Never transmit tokens over HTTP
6. **Logging**: Tokens are automatically redacted in logs (masked)

## Per-Tenant Configuration

### ApplyLens
- **Tenant ID**: `applylens`
- **Subject**: `svc:applylens`
- **Allowlist**: `["applylens.app", ".applylens.app", "api.applylens.app"]`
- **Use case**: PR previews (`pr-123.applylens.app`)

### LedgerMind
- **Tenant ID**: `ledgermind`
- **Subject**: `svc:ledgermind`
- **Allowlist**: `[".ledger-mind.org", "app.ledger-mind.org", "api.ledger-mind.org"]`
- **Use case**: Production + staging environments

### Portfolio
- **Tenant ID**: `portfolio`
- **Subject**: `svc:portfolio`
- **Allowlist**: `[".leoklemet.com", "www.leoklemet.com"]`
- **Use case**: Personal website diagnostics

## Next Steps

1. Generate tokens for all three tenants
2. Store in respective GitHub repositories as `DEVDIAG_JWT`
3. Test each tenant with sample request
4. Set up automated rotation (optional but recommended)
5. Monitor JWT expiration in Grafana (add custom alert)
