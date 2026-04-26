#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════
#  FetchBot — Deploy & Monitor
#  One script. Deploys frontend + backend to the EC2 host using the
#  current origin/main, validates that the running code matches, then
#  drops into an interactive menu for tailing per-container logs.
#
#  Usage:   bash scripts/deploy_and_monitor.sh
#  Env:     EC2_HOST, EC2_USER, PEM_KEY, REMOTE_DIR, BRANCH (all optional)
# ════════════════════════════════════════════════════════════════════

set -euo pipefail

# ── Config ──────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

EC2_HOST="${EC2_HOST:-100.31.135.211}"
EC2_USER="${EC2_USER:-ubuntu}"
PEM_KEY="${PEM_KEY:-$REPO_DIR/fynda-deploy.pem}"
REMOTE_DIR="${REMOTE_DIR:-/opt/fetchbot/ftb-api-26}"
COMPOSE_FILE="docker/docker-compose.prod.yml"
BRANCH="${BRANCH:-main}"

SSH_OPTS=(-i "$PEM_KEY" -o StrictHostKeyChecking=accept-new -o LogLevel=ERROR)
ssh_remote()      { ssh "${SSH_OPTS[@]}" "$EC2_USER@$EC2_HOST" "$@"; }
ssh_remote_tty()  { ssh "${SSH_OPTS[@]}" -t "$EC2_USER@$EC2_HOST" "$@"; }
remote_compose()  { ssh_remote "cd $REMOTE_DIR && docker compose -f $COMPOSE_FILE $*"; }

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
ask()  {
  local prompt="$1" reply
  printf "%s? %s %s" "$Y" "$prompt" "$N" >&2
  read -r reply
  printf "%s" "$reply"
}

# State carried between phases
LOCAL_SHA=""; TARGET_SHA=""; PRIOR_SHA=""; DEPLOYED_SHA=""; SKIP_BUILD=0

# ────────────────────────────────────────────────────────────────────
# Phase 1: Pre-flight (local)
# ────────────────────────────────────────────────────────────────────
preflight() {
  step "Pre-flight (local)"
  [[ -f "$PEM_KEY" ]] || die "PEM key not found: $PEM_KEY"
  command -v git >/dev/null || die "git not installed"
  command -v ssh >/dev/null || die "ssh not installed"
  chmod 600 "$PEM_KEY" 2>/dev/null || true

  cd "$REPO_DIR"
  git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "$REPO_DIR is not a git repo"

  LOCAL_SHA=$(git rev-parse HEAD)
  ok "Local HEAD: $LOCAL_SHA ($(git log -1 --format=%s))"

  if ! git diff --quiet || ! git diff --cached --quiet || [[ -n "$(git ls-files --others --exclude-standard)" ]]; then
    warn "Working tree is DIRTY — these changes will NOT be deployed (git pull only ships committed code):"
    git status --short | sed 's/^/      /'
    [[ "$(ask "Continue anyway? [y/N]")" =~ ^[Yy] ]] || die "Aborted."
  else
    ok "Working tree clean"
  fi

  step "Sync with origin/$BRANCH"
  git fetch origin "$BRANCH" --quiet
  local local_b remote_b
  local_b=$(git rev-parse "$BRANCH" 2>/dev/null || echo "")
  remote_b=$(git rev-parse "origin/$BRANCH")
  if [[ -z "$local_b" ]]; then
    warn "Local $BRANCH not found; deploying origin/$BRANCH"
  elif [[ "$local_b" != "$remote_b" ]]; then
    if git merge-base --is-ancestor "$remote_b" "$local_b"; then
      warn "Local $BRANCH has unpushed commits ahead of origin/$BRANCH"
      if [[ "$(ask "Push to origin/$BRANCH now? [y/N]")" =~ ^[Yy] ]]; then
        git push origin "$BRANCH"
        ok "Pushed."
      else
        warn "Skipping push — remote will deploy origin/$BRANCH (older than local)."
      fi
    else
      warn "Local $BRANCH is BEHIND origin/$BRANCH"
      [[ "$(ask "Continue with origin/$BRANCH? [y/N]")" =~ ^[Yy] ]] || die "Aborted."
    fi
  else
    ok "Local $BRANCH matches origin/$BRANCH"
  fi
  TARGET_SHA=$(git rev-parse "origin/$BRANCH")
  ok "Target deploy SHA: $TARGET_SHA"

  step "SSH connectivity"
  ssh_remote "echo ok" >/dev/null 2>&1 || die "Cannot SSH to $EC2_USER@$EC2_HOST"
  ok "Reachable: $EC2_USER@$EC2_HOST"
}

# ────────────────────────────────────────────────────────────────────
# Phase 2: Capture current production state
# ────────────────────────────────────────────────────────────────────
capture_prior() {
  step "Capture current production state"
  PRIOR_SHA=$(ssh_remote "cd $REMOTE_DIR && git rev-parse HEAD" 2>/dev/null || echo "unknown")
  ok "Remote HEAD before deploy: $PRIOR_SHA"
  if [[ "$PRIOR_SHA" == "$TARGET_SHA" ]]; then
    warn "Remote already at target SHA — nothing new to ship."
    if [[ "$(ask "Force rebuild containers anyway? [y/N]")" =~ ^[Yy] ]]; then
      SKIP_BUILD=0
    else
      SKIP_BUILD=1
    fi
  fi
}

# ────────────────────────────────────────────────────────────────────
# Phase 3: Deploy (backend + frontend)
# ────────────────────────────────────────────────────────────────────
deploy() {
  step "Pull latest code on remote"
  ssh_remote "cd $REMOTE_DIR && git fetch origin $BRANCH --quiet && git checkout $BRANCH && git reset --hard origin/$BRANCH"
  local new_sha
  new_sha=$(ssh_remote "cd $REMOTE_DIR && git rev-parse HEAD")
  [[ "$new_sha" == "$TARGET_SHA" ]] || die "Remote SHA mismatch after pull (got $new_sha, expected $TARGET_SHA)"
  ok "Remote now at $new_sha"

  if [[ "$SKIP_BUILD" == "1" ]]; then
    warn "Skipping container rebuild"
    return
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
  remote_compose "exec -T web python manage.py collectstatic --noinput" >/dev/null 2>&1 || true
  ok "Migrations applied"
}

# ────────────────────────────────────────────────────────────────────
# Phase 4: Post-deploy validation
# ────────────────────────────────────────────────────────────────────
validate() {
  step "Post-deploy validation"

  DEPLOYED_SHA=$(ssh_remote "cd $REMOTE_DIR && git rev-parse HEAD")
  if [[ "$DEPLOYED_SHA" == "$TARGET_SHA" ]]; then
    ok "Deployed SHA matches target ($DEPLOYED_SHA)"
  else
    err "SHA mismatch: deployed=$DEPLOYED_SHA target=$TARGET_SHA"
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
  remote_compose "ps --format 'table {{.Service}}\t{{.State}}\t{{.Status}}'" | sed 's/^/      /'

  local http; http=$(ssh_remote "curl -s -o /dev/null -w '%{http_code}' http://localhost/health/" 2>/dev/null || echo "000")
  if [[ "$http" == "200" ]]; then
    ok "Health endpoint: HTTP 200"
  else
    warn "Health endpoint: HTTP $http"
  fi

  local celery_pong
  celery_pong=$(remote_compose "exec -T celery celery -A config.celery inspect ping --timeout 5" 2>/dev/null \
                | grep -c "pong" || true)
  if [[ "${celery_pong:-0}" -gt 0 ]]; then
    ok "Celery worker responding to ping"
  else
    warn "Celery ping failed (worker may still be starting)"
  fi

  local front_age
  front_age=$(ssh_remote "stat -c %Y /var/lib/docker/volumes/*frontend_dist*/_data/index.html 2>/dev/null \
                          || docker exec \$(docker ps -qf name=nginx) stat -c %Y /usr/share/nginx/html/index.html 2>/dev/null \
                          || echo 0")
  if [[ "${front_age:-0}" -gt 0 ]]; then
    local age_min=$(( ($(date +%s) - front_age) / 60 ))
    if [[ $age_min -lt 10 ]]; then
      ok "Frontend bundle is fresh (built ${age_min}m ago)"
    else
      warn "Frontend bundle is ${age_min}m old — rebuild may not have run"
    fi
  fi
}

# ────────────────────────────────────────────────────────────────────
# Phase 5: Interactive log viewer
# ────────────────────────────────────────────────────────────────────
declare -a SVC_NAMES=()

refresh_services() {
  SVC_NAMES=()
  local line
  while IFS= read -r line; do
    [[ -n "$line" ]] && SVC_NAMES+=("$line")
  done < <(remote_compose "ps --services" 2>/dev/null | sort)
}

print_menu() {
  clear
  banner "FetchBot Deploy & Monitor"
  printf "  %sHost:%s   %s@%s\n" "$B" "$N" "$EC2_USER" "$EC2_HOST"
  printf "  %sBefore:%s %s\n" "$B" "$N" "${PRIOR_SHA:0:12}"
  printf "  %sNow:%s    %s\n" "$B" "$N" "${DEPLOYED_SHA:0:12}"
  printf "\n  %sContainers:%s\n" "$B" "$N"

  local statuses; statuses=$(remote_compose "ps --format '{{.Service}}|{{.State}}|{{.Status}}'" 2>/dev/null || true)
  local i=1 svc state status color line
  for svc in "${SVC_NAMES[@]}"; do
    line=$(printf "%s\n" "$statuses" | awk -F'|' -v s="$svc" '$1==s {print; exit}')
    state=$(printf "%s" "$line" | awk -F'|' '{print $2}')
    status=$(printf "%s" "$line" | awk -F'|' '{print $3}')
    [[ -z "$state" ]] && state="absent"
    color="$G"; [[ "$state" != "running" ]] && color="$R"
    printf "    %s%2d)%s %-12s %s%-10s%s %s%s%s\n" \
      "$B" "$i" "$N" "$svc" "$color" "$state" "$N" "$D" "$status" "$N"
    ((i++))
  done

  printf "\n  %sActions:%s\n" "$B" "$N"
  printf "    %s a)%s tail ALL containers (combined)\n" "$B" "$N"
  printf "    %s e)%s tail only ERROR/WARN lines across all containers\n" "$B" "$N"
  printf "    %s r)%s refresh status\n" "$B" "$N"
  printf "    %s d)%s redeploy (re-run pull + build + validate)\n" "$B" "$N"
  printf "    %s x)%s exec shell on a container\n" "$B" "$N"
  printf "    %s q)%s quit\n\n" "$B" "$N"
}

choose_lines() {
  local n
  n=$(ask "How many lines to tail? [200]")
  [[ -z "$n" ]] && n=200
  [[ "$n" =~ ^[0-9]+$ ]] || n=200
  printf "%s" "$n"
}

view_logs() {
  local svc="$1" lines="$2"
  clear
  printf "%s%s── Tailing logs: %s (last %s lines, follow mode)%s\n" "$C" "$B" "$svc" "$lines" "$N"
  printf "%s    Press Ctrl-C to return to menu%s\n\n" "$Y" "$N"
  trap 'printf "\n  returning to menu...\n"; sleep 1' INT
  if [[ "$svc" == "ALL" ]]; then
    ssh_remote_tty "cd $REMOTE_DIR && docker compose -f $COMPOSE_FILE logs -f --tail=$lines" || true
  else
    ssh_remote_tty "cd $REMOTE_DIR && docker compose -f $COMPOSE_FILE logs -f --tail=$lines $svc" || true
  fi
  trap - INT
}

view_errors() {
  local lines="$1"
  clear
  printf "%s%s── ERROR/WARN lines across all containers (last %s lines, follow)%s\n" "$C" "$B" "$lines" "$N"
  printf "%s    Press Ctrl-C to return to menu%s\n\n" "$Y" "$N"
  trap 'printf "\n  returning to menu...\n"; sleep 1' INT
  ssh_remote_tty "cd $REMOTE_DIR && docker compose -f $COMPOSE_FILE logs -f --tail=$lines \
    | grep --color=always -iE 'error|warn|exception|traceback|critical|failed'" || true
  trap - INT
}

exec_shell() {
  local svc="$1"
  clear
  printf "%s%s── Opening shell in %s%s\n\n" "$C" "$B" "$svc" "$N"
  ssh_remote_tty "cd $REMOTE_DIR && docker compose -f $COMPOSE_FILE exec $svc bash 2>/dev/null \
                  || docker compose -f $COMPOSE_FILE exec $svc sh" || true
}

interactive_loop() {
  refresh_services
  while true; do
    refresh_services
    print_menu
    local choice; choice=$(ask "Select")
    case "$choice" in
      q|Q) printf "\n  bye.\n\n"; exit 0 ;;
      r|R) continue ;;
      a|A) view_logs "ALL" "$(choose_lines)" ;;
      e|E) view_errors "$(choose_lines)" ;;
      d|D)
        capture_prior
        deploy
        validate
        printf "\n%s  press ENTER to return to monitor%s" "$Y" "$N"; read -r _
        ;;
      x|X)
        local n; n=$(ask "Container number to shell into")
        [[ "$n" =~ ^[0-9]+$ ]] && [[ -n "${SVC_NAMES[$((n-1))]:-}" ]] \
          && exec_shell "${SVC_NAMES[$((n-1))]}" \
          || { warn "Invalid"; sleep 1; }
        ;;
      ''|*[!0-9]*) warn "Invalid choice"; sleep 1 ;;
      *)
        local idx=$((choice-1))
        if [[ $idx -ge 0 && $idx -lt ${#SVC_NAMES[@]} ]]; then
          view_logs "${SVC_NAMES[$idx]}" "$(choose_lines)"
        else
          warn "No container at index $choice"; sleep 1
        fi
        ;;
    esac
  done
}

# ────────────────────────────────────────────────────────────────────
# main
# ────────────────────────────────────────────────────────────────────
main() {
  banner "FetchBot Deploy & Monitor"
  preflight
  capture_prior
  deploy
  validate
  printf "\n"
  ok "Deploy + validation complete. Entering interactive log viewer..."
  sleep 2
  interactive_loop
}

main "$@"
