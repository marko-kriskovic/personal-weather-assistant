#!/usr/bin/env bash
# Smoke-test a running server against the real OpenWeatherMap and Groq APIs.
# Usage: scripts/manual_test.sh [city] [date YYYY-MM-DD] [base_url]
set -euo pipefail

CITY="${1:-Zagreb}"
DATE="${2:-$(date -u -d tomorrow +%F 2>/dev/null || date -u -v+1d +%F)}"
BASE_URL="${3:-http://localhost:8000}"

pretty() { if command -v jq >/dev/null; then jq .; else python3 -m json.tool; fi; }

echo "== GET /health"
curl -sS "$BASE_URL/health" | pretty

echo
echo "== GET /api/v1/weather ($CITY, $DATE)"
curl -sS -G "$BASE_URL/api/v1/weather" --data-urlencode "city=$CITY" --data-urlencode "date=$DATE" | pretty

echo
echo "== POST /api/v1/recommendations ($CITY, $DATE)"
curl -sS -X POST "$BASE_URL/api/v1/recommendations" \
  -H "Content-Type: application/json" \
  -d "{\"city\": \"$CITY\", \"date\": \"$DATE\"}" | pretty
