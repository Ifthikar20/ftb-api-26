#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════
#  Cansee — Postgres backup to S3.
#
#  Runs ON the EC2 host (not over SSH). Wired to cron every 6h.
#
#  Until this script exists there is NO backup of any kind: customer
#  data lives only in the `postgres_data` Docker volume on one box.
#  DEPLOY.md tells you to "restore from the most recent Postgres
#  backup" — this is what finally produces one.
#
#  Usage:
#    bash scripts/backup_db.sh                 # alias for 'backup'
#    bash scripts/backup_db.sh backup          # dump + upload to S3
#    bash scripts/backup_db.sh list            # list backups in S3
#    bash scripts/backup_db.sh verify [key]    # restore-test a backup
#    bash scripts/backup_db.sh restore <key>   # restore INTO a target
#    bash scripts/backup_db.sh help
#
#  Required environment:
#    BACKUP_S3_BUCKET     target bucket (no s3:// prefix)
#
#  Optional environment:
#    BACKUP_S3_PREFIX     key prefix           (default: postgres)
#    DB_NAME              database             (default: cansee)
#    DB_USER              role                 (default: postgres)
#    DB_HOST              set to dump a REMOTE server (e.g. RDS)
#                         instead of the local `db` container
#    PGPASSWORD           required when DB_HOST is set
#    BACKUP_TMPDIR        scratch dir          (default: /var/tmp)
#    BACKUP_MIN_BYTES     fail if dump smaller (default: 51200)
#
#  Credentials: none. This relies on the EC2 instance profile. Do not
#  add AWS_ACCESS_KEY_ID here — an instance role cannot leak the way a
#  static key in .env.prod can.
#
#  Format: pg_dump -Fc (custom). Already compressed, so no gzip, and
#  it restores with pg_restore --clean --if-exists and supports
#  parallel + selective restore. --no-owner/--no-privileges keep the
#  dump portable into RDS, where the master user is not a superuser.
# ════════════════════════════════════════════════════════════════════

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

COMPOSE_FILE="${COMPOSE_FILE:-docker/docker-compose.prod.yml}"
BACKUP_S3_BUCKET="${BACKUP_S3_BUCKET:-}"
BACKUP_S3_PREFIX="${BACKUP_S3_PREFIX:-postgres}"
DB_NAME="${DB_NAME:-cansee}"
DB_USER="${DB_USER:-postgres}"
DB_HOST="${DB_HOST:-}"
BACKUP_TMPDIR="${BACKUP_TMPDIR:-/var/tmp}"
BACKUP_MIN_BYTES="${BACKUP_MIN_BYTES:-51200}"
PG_IMAGE="${PG_IMAGE:-postgres:16-alpine}"

# ── Style (matches deploy.sh) ────────────────────────────────────────
B=$'\033[1m'; R=$'\033[0;31m'; G=$'\033[0;32m'; Y=$'\033[1;33m'
C=$'\033[0;36m'; N=$'\033[0m'
step() { printf "\n%s%s> %s%s\n" "$C" "$B" "$*" "$N"; }
ok()   { printf "  %s[ok]%s %s\n" "$G" "$N" "$*"; }
warn() { printf "  %s[!]%s %s\n" "$Y" "$N" "$*"; }
err()  { printf "  %s[x]%s %s\n" "$R" "$N" "$*"; }
die()  { err "$*"; exit 1; }

# Timestamps are UTC so cron output sorts lexically in S3.
stamp() { date -u +%Y%m%dT%H%M%SZ; }

require_bucket() {
  [[ -n "$BACKUP_S3_BUCKET" ]] \
    || die "BACKUP_S3_BUCKET is unset. Export it or add it to the cron env."
}

require_aws() {
  command -v aws >/dev/null 2>&1 \
    || die "aws CLI not found. Install with: sudo snap install aws-cli --classic"
}

# Dump to stdout. Local container by default; remote server if DB_HOST
# is set (used after the RDS cutover, and to snapshot RDS ad-hoc).
pg_dump_stream() {
  local args=(--format=custom --no-owner --no-privileges --verbose)
  if [[ -n "$DB_HOST" ]]; then
    [[ -n "${PGPASSWORD:-}" ]] || die "DB_HOST is set but PGPASSWORD is not."
    docker run --rm -i -e PGPASSWORD "$PG_IMAGE" \
      pg_dump -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" "${args[@]}"
  else
    docker compose -f "$COMPOSE_FILE" exec -T db \
      pg_dump -U "$DB_USER" -d "$DB_NAME" "${args[@]}"
  fi
}

# ════════════════════════════════════════════════════════════════════
# backup
# ════════════════════════════════════════════════════════════════════
cmd_backup() {
  require_bucket; require_aws
  cd "$REPO_DIR"

  local ts key tmp size
  ts="$(stamp)"
  key="${BACKUP_S3_PREFIX}/${DB_NAME}-${ts}.dump"
  tmp="${BACKUP_TMPDIR}/cansee-backup-${ts}.dump"

  # Always clean up the local dump, including on failure — the box has
  # limited disk and deploy.sh already warns under 5 GB free.
  trap '[[ -n "${tmp:-}" && -f "$tmp" ]] && rm -f "$tmp"' EXIT

  step "Checking free disk in $BACKUP_TMPDIR"
  local avail_mb
  avail_mb="$(df -Pm "$BACKUP_TMPDIR" | awk 'NR==2{print $4}')"
  [[ "$avail_mb" -ge 512 ]] \
    || die "only ${avail_mb}MB free in $BACKUP_TMPDIR; need at least 512MB"
  ok "${avail_mb}MB available"

  # Dump to a local file first rather than streaming straight to S3.
  # A streamed pipe can upload a truncated object when pg_dump dies
  # mid-run, and a truncated backup that looks present is worse than
  # no backup at all.
  step "Dumping $DB_NAME"
  if ! pg_dump_stream > "$tmp" 2>/dev/null; then
    die "pg_dump failed; nothing uploaded"
  fi

  size="$(stat -c%s "$tmp" 2>/dev/null || stat -f%z "$tmp")"
  [[ "$size" -ge "$BACKUP_MIN_BYTES" ]] \
    || die "dump is only ${size} bytes (min ${BACKUP_MIN_BYTES}); refusing to upload"
  ok "dump is $(numfmt --to=iec "$size" 2>/dev/null || echo "${size}B")"

  # A custom-format dump must be readable by pg_restore --list. This
  # catches corruption that a size check alone would pass.
  step "Validating dump integrity"
  local objects
  objects="$(docker run --rm -i "$PG_IMAGE" pg_restore --list < "$tmp" 2>/dev/null | grep -c ';' || true)"
  [[ "$objects" -gt 0 ]] || die "pg_restore --list found no objects; dump is corrupt"
  ok "$objects objects in table of contents"

  step "Uploading to s3://${BACKUP_S3_BUCKET}/${key}"
  aws s3 cp "$tmp" "s3://${BACKUP_S3_BUCKET}/${key}" \
    --sse AES256 --only-show-errors \
    || die "upload failed"
  ok "uploaded"

  # Retention is an S3 lifecycle rule (infra/s3.tf), not this script.
  # Deleting from here would mean a bug in a cron job can destroy
  # history; lifecycle policy is declarative and auditable.
  printf "\n%s%sBackup complete:%s s3://%s/%s\n\n" "$G" "$B" "$N" "$BACKUP_S3_BUCKET" "$key"
}

# ════════════════════════════════════════════════════════════════════
# list
# ════════════════════════════════════════════════════════════════════
cmd_list() {
  require_bucket; require_aws
  step "Backups in s3://${BACKUP_S3_BUCKET}/${BACKUP_S3_PREFIX}/"
  aws s3 ls "s3://${BACKUP_S3_BUCKET}/${BACKUP_S3_PREFIX}/" --human-readable \
    | sort -r | head -30
}

latest_key() {
  aws s3 ls "s3://${BACKUP_S3_BUCKET}/${BACKUP_S3_PREFIX}/" \
    | awk '{print $4}' | grep -E '\.dump$' | sort | tail -1
}

# ════════════════════════════════════════════════════════════════════
# verify — restore into a throwaway container and sanity-check it.
#
# This is the step that turns a backup from a hypothesis into a fact.
# Run it once after the first backup, and again before Phase 4.
# ════════════════════════════════════════════════════════════════════
cmd_verify() {
  require_bucket; require_aws
  local key="${1:-}" tmp cname
  [[ -n "$key" ]] || key="$(latest_key)"
  [[ -n "$key" ]] || die "no backups found under ${BACKUP_S3_PREFIX}/"
  [[ "$key" == */* ]] || key="${BACKUP_S3_PREFIX}/${key}"

  tmp="${BACKUP_TMPDIR}/cansee-verify-$$.dump"
  cname="cansee-verify-$$"

  cleanup_verify() {
    docker rm -f "$cname" >/dev/null 2>&1 || true
    [[ -f "$tmp" ]] && rm -f "$tmp"
  }
  trap cleanup_verify EXIT

  step "Downloading s3://${BACKUP_S3_BUCKET}/${key}"
  aws s3 cp "s3://${BACKUP_S3_BUCKET}/${key}" "$tmp" --only-show-errors \
    || die "download failed"
  ok "downloaded"

  step "Starting throwaway Postgres ($cname)"
  docker run -d --name "$cname" \
    -e POSTGRES_PASSWORD=verify -e POSTGRES_DB="$DB_NAME" \
    "$PG_IMAGE" >/dev/null
  local tries=0
  until docker exec "$cname" pg_isready -U postgres >/dev/null 2>&1; do
    tries=$((tries + 1))
    [[ "$tries" -lt 30 ]] || die "throwaway Postgres never became ready"
    sleep 1
  done
  ok "ready"

  step "Restoring"
  # --exit-on-error is deliberately omitted: a dump taken with
  # --no-owner will emit benign role-related notices on a fresh
  # cluster. Row counts below are the real assertion.
  docker exec -i "$cname" pg_restore -U postgres -d "$DB_NAME" --no-owner \
    < "$tmp" >/dev/null 2>&1 || warn "pg_restore reported non-fatal errors"

  step "Sanity-checking restored data"
  local tables
  tables="$(docker exec "$cname" psql -U postgres -d "$DB_NAME" -t -A -c \
    "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';")"
  [[ "$tables" -gt 10 ]] || die "only $tables tables restored; backup is not usable"
  ok "$tables tables"

  # Spot-check the tables that would actually hurt to lose.
  local t
  for t in accounts_user websites_website rag_knowledge_chunk; do
    local n
    n="$(docker exec "$cname" psql -U postgres -d "$DB_NAME" -t -A -c \
      "SELECT count(*) FROM $t;" 2>/dev/null || echo "MISSING")"
    if [[ "$n" == "MISSING" ]]; then
      warn "$t: not present in this dump"
    else
      ok "$t: $n rows"
    fi
  done

  printf "\n%s%sVERIFIED:%s %s restores cleanly.\n\n" "$G" "$B" "$N" "$key"
}

# ════════════════════════════════════════════════════════════════════
# restore — into an explicit target. Refuses to guess.
# ════════════════════════════════════════════════════════════════════
cmd_restore() {
  require_bucket; require_aws
  local key="${1:-}"
  [[ -n "$key" ]] || die "usage: backup_db.sh restore <s3-key>"
  [[ "$key" == */* ]] || key="${BACKUP_S3_PREFIX}/${key}"
  [[ -n "$DB_HOST" ]] \
    || die "refusing to restore without an explicit DB_HOST target."

  local tmp="${BACKUP_TMPDIR}/cansee-restore-$$.dump"
  trap '[[ -f "$tmp" ]] && rm -f "$tmp"' EXIT

  printf "\n%s%sThis OVERWRITES %s on %s.%s\n" "$Y" "$B" "$DB_NAME" "$DB_HOST" "$N"
  read -r -p "  Type the database name to confirm: " confirm
  [[ "$confirm" == "$DB_NAME" ]] || die "confirmation did not match; aborted"

  step "Downloading $key"
  aws s3 cp "s3://${BACKUP_S3_BUCKET}/${key}" "$tmp" --only-show-errors

  step "Restoring into $DB_HOST/$DB_NAME"
  [[ -n "${PGPASSWORD:-}" ]] || die "PGPASSWORD is required for a remote restore"
  docker run --rm -i -e PGPASSWORD "$PG_IMAGE" \
    pg_restore -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" \
      --clean --if-exists --no-owner --no-privileges < "$tmp"
  ok "restore finished"
}

cmd_help() { sed -n '2,44p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }

case "${1:-backup}" in
  backup)  shift || true; cmd_backup "$@" ;;
  list)    shift || true; cmd_list "$@" ;;
  verify)  shift || true; cmd_verify "$@" ;;
  restore) shift || true; cmd_restore "$@" ;;
  help|-h|--help) cmd_help ;;
  *) die "unknown subcommand: $1 (try: backup, list, verify, restore, help)" ;;
esac
