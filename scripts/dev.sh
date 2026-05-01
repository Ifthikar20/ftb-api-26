#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════
#  Local dev launcher — Django + Celery worker + beat
#  Run from the repo root.
# ═══════════════════════════════════════════════════════
#
# Activates the project virtualenv, then starts:
#   1. Django dev server   (foreground; ctrl-c stops everything)
#   2. Celery worker       (background, ai/default/integrations/webhooks queues)
#   3. Celery beat         (background, scheduled tasks)
#
# Usage:
#   scripts/dev.sh              # web + worker + beat
#   scripts/dev.sh --no-beat    # skip the beat scheduler
#   scripts/dev.sh --web-only   # just the Django server
#
# Logs from the background services land in ./tmp/dev-*.log.

set -euo pipefail

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
BOLD='\033[1m'

# ── Locate the repo root from this script's path so the launcher works
#    no matter where the caller invokes it from.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

# ── Activate the venv (create one with `python3.12 -m venv .venv` if missing).
if [[ ! -f ".venv/bin/activate" ]]; then
  echo -e "${RED}✗ .venv not found at ${REPO_ROOT}/.venv${NC}"
  echo "  Create it with:  python3.12 -m venv .venv && source .venv/bin/activate && pip install -r requirements/dev.txt"
  exit 1
fi
# shellcheck disable=SC1091
source .venv/bin/activate
echo -e "${GREEN}✓ venv activated${NC} ($(python --version))"

# ── Args ──
START_BEAT=1
WEB_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --no-beat)  START_BEAT=0 ;;
    --web-only) WEB_ONLY=1 ;;
    -h|--help)
      sed -n '2,20p' "${BASH_SOURCE[0]}" | sed 's/^# //;s/^#//'
      exit 0
      ;;
    *) echo -e "${RED}Unknown arg: $arg${NC}"; exit 1 ;;
  esac
done

mkdir -p tmp
PIDS=()

# ── Cleanup: kill background workers when the foreground server exits.
cleanup() {
  echo ""
  echo -e "${YELLOW}▸ stopping background services…${NC}"
  for pid in "${PIDS[@]:-}"; do
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done
}
trap cleanup EXIT INT TERM

if [[ $WEB_ONLY -eq 0 ]]; then
  echo -e "${BLUE}▸ starting Celery worker… (logs: tmp/dev-worker.log)${NC}"
  celery -A config worker \
    -Q ai,default,integrations,webhooks \
    -l info \
    >tmp/dev-worker.log 2>&1 &
  PIDS+=($!)

  if [[ $START_BEAT -eq 1 ]]; then
    echo -e "${BLUE}▸ starting Celery beat…    (logs: tmp/dev-beat.log)${NC}"
    celery -A config beat -l info >tmp/dev-beat.log 2>&1 &
    PIDS+=($!)
  fi
fi

echo -e "${GREEN}▸ starting Django dev server on http://localhost:8000${NC}"
echo -e "${YELLOW}  (ctrl-c to stop everything)${NC}"
echo ""

# Foreground — runserver holds the terminal. cleanup runs on exit.
python manage.py runserver
