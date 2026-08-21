#!/usr/bin/env bash
#
# Interactive create-user helper.
#
# Prompts for env (local / prod), email, password, and full name,
# then creates the user — locally via the venv or on prod via docker
# compose exec. Mirrors scripts/login.sh so the two halves of the
# "I need a user" flow share the same UX.
#
# Public registration is disabled on prod (SIGNUPS_ENABLED=False), so
# this script is the canonical way to provision an account.
#
# Usage:
#   scripts/create_user.sh                                    # full prompts
#   scripts/create_user.sh local                              # skip env prompt
#   scripts/create_user.sh prod ali44@gmail.com Password@44   # skip almost everything
#   scripts/create_user.sh prod ali44@gmail.com Password@44 "Ali Test"

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_DIR"

# ── Style ────────────────────────────────────────────────────────────
B=$'\033[1m'; G=$'\033[0;32m'; Y=$'\033[1;33m'; R=$'\033[0;31m'
C=$'\033[0;36m'; D=$'\033[2m'; N=$'\033[0m'

# ── Prod SSH config (mirrors deploy.sh defaults) ─────────────────────
EC2_HOST="${EC2_HOST:-100.31.135.211}"
EC2_USER="${EC2_USER:-ubuntu}"
PEM_KEY="${PEM_KEY:-$HOME/.ssh/fynda-deploy.pem}"
REMOTE_DIR="${REMOTE_DIR:-/opt/fetchbot/ftb-api-26}"
COMPOSE_FILE="docker/docker-compose.prod.yml"

# ── Args (all optional) ──────────────────────────────────────────────
env_choice="${1:-}"
email_arg="${2:-}"
password_arg="${3:-}"
name_arg="${4:-}"

# ── Env prompt ───────────────────────────────────────────────────────
if [[ -z "$env_choice" ]]; then
  printf "${B}Where do you want to create the user?${N}\n"
  printf "  ${G}1${N} local  (runs against your local DB)\n"
  printf "  ${G}2${N} prod   (SSH into EC2 and create on the live DB)\n"
  printf "Pick [1/2, default 1]: "
  read -r pick
  case "$pick" in
    2|prod) env_choice="prod" ;;
    *)      env_choice="local" ;;
  esac
fi

# ── Credentials prompts ──────────────────────────────────────────────
if [[ -z "$email_arg" ]]; then
  printf "${B}Email:${N} "
  read -r email_arg
fi
[[ -z "$email_arg" ]] && { printf "${R}Email is required.${N}\n" >&2; exit 1; }

if [[ -z "$password_arg" ]]; then
  printf "${B}Password:${N} "
  stty -echo
  read -r password_arg
  stty echo
  printf "\n"
fi
[[ -z "$password_arg" ]] && { printf "${R}Password is required.${N}\n" >&2; exit 1; }

if [[ -z "$name_arg" ]]; then
  printf "${B}Full name${N} ${D}(blank = Test User)${N}: "
  read -r name_arg
  [[ -z "$name_arg" ]] && name_arg="Test User"
fi

# ── Confirm prod ─────────────────────────────────────────────────────
if [[ "$env_choice" == "prod" ]]; then
  printf "\n${Y}About to create ${B}%s${N}${Y} on PROD.${N}\n" "$email_arg"
  printf "Continue? (y/N) "
  read -r ans
  case "$ans" in
    y|Y|yes) ;;
    *) printf "Aborted.\n"; exit 1 ;;
  esac
fi

printf "\n${C}→ creating user...${N}\n"

# ── Local path ───────────────────────────────────────────────────────
if [[ "$env_choice" == "local" ]]; then
  # Prefer the active virtualenv; fall back to system python.
  if [[ -x "$REPO_DIR/venv/bin/python" ]]; then
    py="$REPO_DIR/venv/bin/python"
  else
    py="python3"
  fi
  "$py" scripts/create_test_user.py "$email_arg" "$name_arg" --password "$password_arg"
  exit $?
fi

# ── Prod path ────────────────────────────────────────────────────────
if [[ ! -f "$PEM_KEY" ]]; then
  printf "${R}PEM key not found at %s${N}\n" "$PEM_KEY" >&2
  printf "Set PEM_KEY=/path/to/fynda-deploy.pem or place it in the repo root.\n" >&2
  exit 1
fi

SSH_OPTS=(-i "$PEM_KEY" -o StrictHostKeyChecking=accept-new -o LogLevel=ERROR)

# Escape single quotes inside the args so they survive the nested
# shell on the EC2 host. We bash-escape each value and inline.
esc() { printf "%q" "$1"; }

remote_cmd="cd $REMOTE_DIR && \
docker compose -f $COMPOSE_FILE exec -T web \
python scripts/create_test_user.py $(esc "$email_arg") $(esc "$name_arg") --password $(esc "$password_arg")"

ssh "${SSH_OPTS[@]}" "$EC2_USER@$EC2_HOST" "$remote_cmd"
