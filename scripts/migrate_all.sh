#!/usr/bin/env bash
#
# One-shot migration runner.
#
# Applies every migration this branch added — Stripe / plan reshape,
# RAG knowledge base, region-aware LLM audits — in the correct order
# and prints what it did. Idempotent: re-running is a no-op when
# everything is already at head.
#
# Usage:
#   ./scripts/migrate_all.sh
#   ./scripts/migrate_all.sh --check   # dry-run; show what would apply

set -euo pipefail

cd "$(dirname "$0")/.."

# ── Style helpers ─────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'
say()  { echo -e "${GREEN}▸${NC} $*"; }
warn() { echo -e "${YELLOW}!${NC} $*"; }
fail() { echo -e "${RED}✗${NC} $*"; exit 1; }

DRY_RUN=0
if [[ "${1:-}" == "--check" || "${1:-}" == "-n" ]]; then
    DRY_RUN=1
fi

# ── Sanity checks ─────────────────────────────────────────────────
[[ -f manage.py ]] || fail "Run from the project root (manage.py not found)."
command -v python >/dev/null || fail "python not on PATH."

# Pick up settings the same way run_dev.sh does.
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings.dev}"

say "Using DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE}"

# ── 1. Show pending migrations ────────────────────────────────────
say "Checking for pending migrations…"
python manage.py showmigrations --plan | grep -E '^\[ \]' || true

# ── 2. Apply all migrations ───────────────────────────────────────
# Order matters only when an app declares an explicit dependency on
# another app's migration. Django's runner already topologically
# sorts the plan, so a single ``migrate`` covers every app added on
# this branch:
#
#   accounts    0008_alter_plan_three_tier
#   billing     0005_alter_subscription_plan_three_tier
#   llm_ranking 0012_brand_strengths_and_smoothed_rate
#   llm_ranking 0013_region_and_citation_countries
#   rag         0001_initial
#
# We still call out the apps individually so the output is easy to
# scan — and so a failure halfway through tells you which app broke.

APPS=(accounts billing llm_ranking rag)

if [[ $DRY_RUN -eq 1 ]]; then
    say "Dry-run mode — would migrate: ${APPS[*]}"
    for app in "${APPS[@]}"; do
        echo
        warn "  $app pending plan:"
        python manage.py showmigrations "$app" 2>/dev/null | sed 's/^/    /'
    done
    exit 0
fi

for app in "${APPS[@]}"; do
    say "migrate $app"
    python manage.py migrate "$app"
done

# Catch anything else (auth / admin / sessions etc.) that isn't on
# the list above. Safe to run unconditionally — already-applied
# migrations are a no-op.
say "migrate (all remaining apps)"
python manage.py migrate

# ── 3. Verify nothing is still pending ────────────────────────────
say "Verifying head…"
PENDING="$(python manage.py showmigrations --plan | grep -c '^\[ \]' || true)"
if [[ "$PENDING" -gt 0 ]]; then
    warn "$PENDING migration(s) still pending. Re-run, or inspect with"
    warn "  python manage.py showmigrations --plan | grep '^\\[ \\]'"
else
    say "All migrations applied."
fi

# ── 4. Friendly post-amble ────────────────────────────────────────
echo
say "Done. Summary of what this branch added:"
cat <<'NOTE'
  • accounts.0008  — Plan choices reshape (User + Organization)
  • billing.0005   — Plan choices reshape (Subscription)
  • llm_ranking.0012 — Plackett-Luce brand_strengths + Beta-Binomial
                      mention_rate_smoothed on LLMRankingAudit
  • llm_ranking.0013 — region + citation_countries on Audit + Result
  • rag.0001       — KnowledgeSource + KnowledgeChunk (initial schema)

  No data migrations are required. Existing Subscription / User rows
  on "starter" continue to resolve via the legacy alias kept in
  PLAN_LIMITS (core.utils.constants), so nothing breaks for current
  users.
NOTE
