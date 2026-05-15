#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════
#  FetchBot — Deploy
#
#  Runs FROM your laptop and SSHs into the EC2 host. One script,
#  four modes. Replaces the old deploy.sh + deploy_and_test.sh +
#  deploy_and_monitor.sh trio.
#
#  Usage:
#    bash scripts/deploy.sh              # deploy + smoke-test (default)
#    bash scripts/deploy.sh --no-test    # deploy without smoke-test
#    bash scripts/deploy.sh --test       # smoke-test only, no deploy
#    bash scripts/deploy.sh --logs       # tail container logs for 60s
#    bash scripts/deploy.sh --inspect-env # dump key names in remote .env.prod
#    bash scripts/deploy.sh --help
#
#  Environment overrides (all optional):
#    BRANCH       git branch to deploy   (default: main)
#    EC2_HOST     SSH host               (default: 100.31.135.211)
#    EC2_USER     SSH user               (default: ubuntu)
#    PEM_KEY      path to SSH key        (default: <repo>/fynda-deploy.pem)
#    REMOTE_DIR   app dir on the server  (default: /opt/fetchbot/ftb-api-26)
#    PUBLIC_HOST  smoke-test target      (default: https://fetchbot.ai)
#
#  First-time EC2 setup (apt update, Docker install, swap, repo
#  clone) is NOT done here — it's a one-time concern. Bootstrap a
#  fresh host with the commands in docs/EC2_BOOTSTRAP.md. This
#  script assumes Docker, git, and the repo are already on the box.
# ════════════════════════════════════════════════════════════════════

set -euo pipefail

# ── Config ──────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

BRANCH="${BRANCH:-main}"
EC2_HOST="${EC2_HOST:-100.31.135.211}"
EC2_USER="${EC2_USER:-ubuntu}"
PEM_KEY="${PEM_KEY:-$REPO_DIR/fynda-deploy.pem}"
REMOTE_DIR="${REMOTE_DIR:-/opt/fetchbot/ftb-api-26}"
PUBLIC_HOST="${PUBLIC_HOST:-https://fetchbot.ai}"
COMPOSE_FILE="docker/docker-compose.prod.yml"

SSH_OPTS=(-i "$PEM_KEY" -o StrictHostKeyChecking=accept-new -o LogLevel=ERROR)

# ── Style ───────────────────────────────────────────────────────────
B=$'\033[1m'; R=$'\033[0;31m'; G=$'\033[0;32m'; Y=$'\033[1;33m'
C=$'\033[0;36m'; D=$'\033[2m'; N=$'\033[0m'
banner() {
  printf "\n%s%s╔══════════════════════════════════════════════════╗%s\n" "$C" "$B" "$N"
  printf "%s%s║  %-48s║%s\n" "$C" "$B" "$1" "$N"
  printf "%s%s╚══════════════════════════════════════════════════╝%s\n\n" "$C" "$B" "$N"
}
step() { printf "\n%s%s▸ %s%s\n" "$C" "$B" "$*" "$N"; }
ok()   { printf "  %s✓%s %s\n" "$G" "$N" "$*"; }
warn() { printf "  %s⚠%s %s\n" "$Y" "$N" "$*"; }
err()  { printf "  %s✗%s %s\n" "$R" "$N" "$*"; }
die()  { err "$*"; exit 1; }

ssh_remote()     { ssh "${SSH_OPTS[@]}" "$EC2_USER@$EC2_HOST" "$@"; }
remote_compose() { ssh_remote "cd $REMOTE_DIR && docker compose -f $COMPOSE_FILE $*"; }

# ── State carried between phases ────────────────────────────────────
LOCAL_SHA=""; TARGET_SHA=""; PRIOR_SHA=""; DEPLOYED_SHA=""; SKIP_BUILD=0

# ════════════════════════════════════════════════════════════════════
# Phase 1 — Pre-flight (local checks)
# ════════════════════════════════════════════════════════════════════
preflight() {
  step "Pre-flight"
  [[ -f "$PEM_KEY" ]] || die "PEM key not found: $PEM_KEY"
  command -v git >/dev/null || die "git not installed"
  command -v ssh >/dev/null || die "ssh not installed"
  chmod 600 "$PEM_KEY" 2>/dev/null || true

  cd "$REPO_DIR"
  git rev-parse --is-inside-work-tree >/dev/null 2>&1 \
    || die "$REPO_DIR is not a git repo"

  LOCAL_SHA=$(git rev-parse HEAD)
  ok "Local HEAD: ${LOCAL_SHA:0:12} ($(git log -1 --format=%s))"

  # Warn (but don't block) on a dirty tree — those changes will NOT
  # deploy because we ship from origin/$BRANCH, not the local copy.
  if ! git diff --quiet \
       || ! git diff --cached --quiet \
       || [[ -n "$(git ls-files --others --exclude-standard)" ]]; then
    warn "Working tree is DIRTY — uncommitted changes will NOT deploy:"
    git status --short | sed 's/^/      /'
  fi

  step "Sync with origin/$BRANCH"
  git fetch origin "$BRANCH" --quiet
  local local_b remote_b
  local_b=$(git rev-parse "$BRANCH" 2>/dev/null || echo "")
  remote_b=$(git rev-parse "origin/$BRANCH")
  if [[ -z "$local_b" ]]; then
    warn "Local '$BRANCH' not checked out; deploying origin/$BRANCH"
  elif [[ "$local_b" != "$remote_b" ]]; then
    if git merge-base --is-ancestor "$remote_b" "$local_b"; then
      warn "Local '$BRANCH' has unpushed commits ahead of origin"
      read -r -p "    Push to origin/$BRANCH now? [y/N] " ans
      if [[ "$ans" =~ ^[Yy] ]]; then
        git push origin "$BRANCH"
        ok "Pushed."
      else
        warn "Skipping push — remote will deploy origin/$BRANCH (older than local)."
      fi
    else
      warn "Local '$BRANCH' is BEHIND origin/$BRANCH; deploying origin/$BRANCH."
    fi
  else
    ok "Local '$BRANCH' matches origin/$BRANCH"
  fi
  TARGET_SHA=$(git rev-parse "origin/$BRANCH")
  ok "Target deploy SHA: ${TARGET_SHA:0:12}"

  step "SSH connectivity"
  ssh_remote "echo ok" >/dev/null 2>&1 \
    || die "Cannot SSH to $EC2_USER@$EC2_HOST (check PEM key + security group)"
  ok "Reachable: $EC2_USER@$EC2_HOST"
}

# ════════════════════════════════════════════════════════════════════
# Phase 2 — Validate remote .env.prod
# Catches missing/placeholder keys BEFORE we restart anything.
# ════════════════════════════════════════════════════════════════════
validate_env() {
  step "Validate remote .env.prod"

  local REQUIRED_STR="DJANGO_SECRET_KEY JWT_SIGNING_KEY FIELD_ENCRYPTION_KEY DB_PASSWORD ANTHROPIC_API_KEY OPENAI_API_KEY GEMINI_API_KEY PERPLEXITY_API_KEY GOOGLE_API_KEY GOOGLE_CSE_ID"
  local OPTIONAL_STR="DEEPSEEK_API_KEY SERPAPI_KEY STRIPE_SECRET_KEY SENDGRID_API_KEY GOOGLE_OAUTH_CLIENT_ID GOOGLE_CSE_DAILY_LIMIT_PER_USER CLAUDE_JUDGE_DAILY_LIMIT_PER_USER CLAUDE_REWRITE_DAILY_LIMIT_PER_USER"

  # Force bash on the remote (Ubuntu's /bin/sh is dash, and we use
  # ${!var} indirect expansion + [[ … == CHANGE_ME* ]] which are
  # bash-only). Pipe the script over stdin so quoting stays sane.
  local out
  out=$(ssh "${SSH_OPTS[@]}" "$EC2_USER@$EC2_HOST" bash -s <<REMOTE
set -e
cd "$REMOTE_DIR"
if [ ! -f .env.prod ]; then
  echo "MISSING_FILE"
  exit 0
fi

# Normalise CRLF line endings before sourcing — a file edited on
# Windows or copy-pasted from a chat will not load via 'source' if
# values are quoted with a trailing \r, and we'll report keys as
# missing even though they're present.
if grep -q \$'\r' .env.prod 2>/dev/null; then
  TMP=\$(mktemp)
  tr -d '\r' < .env.prod > "\$TMP"
  set -a; . "\$TMP"; set +a
  rm -f "\$TMP"
else
  set -a; . ./.env.prod; set +a
fi

missing=""
placeholder=""
optional_missing=""
for v in $REQUIRED_STR; do
  val="\${!v:-}"
  if [ -z "\$val" ]; then
    missing="\$missing \$v"
  elif [[ "\$val" == CHANGE_ME* ]]; then
    placeholder="\$placeholder \$v"
  fi
done
for v in $OPTIONAL_STR; do
  val="\${!v:-}"
  if [ -z "\$val" ]; then
    optional_missing="\$optional_missing \$v"
  fi
done
echo "MISSING:\$missing"
echo "PLACEHOLDER:\$placeholder"
echo "OPTIONAL_MISSING:\$optional_missing"
REMOTE
  )
  if grep -q "^MISSING_FILE$" <<<"$out"; then
    die ".env.prod missing at $EC2_HOST:$REMOTE_DIR — create it from .env.prod.example first."
  fi
  local missing placeholder optional_missing
  missing=$(grep "^MISSING:" <<<"$out" | cut -d: -f2-)
  placeholder=$(grep "^PLACEHOLDER:" <<<"$out" | cut -d: -f2-)
  optional_missing=$(grep "^OPTIONAL_MISSING:" <<<"$out" | cut -d: -f2-)

  if [[ -n "${missing// }" || -n "${placeholder// }" ]]; then
    err ".env.prod is incomplete:"
    [[ -n "${missing// }" ]]     && printf "      %sMissing:%s        %s\n" "$R" "$N" "$missing"
    [[ -n "${placeholder// }" ]] && printf "      %sStill CHANGE_ME:%s %s\n" "$R" "$N" "$placeholder"
    echo ""
    printf "      %sInspect what is actually set in .env.prod (names only, no values):%s\n" "$Y" "$N"
    printf "         bash scripts/deploy.sh --inspect-env\n\n"
    printf "      %sFix the file in place:%s\n" "$Y" "$N"
    printf "         ssh -i %s %s@%s 'sudo nano %s/.env.prod'\n" "$PEM_KEY" "$EC2_USER" "$EC2_HOST" "$REMOTE_DIR"
    exit 1
  fi
  if [[ -n "${optional_missing// }" ]]; then
    warn "Optional features disabled (key missing):$optional_missing"
  fi
  ok ".env.prod looks good"
}

# Dumps the KEY NAMES set in the remote .env.prod (no values cross the
# wire). Use when validate_env reports keys as missing and you want to
# confirm whether they're truly absent vs. mis-named vs. has a parse
# issue (e.g. CRLF, unquoted value with #).
inspect_env() {
  step "Inspect remote .env.prod"
  ssh "${SSH_OPTS[@]}" "$EC2_USER@$EC2_HOST" bash -s <<REMOTE
set -e
cd "$REMOTE_DIR"
if [ ! -f .env.prod ]; then
  echo "no .env.prod found at $REMOTE_DIR"
  exit 1
fi
echo "Keys defined in $REMOTE_DIR/.env.prod (names only):"
echo "──────────────────────────────────────────────────────"
# Grab everything that looks like KEY=value, normalising CRLF first.
tr -d '\r' < .env.prod \
  | grep -E '^[[:space:]]*[A-Za-z_][A-Za-z0-9_]*=' \
  | sed -E 's/^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)=.*/  \1/' \
  | sort -u
echo "──────────────────────────────────────────────────────"
echo "Total: \$(tr -d '\r' < .env.prod | grep -cE '^[[:space:]]*[A-Za-z_][A-Za-z0-9_]*=') keys"
REMOTE
}

# ════════════════════════════════════════════════════════════════════
# Phase 3 — Capture current production state
# ════════════════════════════════════════════════════════════════════
capture_prior() {
  step "Capture current production state"
  PRIOR_SHA=$(ssh_remote "cd $REMOTE_DIR && git rev-parse HEAD" 2>/dev/null || echo "unknown")
  ok "Remote HEAD before deploy: ${PRIOR_SHA:0:12}"
  if [[ "$PRIOR_SHA" == "$TARGET_SHA" ]]; then
    warn "Remote already at target SHA — nothing new to ship."
    read -r -p "    Force rebuild anyway? [y/N] " ans
    if [[ "$ans" =~ ^[Yy] ]]; then
      SKIP_BUILD=0
    else
      SKIP_BUILD=1
    fi
  fi
}

# ════════════════════════════════════════════════════════════════════
# Phase 4 — Deploy (pull, rebuild, migrate)
# ════════════════════════════════════════════════════════════════════
deploy() {
  step "Pull latest code on remote"
  ssh_remote "cd $REMOTE_DIR \
    && git fetch origin $BRANCH --quiet \
    && git checkout $BRANCH \
    && git reset --hard origin/$BRANCH"
  local new_sha
  new_sha=$(ssh_remote "cd $REMOTE_DIR && git rev-parse HEAD")
  [[ "$new_sha" == "$TARGET_SHA" ]] \
    || die "Remote SHA mismatch after pull (got ${new_sha:0:12}, expected ${TARGET_SHA:0:12})"
  ok "Remote now at ${new_sha:0:12}"

  if [[ "$SKIP_BUILD" == "1" ]]; then
    warn "Skipping container rebuild"
    return
  fi

  local cache_bust
  cache_bust=$(date +%s)

  step "Rebuild backend (web + celery)"
  remote_compose "build --build-arg CACHE_DATE=$cache_bust web celery"
  remote_compose "up -d web celery"
  ok "Backend rebuilt and restarted"

  # Frontend is a one-shot init container — `up -d` won't re-run it
  # once it has exited, so we explicitly rm + run + restart nginx.
  step "Rebuild frontend bundle (no-cache)"
  remote_compose "build --no-cache --build-arg CACHE_DATE=$cache_bust frontend"
  remote_compose "rm -f frontend" >/dev/null 2>&1 || true
  remote_compose "run --rm frontend"
  remote_compose "restart nginx"
  ok "Frontend bundle refreshed and nginx reloaded"

  step "Apply migrations & collect static"
  remote_compose "exec -T web python manage.py migrate --noinput"
  remote_compose "exec -T web python manage.py collectstatic --noinput" \
    >/dev/null 2>&1 || true
  ok "Migrations applied"
}

# ════════════════════════════════════════════════════════════════════
# Phase 5 — Post-deploy validation
# ════════════════════════════════════════════════════════════════════
validate_deploy() {
  step "Post-deploy validation"

  DEPLOYED_SHA=$(ssh_remote "cd $REMOTE_DIR && git rev-parse HEAD")
  if [[ "$DEPLOYED_SHA" == "$TARGET_SHA" ]]; then
    ok "Deployed SHA matches target (${DEPLOYED_SHA:0:12})"
  else
    err "SHA mismatch: deployed=${DEPLOYED_SHA:0:12} target=${TARGET_SHA:0:12}"
  fi

  local unapplied
  unapplied=$(remote_compose "exec -T web python manage.py showmigrations --plan" 2>/dev/null \
              | grep -c '^\[ \]' || true)
  if [[ "${unapplied:-0}" -eq 0 ]]; then
    ok "All migrations applied"
  else
    warn "$unapplied migrations still unapplied"
  fi

  ok "Container status:"
  remote_compose "ps --format 'table {{.Service}}\t{{.State}}\t{{.Status}}'" \
    | sed 's/^/      /'

  local http
  http=$(ssh_remote "curl -s -o /dev/null -w '%{http_code}' http://localhost/health/" 2>/dev/null || echo "000")
  if [[ "$http" == "200" ]]; then
    ok "Health endpoint: HTTP 200"
  else
    warn "Health endpoint: HTTP $http"
  fi

  local celery_pong
  celery_pong=$(remote_compose "exec -T celery celery -A config.celery inspect ping --timeout 5" 2>/dev/null \
                | grep -c "pong" || true)
  if [[ "${celery_pong:-0}" -gt 0 ]]; then
    ok "Celery worker responding"
  else
    warn "Celery ping failed (worker may still be warming up)"
  fi
}

# ════════════════════════════════════════════════════════════════════
# Phase 6 — Smoke test
# Each check: "PATH|EXPECTED_CODE|DESCRIPTION".
# 401 = endpoint exists + requires auth (right signal for JWT routes).
# 200 = publicly reachable.
# ════════════════════════════════════════════════════════════════════
smoke_test() {
  step "Smoke test: $PUBLIC_HOST"
  local CHECKS=(
    "/health/|200|backend health"
    "/api/v1/auth/me/|401|/auth/me/ (JWT-gated)"
    "/api/v1/auth/session/|401|/auth/session/"
    "/api/v1/llm-ranking/00000000-0000-0000-0000-000000000000/preview-prompts/|401|/llm-ranking/.../preview-prompts/"
    "/api/v1/llm-ranking/00000000-0000-0000-0000-000000000000/geo/rewrite/|401|/llm-ranking/.../geo/rewrite/ (NEW)"
    "/api/v1/llm-ranking/00000000-0000-0000-0000-000000000000/geo/judge/|401|/llm-ranking/.../geo/judge/ (NEW)"
    "/login|200|/login (SPA route)"
    "/paywall|200|/paywall (SPA route)"
    "/app-onboarding|200|/app-onboarding (SPA route)"
  )
  local FAIL=0
  for row in "${CHECKS[@]}"; do
    IFS='|' read -r path expected desc <<< "$row"
    local got
    got=$(curl -s -o /dev/null -w "%{http_code}" "${PUBLIC_HOST}${path}" || echo "000")
    if [[ "$got" == "$expected" ]]; then
      ok "$desc → $got"
    else
      err "$desc → got $got (expected $expected)"
      FAIL=$((FAIL + 1))
    fi
  done

  # POST /billing/checkout/ {pro} should 401 (auth-gated). 400 means
  # the backend rejected "pro" as an invalid plan = old code is live.
  local post_got
  post_got=$(curl -s -X POST -H "Content-Type: application/json" \
    -d '{"plan":"pro"}' \
    -o /dev/null -w "%{http_code}" \
    "${PUBLIC_HOST}/api/v1/billing/checkout/" || echo "000")
  if [[ "$post_got" == "401" ]]; then
    ok "POST /billing/checkout/ {pro} → 401 (plan accepted)"
  else
    err "POST /billing/checkout/ {pro} → $post_got (expected 401; 400 = old code)"
    FAIL=$((FAIL + 1))
  fi

  if [[ $FAIL -gt 0 ]]; then
    err "Smoke test failed — $FAIL check(s) regressed."
    return 1
  fi
  ok "All endpoints responding as expected."
  return 0
}

# ════════════════════════════════════════════════════════════════════
# Phase 7 — Tail logs (--logs only)
# 60s of streaming container logs so you can watch traffic warm up.
# ════════════════════════════════════════════════════════════════════
tail_logs() {
  step "Tail container logs for 60s (Ctrl+C to stop earlier)"
  remote_compose "logs --tail=50 --follow --timestamps" &
  local pid=$!
  sleep 60
  kill "$pid" 2>/dev/null || true
  wait "$pid" 2>/dev/null || true
}

# ════════════════════════════════════════════════════════════════════
# Entry point
# ════════════════════════════════════════════════════════════════════
usage() {
  sed -n '3,28p' "$0"
}

MODE="full"
case "${1:-}" in
  ""|--full)      MODE="full" ;;
  --no-test)      MODE="deploy" ;;
  --test)         MODE="test" ;;
  --logs)         MODE="logs" ;;
  --inspect-env)  MODE="inspect" ;;
  -h|--help)      usage; exit 0 ;;
  *)              echo "Unknown flag: $1"; usage; exit 1 ;;
esac

banner "FetchBot Deploy — branch=$BRANCH"

case "$MODE" in
  test)
    smoke_test
    exit $?
    ;;
  logs)
    tail_logs
    exit 0
    ;;
  inspect)
    inspect_env
    exit 0
    ;;
  deploy|full)
    preflight
    validate_env
    capture_prior
    deploy
    validate_deploy
    if [[ "$MODE" == "full" ]]; then
      if ! smoke_test; then
        err "Deploy completed but smoke tests failed — investigate before announcing."
        exit 2
      fi
    fi
    ;;
esac

echo ""
ok "Deploy complete  →  $PUBLIC_HOST"
printf "    Before: %s   After: %s\n" "${PRIOR_SHA:0:12}" "${DEPLOYED_SHA:0:12}"
echo ""
