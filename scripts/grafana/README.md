# Grafana Import Scripts

Automated scripts to import DevDiag PostgreSQL datasource and analytics dashboard to Grafana.

## Quick Start

### Prerequisites

- Grafana instance (local, cloud, or self-hosted)
- Grafana API token with Editor or Admin role
- PostgreSQL database with DevDiag schema
- `jq` installed (for bash scripts)

### 1. Set Environment Variables

**Linux/macOS:**
```bash
export GRAFANA_URL="http://localhost:3000"
export GRAFANA_API_KEY="your_grafana_api_token"
export DEVDIAG_PG_HOST="localhost:5432"
export DEVDIAG_PG_USER="grafana"
export DEVDIAG_PG_PASS="StrongGrafanaPass!"
export DEVDIAG_PG_DB="devdiag"
```

**Windows PowerShell:**
```powershell
$env:GRAFANA_URL="http://localhost:3000"
$env:GRAFANA_API_KEY="your_grafana_api_token"
$env:DEVDIAG_PG_HOST="localhost:5432"
$env:DEVDIAG_PG_USER="grafana"
$env:DEVDIAG_PG_PASS="StrongGrafanaPass!"
$env:DEVDIAG_PG_DB="devdiag"
```

### 2. Import Everything (One Command)

**Using Make:**
```bash
make grafana.import
```

**Manual (Linux/macOS):**
```bash
chmod +x scripts/grafana/*.sh
./scripts/grafana/import-datasource.sh
./scripts/grafana/import-dashboard.sh
```

**Manual (Windows):**
```powershell
.\scripts\grafana\import-datasource.ps1
.\scripts\grafana\import-dashboard.ps1
```

---

## Script Reference

### `import-datasource.sh` / `import-datasource.ps1`

Creates or updates the "DevDiag Postgres" datasource in Grafana.

**Features:**
- Idempotent: safe to run multiple times
- Checks if datasource exists (uid: `devdiag-postgres`)
- Updates if exists, creates if doesn't
- Uses read-only `grafana` database user

**Usage:**
```bash
# Bash
./scripts/grafana/import-datasource.sh

# PowerShell
.\scripts\grafana\import-datasource.ps1
```

**Output:**
```
→ Ensuring datasource 'DevDiag Postgres' (uid=devdiag-postgres) exists…
✓ Found — updating datasource
Datasource updated
✓ Datasource ready.
```

---

### `import-dashboard.sh` / `import-dashboard.ps1`

Imports the DevDiag Analytics dashboard to Grafana.

**Features:**
- Overwrites existing dashboard (safe updates)
- Places dashboard in "General" folder (folderId: 0)
- References `devdiag-postgres` datasource by UID
- Returns dashboard URL

**Usage:**
```bash
# Bash (default path)
./scripts/grafana/import-dashboard.sh

# Bash (custom path)
./scripts/grafana/import-dashboard.sh path/to/dashboard.json

# PowerShell
.\scripts\grafana\import-dashboard.ps1
```

**Output:**
```
→ Importing dashboard from deployments/grafana/dashboards/devdiag-analytics.json
✓ success: devdiag-analytics
  Dashboard URL: http://localhost:3000/d/devdiag-analytics
```

---

## Grafana API Token Setup

### 1. Create API Key

1. Go to Grafana → **Administration** → **Service accounts**
2. Click **Add service account**
3. Name: `DevDiag Import`
4. Role: **Editor** or **Admin**
5. Click **Add service account token**
6. Copy the token (starts with `glsa_`)

### 2. Test Token

```bash
curl -H "Authorization: Bearer $GRAFANA_API_KEY" \
  "$GRAFANA_URL/api/org"
```

Should return org details (not 401/403).

---

## Makefile Targets

```bash
make grafana.import       # Import datasource + dashboard
make grafana.datasource   # Import only datasource
make grafana.dashboard    # Import only dashboard
```

---

## GitHub Actions (CI/CD)

The workflow `.github/workflows/grafana-import.yml` automatically imports dashboards on changes.

### Setup Secrets

In GitHub repository settings → **Secrets and variables** → **Actions**, add:

| Secret Name | Example Value |
|------------|---------------|
| `GRAFANA_URL` | `https://your-org.grafana.net` |
| `GRAFANA_API_KEY` | `glsa_ABC123...` |
| `DEVDIAG_PG_HOST` | `db.example.com:5432` |
| `DEVDIAG_PG_USER` | `grafana` |
| `DEVDIAG_PG_PASS` | `YourPassword` |
| `DEVDIAG_PG_DB` | `devdiag` |

### Trigger Workflow

**Automatically:**
- Push changes to `deployments/grafana/dashboards/*.json`
- Push changes to `scripts/grafana/*.sh`

**Manually:**
- Go to **Actions** → **Grafana Import** → **Run workflow**

---

## Troubleshooting

### ❌ 401 Unauthorized

**Problem:** Invalid or expired API token

**Solution:**
1. Verify token: `echo $GRAFANA_API_KEY`
2. Check token hasn't expired in Grafana
3. Ensure token has Editor/Admin role
4. Test: `curl -H "Authorization: Bearer $GRAFANA_API_KEY" "$GRAFANA_URL/api/org"`

---

### ❌ 403 Forbidden

**Problem:** API token lacks permissions

**Solution:**
1. Go to Grafana → Service accounts
2. Find your token's service account
3. Change role to **Editor** or **Admin**
4. Try again

---

### ❌ Connection refused

**Problem:** Grafana URL incorrect or Grafana not running

**Solution:**
1. Check Grafana is running: `curl $GRAFANA_URL/api/health`
2. Verify URL (no trailing slash): `http://localhost:3000`
3. For Grafana Cloud: Use `https://YOUR_SUBDOMAIN.grafana.net`

---

### ❌ jq: command not found

**Problem:** `jq` not installed (required for bash scripts)

**Solution:**
```bash
# Ubuntu/Debian
sudo apt-get install jq

# macOS
brew install jq

# Windows (use PowerShell scripts instead)
# Or install jq via chocolatey: choco install jq
```

---

### ❌ Dashboard import fails with "datasource not found"

**Problem:** Datasource UID mismatch

**Solution:**
1. Import datasource first: `./scripts/grafana/import-datasource.sh`
2. Verify UID: `curl -H "Authorization: Bearer $GRAFANA_API_KEY" "$GRAFANA_URL/api/datasources/uid/devdiag-postgres"`
3. Dashboard expects UID: `devdiag-postgres`

---

### ❌ PowerShell: Invoke-RestMethod fails with SSL error

**Problem:** Self-signed certificate or SSL validation

**Solution:**
```powershell
# Disable SSL validation (development only!)
[System.Net.ServicePointManager]::ServerCertificateValidationCallback = {$true}

# Or fix certificate chain
```

---

## Advanced Usage

### One-Liner Import (Bash)

**Create/update datasource:**
```bash
curl -s -H "Authorization: Bearer $GRAFANA_API_KEY" \
  "$GRAFANA_URL/api/datasources/uid/devdiag-postgres" \
  || curl -s -X POST "$GRAFANA_URL/api/datasources" \
     -H "Authorization: Bearer $GRAFANA_API_KEY" \
     -H "Content-Type: application/json" \
     --data-raw "{
       \"name\":\"DevDiag Postgres\",
       \"type\":\"postgres\",
       \"uid\":\"devdiag-postgres\",
       \"access\":\"proxy\",
       \"url\":\"$DEVDIAG_PG_HOST\",
       \"user\":\"$DEVDIAG_PG_USER\",
       \"secureJsonData\":{\"password\":\"$DEVDIAG_PG_PASS\"},
       \"jsonData\":{\"database\":\"$DEVDIAG_PG_DB\",\"sslmode\":\"disable\",\"postgresVersion\":1600}
     }"
```

**Import dashboard:**
```bash
jq '.dashboard.id=null | .overwrite=true' \
  --argfile dashboard deployments/grafana/dashboards/devdiag-analytics.json \
  -n '{dashboard:$dashboard, folderId:0, overwrite:true}' \
| curl -s -X POST "$GRAFANA_URL/api/dashboards/db" \
  -H "Authorization: Bearer $GRAFANA_API_KEY" \
  -H "Content-Type: application/json" \
  --data-binary @- | jq
```

---

### Custom Dashboard Folder

To import to a specific folder instead of "General":

1. Get folder UID:
```bash
curl -H "Authorization: Bearer $GRAFANA_API_KEY" \
  "$GRAFANA_URL/api/folders" | jq
```

2. Modify script:
```bash
# In import-dashboard.sh, change:
DASH=$(jq '.dashboard.id=null | .overwrite=true' \
        --argfile dashboard "$DASH_PATH" \
        --arg folderUid "YOUR_FOLDER_UID" \
        -n '{dashboard:$dashboard, folderUid:$folderUid, overwrite:true}')
```

---

### Grafana Cloud

For Grafana Cloud instances:

1. Use full URL:
```bash
export GRAFANA_URL="https://YOUR_SUBDOMAIN.grafana.net"
```

2. Create API token (Cloud Admin required):
   - https://YOUR_SUBDOMAIN.grafana.net/org/apikeys

3. Database host must be publicly accessible or use Grafana Cloud Agent

---

## Files

| File | Purpose |
|------|---------|
| `import-datasource.sh` | Bash script to import datasource |
| `import-datasource.ps1` | PowerShell script to import datasource |
| `import-dashboard.sh` | Bash script to import dashboard |
| `import-dashboard.ps1` | PowerShell script to import dashboard |
| `README.md` | This file |

---

## See Also

- [Grafana HTTP API Documentation](https://grafana.com/docs/grafana/latest/developers/http_api/)
- [DevDiag Grafana Setup Guide](../../deployments/grafana/SETUP.md)
- [DevDiag Alert Queries](../../deployments/grafana/ALERT_QUERIES.md)
- [Analytics Warehouse Documentation](../../docs/ANALYTICS_WAREHOUSE.md)

---

## Support

- **Issues:** https://github.com/leok974/mcp-devdiag/issues
- **Discussions:** https://github.com/leok974/mcp-devdiag/discussions
- **Documentation:** https://github.com/leok974/mcp-devdiag/tree/main/docs
