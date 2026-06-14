#!/usr/bin/env bash
set -euo pipefail

BASE_URL="https://www.schosel.net"
COOKIE_JAR="$(mktemp)"

USERNAME="${SCH_USERNAME:?Set SCH_USERNAME}"
PASSWORD="${SCH_PASSWORD:?Set SCH_PASSWORD}"

MATCH_ID="${1:?Usage: $0 MATCH_ID GOALS_TEAM1 GOALS_TEAM2 [FIRST_GOAL] [OVER]}"
GOALS_TEAM1="${2:?Missing goalsTeam1}"
GOALS_TEAM2="${3:?Missing goalsTeam2}"
FIRST_GOAL="${4:-}"
OVER="${5:-false}"

# Login; field names are inferred from the standard login form.
echo "Logging in..."

curl -i -sS -c "$COOKIE_JAR" \
  -X POST "$BASE_URL/api/login" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg email "$USERNAME" --arg password "$PASSWORD" \
    '{email:$email,password:$password}')"

echo
echo "Cookies:"
cat "$COOKIE_JAR"
echo

# Build JSON payload
if [[ -n "$FIRST_GOAL" ]]; then
  JSON=$(jq -n \
    --argjson g1 "$GOALS_TEAM1" \
    --argjson g2 "$GOALS_TEAM2" \
    --arg fg "$FIRST_GOAL" \
    --argjson over "$OVER" \
    '{goalsTeam1:$g1, goalsTeam2:$g2, firstGoal:$fg, over:$over}')
else
  JSON=$(jq -n \
    --argjson g1 "$GOALS_TEAM1" \
    --argjson g2 "$GOALS_TEAM2" \
    --argjson over "$OVER" \
    '{goalsTeam1:$g1, goalsTeam2:$g2, over:$over}')
fi

curl -sS -b "$COOKIE_JAR" \
  -X POST "$BASE_URL/api/admin/outcome/$MATCH_ID" \
  -H "Content-Type: application/json" \
  -d "$JSON"

cat "$COOKIE_JAR"
