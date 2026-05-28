#!/usr/bin/env bash
# Smoke-test POST /api/auth/login against a running API.
#
# Usage:
#   export LOGIN_TEST_EMAIL="you@example.com"
#   export LOGIN_TEST_PASSWORD="your-password"
#   ./scripts/smoke-login.sh
#
# Optional: API_URL=http://localhost:8000

set -euo pipefail

API_URL="${API_URL:-http://localhost:8000}"
EMAIL="${LOGIN_TEST_EMAIL:-}"
PASSWORD="${LOGIN_TEST_PASSWORD:-}"

if [[ -z "$EMAIL" || -z "$PASSWORD" ]]; then
  echo "Set LOGIN_TEST_EMAIL and LOGIN_TEST_PASSWORD to run the live smoke test."
  exit 1
fi

echo "POST ${API_URL}/api/auth/login"
response="$(curl -sS -w "\n%{http_code}" -X POST "${API_URL}/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}")"

body="${response%$'\n'*}"
status="${response##*$'\n'}"

echo "HTTP ${status}"
echo "${body}" | python3 -m json.tool

if [[ "${status}" != "200" ]]; then
  exit 1
fi

LOGIN_RESPONSE_BODY="${body}" python3 - <<'PY'
import json
import os

payload = json.loads(os.environ["LOGIN_RESPONSE_BODY"])
assert payload.get("authenticated"), "expected authenticated=true"
session = payload.get("session") or {}
assert session.get("access_token"), "expected session.access_token"
assert session.get("refresh_token"), "expected session.refresh_token"
print("OK: login response includes a client-usable session")
PY
