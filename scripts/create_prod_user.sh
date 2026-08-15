#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════
#  Create a real user in the fetchbot.ai production database.
#
#  Run from your local machine. SSHes to the EC2 box, execs into the
#  running web container, and invokes scripts/create_prod_user.py with
#  the prod Django settings already loaded.
#
#  Usage:
#    bash scripts/create_prod_user.sh user@example.com "Jane Doe"
#    bash scripts/create_prod_user.sh user@example.com "Jane Doe" 'S3cretPass!'
#    bash scripts/create_prod_user.sh --staff user@example.com "Admin User"
#    bash scripts/create_prod_user.sh --plan growth user@example.com "Pro User"
#
#  Defaults:
#    EC2_HOST    100.31.135.211
#    EC2_USER    ubuntu
#    PEM_KEY     ~/Desktop/FTB_APP/fynda-deploy.pem
#    REMOTE_DIR  /opt/fetchbot/ftb-api-26
#
#  Override any of those by exporting before invoking, e.g.
#    PEM_KEY=~/.ssh/other-key.pem bash scripts/create_prod_user.sh ...
# ════════════════════════════════════════════════════════════════════

set -euo pipefail

EC2_HOST="${EC2_HOST:-100.31.135.211}"
EC2_USER="${EC2_USER:-ubuntu}"
PEM_KEY="${PEM_KEY:-$HOME/Desktop/FTB_APP/fynda-deploy.pem}"
REMOTE_DIR="${REMOTE_DIR:-/opt/fetchbot/ftb-api-26}"
COMPOSE_FILE="${COMPOSE_FILE:-docker/docker-compose.prod.yml}"
WEB_SERVICE="${WEB_SERVICE:-web}"

# ── Args ─────────────────────────────────────────────────────────────
EXTRA_FLAGS=()
POSITIONAL=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --staff)
      EXTRA_FLAGS+=("--staff"); shift ;;
    --plan)
      [[ $# -lt 2 ]] && { echo "ERR: --plan needs a value" >&2; exit 1; }
      EXTRA_FLAGS+=("--plan" "$2"); shift 2 ;;
    --plan=*)
      EXTRA_FLAGS+=("--plan" "${1#--plan=}"); shift ;;
    -h|--help)
      sed -n '3,21p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *)
      POSITIONAL+=("$1"); shift ;;
  esac
done

if [[ ${#POSITIONAL[@]} -lt 2 ]]; then
  echo "Usage: bash scripts/create_prod_user.sh [--staff] [--plan PLAN] EMAIL FULL_NAME [PASSWORD]" >&2
  exit 1
fi

EMAIL="${POSITIONAL[0]}"
FULL_NAME="${POSITIONAL[1]}"
PASSWORD="${POSITIONAL[2]:-}"

# ── Pre-flight ───────────────────────────────────────────────────────
if [[ ! -f "$PEM_KEY" ]]; then
  echo "ERR: PEM key not found at $PEM_KEY" >&2
  echo "     Set PEM_KEY env var to override." >&2
  exit 1
fi
chmod 600 "$PEM_KEY" 2>/dev/null || true

echo "▸ Creating user in PROD (${EC2_HOST})"
echo "  Email:     $EMAIL"
echo "  Name:      $FULL_NAME"
if [[ -n "$PASSWORD" ]]; then
  echo "  Password:  (provided)"
else
  echo "  Password:  (auto-generated, printed below)"
fi
[[ ${EXTRA_FLAGS[@]+x} ]] && echo "  Flags:     ${EXTRA_FLAGS[*]}"
echo ""

# ── Build the remote command ─────────────────────────────────────────
# We exec into the running web container so DATABASE_URL and the rest
# of the prod env are already loaded. --yes skips the "type CREATE"
# prompt because we have no TTY on the inner shell.
PY_CMD=(python scripts/create_prod_user.py --yes)
[[ -n "$PASSWORD" ]] && PY_CMD+=(--password "$PASSWORD")
for f in ${EXTRA_FLAGS[@]+"${EXTRA_FLAGS[@]}"}; do
  PY_CMD+=("$f")
done
PY_CMD+=("$EMAIL" "$FULL_NAME")

# Quote each arg for safe interpolation through ssh + docker compose exec
printf -v QUOTED '%q ' "${PY_CMD[@]}"

REMOTE_CMD="cd ${REMOTE_DIR} && docker compose -f ${COMPOSE_FILE} exec -T ${WEB_SERVICE} ${QUOTED}"

# ── Run ──────────────────────────────────────────────────────────────
ssh -o StrictHostKeyChecking=accept-new -i "$PEM_KEY" "${EC2_USER}@${EC2_HOST}" \
  "$REMOTE_CMD"
