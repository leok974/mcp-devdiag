#!/usr/bin/env bash
# Import DevDiag alert rules to Grafana
# Requires: GRAFANA_URL, GRAFANA_API_KEY environment variables

set -euo pipefail

: "${GRAFANA_URL:?Missing GRAFANA_URL}"
: "${GRAFANA_API_KEY:?Missing GRAFANA_API_KEY}"

ALERTS_DIR="${1:-deployments/grafana/alerts}"
FOLDER_UID="devdiag-alerts"
FOLDER_TITLE="DevDiag Alerts"

echo "→ Ensuring alert folder '$FOLDER_TITLE' exists…"

# Create folder if doesn't exist
set +e
curl -sfS -H "Authorization: Bearer $GRAFANA_API_KEY" \
  "$GRAFANA_URL/api/folders/$FOLDER_UID" >/dev/null 2>&1
folder_exists=$?
set -e

if [ $folder_exists -ne 0 ]; then
  echo "• Creating folder"
  curl -sfS -X POST "$GRAFANA_URL/api/folders" \
    -H "Authorization: Bearer $GRAFANA_API_KEY" \
    -H "Content-Type: application/json" \
    --data-raw "{\"uid\":\"$FOLDER_UID\",\"title\":\"$FOLDER_TITLE\"}" | jq -r '.uid'
else
  echo "✓ Folder exists"
fi

echo ""
echo "→ Importing alert rules from $ALERTS_DIR..."

# Import each alert JSON file
for alert_file in "$ALERTS_DIR"/*.json; do
  [ -f "$alert_file" ] || continue
  
  alert_name=$(basename "$alert_file" .json)
  echo "  • Importing: $alert_name"
  
  # Read alert JSON
  alert_data=$(cat "$alert_file")
  
  # Wrap in alert rule group payload
  payload=$(jq -n \
    --arg title "$alert_name" \
    --arg folderUID "$FOLDER_UID" \
    --argjson alert "$alert_data" \
    '{
      name: $title,
      interval: "1m",
      rules: [$alert]
    }')
  
  # POST to Grafana (provisioning/alerting/*/rule endpoint for Grafana 9+)
  curl -sfS -X POST "$GRAFANA_URL/api/v1/provisioning/alert-rules" \
    -H "Authorization: Bearer $GRAFANA_API_KEY" \
    -H "Content-Type: application/json" \
    -H "X-Disable-Provenance: true" \
    --data-raw "$payload" | jq -r '.uid // .message' || echo "  ⚠️  May already exist or need update"
done

echo ""
echo "✓ Alert import complete"
echo "  View at: $GRAFANA_URL/alerting/list"
