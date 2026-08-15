#!/usr/bin/env bash
# Fetch logs from the production EC2 host.
#
# Usage:
#   scripts/logs.sh                          # tail -f web service logs
#   scripts/logs.sh <request-id>             # grep a single request id
#   scripts/logs.sh -s <service>             # tail a specific compose service
#   scripts/logs.sh -s celery -n 500         # last 500 lines of celery service
#   scripts/logs.sh -s web <request-id>      # grep request id in web logs
#
# Env overrides (same defaults as scripts/deploy.sh):
#   EC2_HOST=100.31.135.211
#   EC2_USER=ubuntu
#   PEM_KEY=./fynda-deploy.pem
#   REMOTE_DIR=/opt/fetchbot/ftb-api-26
#   SERVICE=web

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

EC2_HOST="${EC2_HOST:-100.31.135.211}"
EC2_USER="${EC2_USER:-ubuntu}"
PEM_KEY="${PEM_KEY:-$REPO_DIR/fynda-deploy.pem}"
REMOTE_DIR="${REMOTE_DIR:-/opt/fetchbot/ftb-api-26}"
COMPOSE_FILE="docker/docker-compose.prod.yml"

SERVICE="${SERVICE:-web}"
LINES=""
REQUEST_ID=""

usage() {
  sed -n '2,15p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -s|--service) SERVICE="$2"; shift 2 ;;
    -n|--lines)   LINES="$2";   shift 2 ;;
    -h|--help)    usage 0 ;;
    --) shift; REQUEST_ID="${1:-}"; break ;;
    -*) echo "Unknown flag: $1" >&2; usage 1 ;;
    *)  REQUEST_ID="$1"; shift ;;
  esac
done

if [[ ! -f "$PEM_KEY" ]]; then
  echo "PEM key not found at $PEM_KEY" >&2
  echo "Set PEM_KEY=/path/to/key.pem or place fynda-deploy.pem in repo root." >&2
  exit 1
fi

SSH_OPTS=(-i "$PEM_KEY" -o StrictHostKeyChecking=accept-new -o LogLevel=ERROR)

if [[ -n "$REQUEST_ID" ]]; then
  # Grep a specific request id across the full log history.
  echo "Searching $SERVICE logs on $EC2_HOST for request_id=$REQUEST_ID ..."
  remote_cmd="cd $REMOTE_DIR && docker compose -f $COMPOSE_FILE logs --no-color ${LINES:+--tail $LINES} $SERVICE 2>&1 | grep -F '$REQUEST_ID' || echo 'No matches for request_id=$REQUEST_ID in $SERVICE.'"
else
  # Tail -f the service. Default to last 200 lines if not specified.
  TAIL_LINES="${LINES:-200}"
  echo "Streaming $SERVICE logs on $EC2_HOST (Ctrl-C to stop)..."
  remote_cmd="cd $REMOTE_DIR && docker compose -f $COMPOSE_FILE logs --no-color --tail $TAIL_LINES -f $SERVICE"
fi

exec ssh "${SSH_OPTS[@]}" "$EC2_USER@$EC2_HOST" "$remote_cmd"
