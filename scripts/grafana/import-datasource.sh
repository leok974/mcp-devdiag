#!/usr/bin/env bash
# Import/update DevDiag PostgreSQL datasource in Grafana
# Requires: GRAFANA_URL, GRAFANA_API_KEY, DEVDIAG_PG_* environment variables

set -euo pipefail

: "${GRAFANA_URL:?Missing GRAFANA_URL}"
: "${GRAFANA_API_KEY:?Missing GRAFANA_API_KEY}"
: "${DEVDIAG_PG_HOST:?Missing DEVDIAG_PG_HOST}"   # host:port
: "${DEVDIAG_PG_USER:?Missing DEVDIAG_PG_USER}"
: "${DEVDIAG_PG_PASS:?Missing DEVDIAG_PG_PASS}"
: "${DEVDIAG_PG_DB:?Missing DEVDIAG_PG_DB}"

NAME="DevDiag Postgres"
UID="devdiag-postgres"

echo "→ Ensuring datasource '$NAME' (uid=$UID) exists…"
set +e
curl -sfS -H "Authorization: Bearer $GRAFANA_API_KEY" \
  "$GRAFANA_URL/api/datasources/uid/$UID" >/dev/null
exists=$?
set -e

payload=$(cat <<JSON
{
  "name": "$NAME",
  "type": "postgres",
  "uid": "$UID",
  "access": "proxy",
  "url": "$DEVDIAG_PG_HOST",
  "user": "$DEVDIAG_PG_USER",
  "secureJsonData": { "password": "$DEVDIAG_PG_PASS" },
  "jsonData": {
    "database": "$DEVDIAG_PG_DB",
    "sslmode": "disable",
    "postgresVersion": 1600,
    "timescaledb": false
  },
  "isDefault": false
}
JSON
)

if [ $exists -eq 0 ]; then
  echo "✓ Found — updating datasource"
  curl -sfS -X PUT "$GRAFANA_URL/api/datasources/uid/$UID" \
    -H "Authorization: Bearer $GRAFANA_API_KEY" \
    -H "Content-Type: application/json" \
    --data-raw "$payload" | jq -r '.message'
else
  echo "• Not found — creating datasource"
  curl -sfS -X POST "$GRAFANA_URL/api/datasources" \
    -H "Authorization: Bearer $GRAFANA_API_KEY" \
    -H "Content-Type: application/json" \
    --data-raw "$payload" | jq -r '.message'
fi
echo "✓ Datasource ready."
