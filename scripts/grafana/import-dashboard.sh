#!/usr/bin/env bash
# Import DevDiag Analytics dashboard to Grafana
# Requires: GRAFANA_URL, GRAFANA_API_KEY environment variables

set -euo pipefail

: "${GRAFANA_URL:?Missing GRAFANA_URL}"
: "${GRAFANA_API_KEY:?Missing GRAFANA_API_KEY}"

DASH_PATH="${1:-deployments/grafana/dashboards/devdiag-analytics.json}"
[ -f "$DASH_PATH" ] || { echo "Dashboard JSON not found: $DASH_PATH" >&2; exit 1; }

# Force Grafana to treat as new / update by clearing id and ensuring overwrite
DASH=$(jq '.dashboard.id=null | .overwrite=true' \
        --argfile dashboard "$DASH_PATH" \
        -n '{dashboard:$dashboard, folderId:0, overwrite:true}')

echo "→ Importing dashboard from $DASH_PATH"
curl -sfS -X POST "$GRAFANA_URL/api/dashboards/db" \
  -H "Authorization: Bearer $GRAFANA_API_KEY" \
  -H "Content-Type: application/json" \
  --data-raw "$DASH" | jq -r '"✓ "+.status+": "+.slug'
