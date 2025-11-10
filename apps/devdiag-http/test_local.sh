#!/bin/bash
# Quick local smoke test for devdiag-http server
# Run after: pip install -r requirements.txt && uvicorn main:app --reload --port 8080

set -e

BASE="http://127.0.0.1:8080"

echo "🔍 Testing DevDiag HTTP Server..."
echo ""

echo "1️⃣ Health check..."
curl -sf "$BASE/healthz" | jq .
echo "✅ Health check passed"
echo ""

echo "2️⃣ Probe presets..."
curl -sf "$BASE/probes" | jq .
echo "✅ Presets check passed"
echo ""

echo "3️⃣ Full diagnostic run..."
curl -sf -X POST "$BASE/diag/run" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.leoklemet.com","preset":"app"}' | jq .ok
echo "✅ Diagnostic run passed"
echo ""

echo "🎉 All tests passed! Server is working correctly."
