#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════
#  FetchBot — single-file dev + deploy entry point.
#
#  One script. Multiple subcommands. Replaces deploy.sh,
#  deploy_and_test.sh, deploy_and_monitor.sh, dev.sh, migrate_all.sh,
#  health_check.py, seed_data.py, eval_ranking.py.
#
#  Usage:
#    bash scripts/deploy.sh                  # alias for 'deploy'
#    bash scripts/deploy.sh deploy [flags]   # production deploy
#    bash scripts/deploy.sh dev [flags]      # local Django + Celery
#    bash scripts/deploy.sh migrate [flags]  # local Django migrations
#    bash scripts/deploy.sh seed             # seed dev DB
#    bash scripts/deploy.sh eval             # NDCG@5 / MRR ranking eval
#    bash scripts/deploy.sh health           # container DB+cache probe
#    bash scripts/deploy.sh install-hooks    # bind git pre-commit
#    bash scripts/deploy.sh help
#
#  Deploy flags (only apply to the 'deploy' subcommand):
#    --no-test       deploy without smoke-test
#    --test          smoke-test only, no deploy
#    --logs          tail container logs for 60s
#    --inspect-env   dump key names in remote .env.prod (no values)
#    --force         bypass critical-secret + prod-sanity blockers
#    --clean         docker system prune -af before build (aggressive)
#
#  Dev flags (--no-beat / --web-only) apply to the 'dev' subcommand.
#  Migrate flags (--check) apply to the 'migrate' subcommand.
#
#  Environment overrides (deploy):
#    BRANCH=main  EC2_HOST=…  EC2_USER=ubuntu  PEM_KEY=…
#    REMOTE_DIR=/opt/fetchbot/ftb-api-26  PUBLIC_HOST=https://fetchbot.ai
# ════════════════════════════════════════════════════════════════════

set -euo pipefail

# ── Repo root ────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Deploy config (env-overridable) ──────────────────────────────────
BRANCH="${BRANCH:-main}"
EC2_HOST="${EC2_HOST:-100.31.135.211}"
EC2_USER="${EC2_USER:-ubuntu}"
PEM_KEY="${PEM_KEY:-$REPO_DIR/fynda-deploy.pem}"
REMOTE_DIR="${REMOTE_DIR:-/opt/fetchbot/ftb-api-26}"
PUBLIC_HOST="${PUBLIC_HOST:-https://fetchbot.ai}"
COMPOSE_FILE="docker/docker-compose.prod.yml"

SSH_OPTS=(-i "$PEM_KEY" -o StrictHostKeyChecking=accept-new -o LogLevel=ERROR)

# ── Style ────────────────────────────────────────────────────────────
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

# ════════════════════════════════════════════════════════════════════
# Subcommand: deploy
# ════════════════════════════════════════════════════════════════════
LOCAL_SHA=""; TARGET_SHA=""; PRIOR_SHA=""; DEPLOYED_SHA=""; SKIP_BUILD=0; FORCE="0"; CLEAN="0"

dep_preflight() {
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

  # Surface disk usage early so the user sees pressure before pip
  # downloads 200 MB and the build crashes on layer-extract with
  # 'no space left on device'.
  step "Remote disk usage on /"
  ssh_remote "df -h / | awk 'NR==2 {printf \"      %s used, %s avail (%s of %s)\n\", \$3, \$4, \$5, \$2}'"
  # Pull the avail-in-GB integer; warn if it's tight.
  local avail_g
  avail_g=$(ssh_remote "df -BG / | awk 'NR==2 {gsub(/G/, \"\", \$4); print \$4}'" 2>/dev/null || echo "")
  if [[ -n "$avail_g" && "$avail_g" =~ ^[0-9]+$ && "$avail_g" -lt 5 ]]; then
    warn "Less than 5 GB free — Docker builds typically need 3-4 GB headroom."
    warn "Re-run with --clean to docker-system-prune before building."
  fi
}

# Reclaim disk space on the remote. Two modes:
#   default → docker image prune -f + docker builder prune -f
#             (safe: only removes dangling images / unreferenced build cache)
#   --clean → docker system prune -af + docker volume prune -f
#             (aggressive: removes ALL unused images, networks, volumes)
dep_reclaim_disk() {
  # ${1:-} so the default 'safe' call (no arg) doesn't trip `set -u`.
  local mode="${1:-}"
  if [[ "$mode" == "aggressive" ]]; then
    step "Reclaiming disk (aggressive — docker system prune -af + volumes)"
    ssh_remote "docker system prune -af 2>&1 | tail -3" | sed 's/^/      /'
    ssh_remote "docker volume prune -f 2>&1 | tail -3" | sed 's/^/      /'
  else
    step "Reclaiming disk (dangling images + build cache)"
    ssh_remote "docker image prune -f 2>&1 | tail -3" | sed 's/^/      /'
    ssh_remote "docker builder prune -f 2>&1 | tail -3" | sed 's/^/      /'
  fi
  ssh_remote "df -h / | awk 'NR==2 {printf \"      after: %s used, %s avail\n\", \$3, \$4}'"
}

dep_validate_env() {
  step "Validate remote .env.prod"

  # CRITICAL — app literally cannot start without these.
  #   * DJANGO_SECRET_KEY: signs sessions, password-reset URLs, etc.
  #   * JWT_SIGNING_KEY: signs API auth tokens.
  #   * DB_PASSWORD: required for Postgres connection.
  # PROVIDER — third-party / feature-degrades on absence.
  #   * FIELD_ENCRYPTION_KEY: EncryptedTextField falls back to
  #     plaintext when empty (see core/encryption/field_encryption.py
  #     — _get_fernet returns None, save/read becomes a pass-through),
  #     so app starts fine. Warn but don't block. Security caveat:
  #     API keys/OAuth tokens/webhook URLs land in the DB as
  #     plaintext until you set the key.
  # OPTIONAL — billing, OAuth, etc.
  local CRITICAL_STR="DJANGO_SECRET_KEY JWT_SIGNING_KEY DB_PASSWORD"
  local PROVIDER_STR="FIELD_ENCRYPTION_KEY ANTHROPIC_API_KEY OPENAI_API_KEY GEMINI_API_KEY PERPLEXITY_API_KEY GOOGLE_API_KEY|GOOGLE_SEARCH_API_KEY GOOGLE_CSE_ID|GOOGLE_SEARCH_ENGINE_ID"
  local OPTIONAL_STR="DEEPSEEK_API_KEY SERPAPI_KEY STRIPE_SECRET_KEY SENDGRID_API_KEY GOOGLE_OAUTH_CLIENT_ID GOOGLE_CSE_DAILY_LIMIT_PER_USER CLAUDE_JUDGE_DAILY_LIMIT_PER_USER CLAUDE_REWRITE_DAILY_LIMIT_PER_USER"

  # macOS ships bash 3.2 which mis-parses heredocs inside command
  # substitution when the body contains ')' (every case pattern).
  # Write the remote script to a tempfile and pipe it via stdin
  # instead. Works on every bash from 3.2 upward.
  local _tmp_remote
  _tmp_remote=$(mktemp)
  cat > "$_tmp_remote" <<REMOTE
set -e
cd "$REMOTE_DIR"

# Slot lists arrive as QUOTED string assignments so the '|' chars
# in alias slots (GOOGLE_API_KEY|GOOGLE_SEARCH_API_KEY) are just
# data, not pipeline operators. The for-loops below reference
# these variables at runtime; word-splitting on whitespace gives
# us one slot per loop iteration, and the embedded '|' survives
# untouched into resolve_slot().
CRITICAL_STR="$CRITICAL_STR"
PROVIDER_STR="$PROVIDER_STR"
OPTIONAL_STR="$OPTIONAL_STR"

if [ ! -f .env.prod ]; then
  echo "MISSING_FILE"
  exit 0
fi
if grep -q \$'\r' .env.prod 2>/dev/null; then
  TMP=\$(mktemp); tr -d '\r' < .env.prod > "\$TMP"
  set -a; . "\$TMP"; set +a; rm -f "\$TMP"
else
  set -a; . ./.env.prod; set +a
fi

is_placeholder() {
  local v=\$1
  case "\$v" in CHANGE_ME*|change-me*|change_me*) return 0;; esac
  case "\$v" in *...) return 0;; esac
  return 1
}
resolve_slot() {
  local slot=\$1; local IFS='|'; read -ra names <<< "\$slot"; local saw_placeholder=""
  for name in "\${names[@]}"; do
    local val="\${!name:-}"
    if [ -n "\$val" ]; then
      if is_placeholder "\$val"; then saw_placeholder="\$name"; continue; fi
      echo "ok:\$name"; return
    fi
  done
  if [ -n "\$saw_placeholder" ]; then echo "placeholder:\$saw_placeholder"
  else echo "missing:\${names[0]}"; fi
}

crit_missing=""; crit_placeholder=""; prov_missing=""; prov_placeholder=""; optional_missing=""
for slot in \$CRITICAL_STR; do
  res=\$(resolve_slot "\$slot"); s="\${res%%:*}"; n="\${res#*:}"
  case "\$s" in
    missing)     crit_missing="\$crit_missing \$slot" ;;
    placeholder) crit_placeholder="\$crit_placeholder \$n" ;;
  esac
done
for slot in \$PROVIDER_STR; do
  res=\$(resolve_slot "\$slot"); s="\${res%%:*}"; n="\${res#*:}"
  case "\$s" in
    missing)     prov_missing="\$prov_missing \$slot" ;;
    placeholder) prov_placeholder="\$prov_placeholder \$n" ;;
  esac
done
for v in \$OPTIONAL_STR; do
  val="\${!v:-}"
  [ -z "\$val" ] && optional_missing="\$optional_missing \$v"
done

sanity_warn=""
if [[ "\${DJANGO_SETTINGS_MODULE:-}" == *.dev || "\${DJANGO_SETTINGS_MODULE:-}" == *.development ]]; then
  sanity_warn="\$sanity_warn DJANGO_SETTINGS_MODULE=\${DJANGO_SETTINGS_MODULE}_(should-be-config.settings.prod);"
fi
case "\${DEBUG:-}" in
  True|true|1|yes) sanity_warn="\$sanity_warn DEBUG=\${DEBUG}_(must-be-False-in-prod);" ;;
esac
if [[ "\${ALLOWED_HOSTS:-}" == "localhost"* || "\${ALLOWED_HOSTS:-}" == *"127.0.0.1"* ]] \
   && [[ "\${ALLOWED_HOSTS:-}" != *","* ]]; then
  sanity_warn="\$sanity_warn ALLOWED_HOSTS=\${ALLOWED_HOSTS}_(missing-prod-domain);"
fi

duplicates=\$(tr -d '\r' < .env.prod \
  | grep -E '^[[:space:]]*[A-Za-z_][A-Za-z0-9_]*=' \
  | sed -E 's/^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)=.*/\1/' \
  | sort | uniq -d | tr '\n' ' ')

echo "CRIT_MISSING:\$crit_missing"
echo "CRIT_PLACEHOLDER:\$crit_placeholder"
echo "PROV_MISSING:\$prov_missing"
echo "PROV_PLACEHOLDER:\$prov_placeholder"
echo "OPTIONAL_MISSING:\$optional_missing"
echo "SANITY:\$sanity_warn"
echo "DUPLICATES:\$duplicates"
REMOTE
  local out
  out=$(ssh "${SSH_OPTS[@]}" "$EC2_USER@$EC2_HOST" bash -s < "$_tmp_remote")
  rm -f "$_tmp_remote"

  if grep -q "^MISSING_FILE$" <<<"$out"; then
    die ".env.prod missing at $EC2_HOST:$REMOTE_DIR — create it from .env.prod.example first."
  fi
  local crit_missing crit_placeholder prov_missing prov_placeholder
  local optional_missing sanity duplicates
  crit_missing=$(grep "^CRIT_MISSING:"     <<<"$out" | cut -d: -f2-)
  crit_placeholder=$(grep "^CRIT_PLACEHOLDER:" <<<"$out" | cut -d: -f2-)
  prov_missing=$(grep "^PROV_MISSING:"     <<<"$out" | cut -d: -f2-)
  prov_placeholder=$(grep "^PROV_PLACEHOLDER:" <<<"$out" | cut -d: -f2-)
  optional_missing=$(grep "^OPTIONAL_MISSING:"  <<<"$out" | cut -d: -f2-)
  sanity=$(grep "^SANITY:"     <<<"$out" | cut -d: -f2-)
  duplicates=$(grep "^DUPLICATES:" <<<"$out" | cut -d: -f2-)

  if [[ -n "${prov_missing// }" || -n "${prov_placeholder// }" ]]; then
    warn "Provider API keys absent or placeholder — those features will be disabled:"
    [[ -n "${prov_missing// }" ]]     && printf "      %sMissing:%s            %s\n" "$Y" "$N" "$prov_missing"
    [[ -n "${prov_placeholder// }" ]] && printf "      %sStill a placeholder:%s %s\n" "$Y" "$N" "$prov_placeholder"
  fi
  if [[ -n "${optional_missing// }" ]]; then
    warn "Optional keys not set (defaults will apply):$optional_missing"
  fi
  if [[ -n "${duplicates// }" ]]; then
    warn "Keys defined more than once (last definition wins): $duplicates"
  fi
  if [[ -n "${sanity// }" ]]; then
    if [[ "$FORCE" == "1" ]]; then
      warn "Production sanity check (overridden by --force):"
    else
      warn "Production sanity check — this looks like a dev .env on a prod host:"
    fi
    for item in $sanity; do
      printf "      %s%s%s\n" "$Y" "${item//_/ }" "$N"
    done
  fi
  if [[ -n "${crit_missing// }" || -n "${crit_placeholder// }" ]]; then
    if [[ "$FORCE" == "1" ]]; then
      warn "Critical secrets missing/placeholder — proceeding anyway (--force):"
      [[ -n "${crit_missing// }" ]]     && printf "      %sMissing:%s            %s\n" "$Y" "$N" "$crit_missing"
      [[ -n "${crit_placeholder// }" ]] && printf "      %sStill a placeholder:%s %s\n" "$Y" "$N" "$crit_placeholder"
    else
      err "Critical secrets missing or placeholder — deploy refused:"
      [[ -n "${crit_missing// }" ]]     && printf "      %sMissing:%s            %s\n" "$R" "$N" "$crit_missing"
      [[ -n "${crit_placeholder// }" ]] && printf "      %sStill a placeholder:%s %s\n" "$R" "$N" "$crit_placeholder"
      echo ""
      printf "      Without these the app cannot start (DJANGO_SECRET_KEY,\n"
      printf "      JWT_SIGNING_KEY, DB_PASSWORD).\n\n"
      printf "      %sInspect what is actually set (names only):%s\n" "$Y" "$N"
      printf "         bash scripts/deploy.sh deploy --inspect-env\n\n"
      printf "      %sFix the file in place:%s\n" "$Y" "$N"
      printf "         ssh -i %s %s@%s 'sudo nano %s/.env.prod'\n\n" "$PEM_KEY" "$EC2_USER" "$EC2_HOST" "$REMOTE_DIR"
      printf "      %sOr bypass (NOT for production traffic):%s\n" "$Y" "$N"
      printf "         bash scripts/deploy.sh deploy --force\n"
      exit 1
    fi
  fi
  ok ".env.prod accepted"
}

dep_capture_prior() {
  step "Capture current production state"
  PRIOR_SHA=$(ssh_remote "cd $REMOTE_DIR && git rev-parse HEAD" 2>/dev/null || echo "unknown")
  ok "Remote HEAD before deploy: ${PRIOR_SHA:0:12}"
  if [[ "$PRIOR_SHA" == "$TARGET_SHA" ]]; then
    warn "Remote already at target SHA — nothing new to ship."
    read -r -p "    Force rebuild anyway? [y/N] " ans
    [[ "$ans" =~ ^[Yy] ]] && SKIP_BUILD=0 || SKIP_BUILD=1
  fi
}

dep_deploy() {
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

  # Reclaim disk before building. With --clean, run the aggressive
  # 'docker system prune -af'; otherwise just prune dangling images +
  # build cache. Either way prevents the 'no space left on device'
  # extract-layer failure that bit us last deploy.
  if [[ "$CLEAN" == "1" ]]; then
    dep_reclaim_disk aggressive
  else
    dep_reclaim_disk
  fi

  local cache_bust; cache_bust=$(date +%s)

  step "Rebuild backend (web + celery)"
  remote_compose "build --build-arg CACHE_DATE=$cache_bust web celery"
  remote_compose "up -d web celery"
  ok "Backend rebuilt and restarted"

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

dep_validate_deploy() {
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
  if [[ "$http" == "200" ]]; then ok "Health endpoint: HTTP 200"
  else warn "Health endpoint: HTTP $http"; fi
  local celery_pong
  celery_pong=$(remote_compose "exec -T celery celery -A config.celery inspect ping --timeout 5" 2>/dev/null \
                | grep -c "pong" || true)
  if [[ "${celery_pong:-0}" -gt 0 ]]; then ok "Celery worker responding"
  else warn "Celery ping failed (worker may still be warming up)"; fi
}

dep_smoke_test() {
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
    if [[ "$got" == "$expected" ]]; then ok "$desc → $got"
    else err "$desc → got $got (expected $expected)"; FAIL=$((FAIL + 1)); fi
  done
  local post_got
  post_got=$(curl -s -X POST -H "Content-Type: application/json" \
    -d '{"plan":"pro"}' -o /dev/null -w "%{http_code}" \
    "${PUBLIC_HOST}/api/v1/billing/checkout/" || echo "000")
  if [[ "$post_got" == "401" ]]; then ok "POST /billing/checkout/ {pro} → 401 (plan accepted)"
  else err "POST /billing/checkout/ {pro} → $post_got (expected 401; 400 = old code)"; FAIL=$((FAIL + 1)); fi
  if [[ $FAIL -gt 0 ]]; then err "Smoke test failed — $FAIL check(s) regressed."; return 1; fi
  ok "All endpoints responding as expected."
  return 0
}

dep_tail_logs() {
  step "Tail container logs for 60s (Ctrl+C to stop earlier)"
  remote_compose "logs --tail=50 --follow --timestamps" &
  local pid=$!
  sleep 60
  kill "$pid" 2>/dev/null || true
  wait "$pid" 2>/dev/null || true
}

dep_inspect_env() {
  step "Inspect remote .env.prod"
  ssh "${SSH_OPTS[@]}" "$EC2_USER@$EC2_HOST" bash -s <<REMOTE
set -e
cd "$REMOTE_DIR"
if [ ! -f .env.prod ]; then
  echo "no .env.prod found at $REMOTE_DIR"; exit 1
fi
echo "Keys defined in $REMOTE_DIR/.env.prod (names only):"
echo "──────────────────────────────────────────────────────"
tr -d '\r' < .env.prod \
  | grep -E '^[[:space:]]*[A-Za-z_][A-Za-z0-9_]*=' \
  | sed -E 's/^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)=.*/  \1/' \
  | sort -u
echo "──────────────────────────────────────────────────────"
echo "Total: \$(tr -d '\r' < .env.prod | grep -cE '^[[:space:]]*[A-Za-z_][A-Za-z0-9_]*=') keys"
REMOTE
}

cmd_deploy() {
  local sub_mode="full"
  for arg in "$@"; do
    case "$arg" in
      --force)        FORCE="1" ;;
      --clean)        CLEAN="1" ;;
      --no-test)      sub_mode="deploy" ;;
      --test)         sub_mode="test" ;;
      --logs)         sub_mode="logs" ;;
      --inspect-env)  sub_mode="inspect" ;;
      --full|"")      ;;
      *) echo "Unknown deploy flag: $arg"; exit 1 ;;
    esac
  done
  banner "FetchBot Deploy — branch=$BRANCH"
  case "$sub_mode" in
    test)    dep_smoke_test; exit $? ;;
    logs)    dep_tail_logs; exit 0 ;;
    inspect) dep_inspect_env; exit 0 ;;
    deploy|full)
      dep_preflight
      dep_validate_env
      dep_capture_prior
      dep_deploy
      dep_validate_deploy
      if [[ "$sub_mode" == "full" ]]; then
        if ! dep_smoke_test; then
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
}

# ════════════════════════════════════════════════════════════════════
# Subcommand: dev (local Django + Celery worker + beat)
# ════════════════════════════════════════════════════════════════════
cmd_dev() {
  local START_BEAT=1 WEB_ONLY=0
  for arg in "$@"; do
    case "$arg" in
      --no-beat)   START_BEAT=0 ;;
      --web-only)  WEB_ONLY=1 ;;
      *) echo "Unknown dev flag: $arg"; exit 1 ;;
    esac
  done

  cd "$REPO_DIR"
  if [[ ! -f ".venv/bin/activate" ]]; then
    err ".venv not found at ${REPO_DIR}/.venv"
    echo "    Create it with:  python3.12 -m venv .venv && source .venv/bin/activate && pip install -r requirements/dev.txt"
    exit 1
  fi
  # shellcheck disable=SC1091
  source .venv/bin/activate
  ok "venv activated ($(python --version))"

  mkdir -p tmp
  local PIDS=()
  cleanup_dev() {
    echo ""
    step "stopping background services…"
    for pid in "${PIDS[@]:-}"; do
      [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null && kill "$pid" 2>/dev/null || true
    done
  }
  trap cleanup_dev EXIT INT TERM

  if [[ $WEB_ONLY -eq 0 ]]; then
    step "starting Celery worker (logs: tmp/dev-worker.log)"
    celery -A config worker \
      -Q ai,default,integrations,webhooks -l info \
      >tmp/dev-worker.log 2>&1 &
    PIDS+=($!)
    if [[ $START_BEAT -eq 1 ]]; then
      step "starting Celery beat (logs: tmp/dev-beat.log)"
      celery -A config beat -l info >tmp/dev-beat.log 2>&1 &
      PIDS+=($!)
    fi
  fi

  step "starting Django dev server on http://localhost:8000"
  warn "(ctrl-c to stop everything)"
  python manage.py runserver
}

# ════════════════════════════════════════════════════════════════════
# Subcommand: migrate (local Django migrations)
# ════════════════════════════════════════════════════════════════════
cmd_migrate() {
  local DRY_RUN=0
  for arg in "$@"; do
    case "$arg" in
      --check|-n) DRY_RUN=1 ;;
      *) echo "Unknown migrate flag: $arg"; exit 1 ;;
    esac
  done

  cd "$REPO_DIR"
  [[ -f manage.py ]] || die "manage.py not found in $REPO_DIR"

  # Activate venv: .venv, then venv, then env. Fall back to system python with a warning.
  local activated=""
  for cand in .venv venv env; do
    if [[ -f "$REPO_DIR/$cand/bin/activate" ]]; then
      # shellcheck disable=SC1090
      source "$REPO_DIR/$cand/bin/activate"
      activated="$cand"
      break
    fi
  done
  if [[ -n "$activated" ]]; then
    ok "venv activated: $activated/ ($(python --version 2>&1))"
  else
    warn "No project venv found — falling back to system Python: $(command -v python || echo NONE)"
  fi
  command -v python >/dev/null || die "python not on PATH"
  python -c "import django, environ" 2>/dev/null \
    || die "Django/django-environ not installed in the active Python. Run: pip install -r requirements/dev.txt"

  export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings.dev}"
  ok "DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE"

  step "Pending migrations"
  python manage.py showmigrations --plan 2>&1 | grep -E '^\[ \]' || echo "  (none — head is clean)"

  if [[ $DRY_RUN -eq 1 ]]; then
    ok "Dry-run mode — nothing applied."
    exit 0
  fi

  step "Applying migrations"
  python manage.py migrate

  step "Verifying head"
  local pending
  pending=$(python manage.py showmigrations --plan | grep -c '^\[ \]' || true)
  if [[ "$pending" -gt 0 ]]; then
    warn "$pending migration(s) still pending."
  else
    ok "All migrations applied."
  fi
}

# ════════════════════════════════════════════════════════════════════
# Subcommand: seed (dev DB)
# ════════════════════════════════════════════════════════════════════
cmd_seed() {
  cd "$REPO_DIR"
  for cand in .venv venv env; do
    [[ -f "$REPO_DIR/$cand/bin/activate" ]] && source "$REPO_DIR/$cand/bin/activate" && break
  done
  step "Seeding dev DB"
  DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings.dev}" \
    python <<'PYEOF'
import os, sys, django
sys.path.insert(0, os.getcwd())
django.setup()
from apps.accounts.models import User
from apps.websites.models import Website, WebsiteSettings

admin, c = User.objects.get_or_create(
    email="admin@growthpilot.io",
    defaults={"full_name": "Admin User", "company_name": "GrowthPilot",
              "plan": "scale", "is_staff": True, "is_superuser": True,
              "is_email_verified": True},
)
if c:
    admin.set_password("AdminPass123!"); admin.save()
    print(f"  created admin: {admin.email}")
else:
    print(f"  admin already exists: {admin.email}")

demo, c = User.objects.get_or_create(
    email="demo@example.com",
    defaults={"full_name": "Demo User", "company_name": "Acme Corp",
              "plan": "growth", "is_email_verified": True},
)
if c:
    demo.set_password("DemoPass123!"); demo.save()
    print(f"  created demo user: {demo.email}")

site, c = Website.objects.get_or_create(
    user=demo, url="https://demo.example.com",
    defaults={"name": "Demo Website", "industry": "SaaS"},
)
if c:
    WebsiteSettings.objects.get_or_create(website=site)
    print(f"  created website: {site.name}")

print("seed complete")
PYEOF
  ok "seed done"
}

# ════════════════════════════════════════════════════════════════════
# Subcommand: eval (NDCG@5 / MRR over completed audits)
# ════════════════════════════════════════════════════════════════════
cmd_eval() {
  cd "$REPO_DIR"
  for cand in .venv venv env; do
    [[ -f "$REPO_DIR/$cand/bin/activate" ]] && source "$REPO_DIR/$cand/bin/activate" && break
  done
  step "Ranking eval (NDCG@5 / MRR)"
  DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings.dev}" \
    python <<'PYEOF'
import math, os, sys, django
from collections import defaultdict
sys.path.insert(0, os.getcwd())
django.setup()

def dcg(rels): return sum(r / math.log2(i + 2) for i, r in enumerate(rels))
def ndcg_at_k(pred, rel, k=5):
    pr = [rel.get(b, 0.0) for b in pred[:k]]
    ir = sorted(rel.values(), reverse=True)[:k]
    idcg = dcg(ir)
    return dcg(pr) / idcg if idcg > 0 else 0.0

from apps.llm_ranking.models import LLMRankingAudit
limit = int(os.environ.get("EVAL_LIMIT", "200"))
audits = (LLMRankingAudit.objects
          .filter(status=LLMRankingAudit.STATUS_COMPLETED)
          .prefetch_related("results")
          .order_by("-created_at")[:limit])

ndcgs, mrrs, with_signal = [], [], 0
for a in audits:
    strengths = a.brand_strengths or {}
    if not strengths: continue
    with_signal += 1
    predicted = sorted(strengths, key=strengths.get, reverse=True)
    per_prompt = defaultdict(list)
    for r in a.results.all():
        if not (r.query_succeeded and r.mention_rank): continue
        if r.is_mentioned:
            per_prompt[r.prompt].append((a.business_name, int(r.mention_rank)))
        for c in r.competitors_mentioned or []:
            if not isinstance(c, dict): continue
            pos = c.get("position"); name = (c.get("name") or "").strip()
            if name and pos:
                try: per_prompt[r.prompt].append((name, int(pos)))
                except (TypeError, ValueError): continue
    for items in per_prompt.values():
        if not items: continue
        agg = defaultdict(list)
        for b, p in items: agg[b].append(p)
        rel = {b: 1.0 / (sum(ps) / len(ps)) for b, ps in agg.items()}
        ndcgs.append(ndcg_at_k(predicted, rel, k=5))
        if a.business_name in predicted:
            mrrs.append(1.0 / (predicted.index(a.business_name) + 1))

print(f"Audits evaluated:   {with_signal}")
print(f"Prompts evaluated:  {len(ndcgs)}")
print(f"NDCG@5:             {(sum(ndcgs)/len(ndcgs)) if ndcgs else 0:.3f}")
print(f"MRR:                {(sum(mrrs)/len(mrrs)) if mrrs else 0:.3f}")
PYEOF
}

# ════════════════════════════════════════════════════════════════════
# Subcommand: health (container DB+cache probe, exits 0/1)
# ════════════════════════════════════════════════════════════════════
cmd_health() {
  DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings.prod}" \
    python <<'PYEOF'
import os, sys, django
django.setup()
try:
    from django.db import connection
    connection.ensure_connection()
    from django.core.cache import cache
    cache.set("health_check", "ok", 30)
    assert cache.get("health_check") == "ok"
    print("Health check passed.")
    sys.exit(0)
except Exception as e:
    print(f"Health check failed: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF
}

# ════════════════════════════════════════════════════════════════════
# Subcommand: install-hooks (write git pre-commit into .git/hooks)
# ════════════════════════════════════════════════════════════════════
# The hook body is embedded right here so this single script is the
# ONLY thing under scripts/. Running install-hooks materializes the
# hook file into the repo's .git/hooks/ directory.
cmd_install_hooks() {
  cd "$REPO_DIR"
  local dst="$REPO_DIR/.git/hooks"
  [[ -d "$dst" ]] || die "not a git checkout (.git/hooks missing)"
  step "Writing pre-commit hook → $dst/pre-commit"
  cat > "$dst/pre-commit" <<'HOOK'
#!/usr/bin/env bash
# Block any .env-shaped file from being committed. Generated by
# scripts/deploy.sh install-hooks — edit there, not here.
BLOCKED_PATTERNS=(
  '\.env$'
  '\.env\.'
  '\.env\.prod'
  '\.env\.production'
  '\.env\.example'
  '\.env\..*\.example'
  '\.env\.local'
  '\.env\.staging'
)
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACR)
BLOCKED_FILES=()
for file in $STAGED_FILES; do
  for pattern in "${BLOCKED_PATTERNS[@]}"; do
    if echo "$file" | grep -qE "(^|/)$pattern"; then
      BLOCKED_FILES+=("$file")
      break
    fi
  done
done
if [ ${#BLOCKED_FILES[@]} -gt 0 ]; then
  echo "ERROR: Commit blocked by pre-commit hook."
  echo ""
  echo "The following environment files must not be committed:"
  for f in "${BLOCKED_FILES[@]}"; do echo "  - $f"; done
  echo ""
  echo "These files may contain secrets. Unstage with: git reset HEAD <file>"
  exit 1
fi
exit 0
HOOK
  chmod +x "$dst/pre-commit"
  ok "pre-commit hook installed"
}

# ════════════════════════════════════════════════════════════════════
# Help
# ════════════════════════════════════════════════════════════════════
usage() {
  sed -n '3,33p' "$0"
}

# ════════════════════════════════════════════════════════════════════
# Dispatcher
# ════════════════════════════════════════════════════════════════════
case "${1:-}" in
  ""|--full|--no-test|--test|--logs|--inspect-env|--force)
    cmd_deploy "$@" ;;
  deploy)        shift; cmd_deploy "$@" ;;
  dev)           shift; cmd_dev "$@" ;;
  migrate)       shift; cmd_migrate "$@" ;;
  seed)          shift; cmd_seed ;;
  eval)          shift; cmd_eval ;;
  health)        shift; cmd_health ;;
  install-hooks) shift; cmd_install_hooks ;;
  help|-h|--help) usage; exit 0 ;;
  *) echo "Unknown command: $1"; echo ""; usage; exit 1 ;;
esac
