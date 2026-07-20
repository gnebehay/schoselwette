#!/usr/bin/env bash
set -euo pipefail

BASE_URL="https://schosel.net"
COOKIE_JAR="$(mktemp)"

USERNAME="${SCH_USERNAME:?Set SCH_USERNAME}"
PASSWORD="${SCH_PASSWORD:?Set SCH_PASSWORD}"

CHAMPION_ID="${1:?Usage: $0 CHAMPION_ID}"

# Login; field names are inferred from the standard login form.
echo "Logging in..."

curl -i -sS -L -c "$COOKIE_JAR" \
  -X POST "$BASE_URL/api/login" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg email "$USERNAME" --arg password "$PASSWORD" \
    '{email:$email,password:$password}')"

echo
echo "Cookies:"
cat "$COOKIE_JAR"
echo

JSON=$(jq -n --argjson champion_id "$CHAMPION_ID" '{champion_id:$champion_id}')

curl -sS -L -b "$COOKIE_JAR" \
  -X POST "$BASE_URL/api/admin/make_champion" \
  -H "Content-Type: application/json" \
  -d "$JSON"

cat "$COOKIE_JAR"
