#!/bin/bash
# ═══════════════════════════════════════════════════════
#  FetchBot — Deploy & Smoke-Test
#  Replaces local_deploy.sh. Two differences:
#    1. Runs each remote step as a separate SSH invocation so a failure
#       can't be silently swallowed by a heredoc + set -e combo (which
#       is what bit us on 2026-04-24 — the web rebuild + migrations
#       steps never actually ran on the first attempt).
#    2. After deploy, hits a checklist of endpoints and fails loudly
#       when any of them returns an unexpected status.
#
#  Usage:
#    ./scripts/deploy_and_test.sh           # deploy + smoke-test
#    ./scripts/deploy_and_test.sh --test    # smoke-test only (no deploy)
#    ./scripts/deploy_and_test.sh --no-test # deploy only
# ═══════════════════════════════════════════════════════

set -euo pipefail

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
BOLD='\033[1m'

# ── Config ──
EC2_IP="100.31.135.211"
EC2_USER="ubuntu"
PUBLIC_HOST="https://fetchbot.ai"
PEM_KEY="$(dirname "$0")/../fynda-deploy.pem"
REMOTE_DIR="/opt/fetchbot/ftb-api-26"
LOCAL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_FILE="docker/docker-compose.prod.yml"
SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR"

ssh_run() {
  # Run one command remotely and surface its exit code directly.
  ssh -i "$PEM_KEY" $SSH_OPTS "$EC2_USER@$EC2_IP" "cd $REMOTE_DIR && $1"
}

scp_file() {
  scp -i "$PEM_KEY" $SSH_OPTS "$1" "$EC2_USER@$EC2_IP:$2"
}

rsync_dir() {
  rsync -avz --delete \
    -e "ssh -i $PEM_KEY $SSH_OPTS" \
    --exclude='node_modules' --exclude='__pycache__' --exclude='.pyc' --exclude='.git' \
    "$1" "$EC2_USER@$EC2_IP:$2"
}

# ────────────────────────────────────────────────────────
# SMOKE TEST
# Each check: "URL|EXPECTED_CODE|DESCRIPTION"
#   Expected 401 = endpoint exists and requires auth (good signal for JWT-protected routes).
#   Expected 200 = publicly reachable.
# ────────────────────────────────────────────────────────
smoke_test() {
  echo ""
  echo -e "${BLUE}${BOLD}  ── Smoke test: $PUBLIC_HOST ──${NC}"
  local CHECKS=(
    "/health/|200|backend health"
    "/api/v1/auth/me/|401|/auth/me/ (control — should still work)"
    "/api/v1/auth/session/|401|/auth/session/ (NEW — gates the app)"
    "/api/v1/llm-ranking/00000000-0000-0000-0000-000000000000/preview-prompts/|401|/llm-ranking/.../preview-prompts/ (NEW)"
    "/login|200|/login (SPA route)"
    "/paywall|200|/paywall (NEW SPA route)"
    "/app-onboarding|200|/app-onboarding (NEW SPA route)"
  )
  local FAIL=0
  for row in "${CHECKS[@]}"; do
    IFS='|' read -r path expected desc <<< "$row"
    local got
    got=$(curl -s -o /dev/null -w "%{http_code}" "${PUBLIC_HOST}${path}" || echo "000")
    if [ "$got" = "$expected" ]; then
      echo -e "  ${GREEN}✓${NC} $desc → $got"
    else
      echo -e "  ${RED}✗${NC} $desc → got $got (expected $expected)"
      FAIL=$((FAIL + 1))
    fi
  done

  # Extra check: POST /billing/checkout/ with pro plan — expects 401, not 400
  # (400 would mean backend rejects "pro" as an invalid plan = old code is live).
  local post_got
  post_got=$(curl -s -X POST -H "Content-Type: application/json" \
    -d '{"plan":"pro"}' \
    -o /dev/null -w "%{http_code}" \
    "${PUBLIC_HOST}/api/v1/billing/checkout/" || echo "000")
  if [ "$post_got" = "401" ]; then
    echo -e "  ${GREEN}✓${NC} POST /billing/checkout/ {pro} → 401 (pro plan accepted)"
  else
    echo -e "  ${RED}✗${NC} POST /billing/checkout/ {pro} → $post_got (expected 401; 400 = old code)"
    FAIL=$((FAIL + 1))
  fi

  if [ $FAIL -gt 0 ]; then
    echo ""
    echo -e "${RED}${BOLD}  ✗ Smoke test failed — $FAIL check(s) regressed.${NC}"
    return 1
  fi
  echo ""
  echo -e "${GREEN}${BOLD}  ✓ All endpoints responding as expected.${NC}"
  return 0
}

# ────────────────────────────────────────────────────────
# MODE HANDLING
# ────────────────────────────────────────────────────────
MODE="full"
case "${1:-}" in
  --test)    MODE="test" ;;
  --no-test) MODE="deploy" ;;
  "")        MODE="full" ;;
  *)         echo "Usage: $0 [--test | --no-test]"; exit 1 ;;
esac

if [ "$MODE" = "test" ]; then
  smoke_test
  exit $?
fi

# ────────────────────────────────────────────────────────
# DEPLOY
# ────────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}${BOLD}  ╔══════════════════════════════════════╗${NC}"
echo -e "${BLUE}${BOLD}  ║   FetchBot Deploy & Test             ║${NC}"
echo -e "${BLUE}${BOLD}  ║   Target: ${EC2_IP}            ║${NC}"
echo -e "${BLUE}${BOLD}  ╚══════════════════════════════════════╝${NC}"
echo ""

echo -e "${YELLOW}▸ [1/7] SSH connectivity${NC}"
ssh_run "echo ok" > /dev/null
echo -e "${GREEN}  ✓ Connected${NC}"

echo -e "${YELLOW}▸ [2/7] Syncing frontend files${NC}"
rsync_dir "$LOCAL_DIR/frontend/" "$REMOTE_DIR/frontend/"
echo -e "${GREEN}  ✓ Frontend synced${NC}"

echo -e "${YELLOW}▸ [3/7] Syncing backend files${NC}"
for dir in apps config core scripts pixel; do
  [ -d "$LOCAL_DIR/$dir" ] && rsync_dir "$LOCAL_DIR/$dir/" "$REMOTE_DIR/$dir/"
done
for f in manage.py pyproject.toml conftest.py docker/docker-compose.prod.yml \
         docker/Dockerfile docker/Dockerfile.frontend docker/Dockerfile.celery; do
  [ -f "$LOCAL_DIR/$f" ] && scp_file "$LOCAL_DIR/$f" "$REMOTE_DIR/$f"
done
echo -e "${GREEN}  ✓ Backend synced${NC}"

echo -e "${YELLOW}▸ [4/7] Rebuilding frontend bundle${NC}"
ssh_run "docker compose -f $COMPOSE_FILE build --no-cache --build-arg CACHE_DATE=\"\$(date +%s)\" frontend"
ssh_run "docker compose -f $COMPOSE_FILE rm -f frontend 2>/dev/null || true"
ssh_run "docker compose -f $COMPOSE_FILE run --rm frontend"
ssh_run "docker compose -f $COMPOSE_FILE restart nginx"
echo -e "${GREEN}  ✓ Frontend rebuilt, nginx restarted${NC}"

echo -e "${YELLOW}▸ [5/7] Rebuilding web + celery containers${NC}"
ssh_run "docker compose -f $COMPOSE_FILE up -d --build web celery"
echo -e "${GREEN}  ✓ Web + celery recreated${NC}"

echo -e "${YELLOW}▸ [6/7] Waiting for web to be healthy${NC}"
WAITED=0
while [ $WAITED -lt 60 ]; do
  STATUS=$(ssh_run "docker inspect --format='{{.State.Health.Status}}' docker-web-1 2>/dev/null || echo unknown") || true
  if [ "$STATUS" = "healthy" ]; then
    echo -e "${GREEN}  ✓ web healthy${NC}"
    break
  fi
  sleep 3
  WAITED=$((WAITED + 3))
done
if [ "$STATUS" != "healthy" ]; then
  echo -e "${RED}  ✗ web did not reach healthy within 60s (status=$STATUS)${NC}"
  ssh_run "docker compose -f $COMPOSE_FILE logs --tail=40 web"
  exit 1
fi

echo -e "${YELLOW}▸ [7/7] Migrations + static collection${NC}"
# Show migrate output so any unapplied migration is visible in the log.
ssh_run "docker compose -f $COMPOSE_FILE exec -T web python manage.py migrate --noinput"
ssh_run "docker compose -f $COMPOSE_FILE exec -T web python manage.py collectstatic --noinput 2>/dev/null || true"
echo -e "${GREEN}  ✓ Migrations applied${NC}"

echo ""
echo -e "${BLUE}${BOLD}  Container status:${NC}"
ssh_run "docker compose -f $COMPOSE_FILE ps"

# ── Smoke test ──
if [ "$MODE" = "full" ]; then
  if ! smoke_test; then
    echo ""
    echo -e "${RED}${BOLD}  Deploy completed but smoke tests failed. Investigate before announcing.${NC}"
    exit 2
  fi
fi

echo ""
echo -e "${GREEN}${BOLD}  ✓ Deploy complete! → $PUBLIC_HOST${NC}"
echo ""
