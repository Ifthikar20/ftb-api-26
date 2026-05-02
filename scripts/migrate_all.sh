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

# Resolve the repo root from this script's location so the launcher
# works regardless of where it's invoked from.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

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
[[ -f manage.py ]] || fail "manage.py not found in ${REPO_ROOT}."

# Activate the project venv. Try the conventional names in order so
# we work whether the developer used ``.venv`` (PEP 405 style),
# ``venv`` (most tutorials), or ``env``.
#
# If none exist, fall back to whatever python is on PATH and warn
# loudly — the most likely failure (Anaconda's base env not having
# django-environ) is exactly what triggered this fix in the first
# place.
ACTIVATED=""
for cand in .venv venv env; do
    if [[ -f "${REPO_ROOT}/${cand}/bin/activate" ]]; then
        # shellcheck disable=SC1090
        source "${REPO_ROOT}/${cand}/bin/activate"
        ACTIVATED="${cand}"
        break
    fi
done
if [[ -n "${ACTIVATED}" ]]; then
    say "venv activated: ${ACTIVATED}/ ($(python --version 2>&1))"
else
    warn "No project venv found (tried .venv/, venv/, env/)."
    warn "Falling back to system Python: $(command -v python || echo 'NONE')"
    warn "If migrations fail with ModuleNotFoundError, run:"
    warn "  python -m venv .venv && source .venv/bin/activate \\"
    warn "    && pip install -r requirements/dev.txt"
fi

command -v python >/dev/null || fail "python still not on PATH after venv lookup."

# Confirm Django + django-environ are importable up front so the
# error message is friendly rather than a 30-line traceback later.
if ! python -c "import django, environ" 2>/dev/null; then
    fail "Django or django-environ isn't installed in the active Python.
       Active python: $(command -v python)
       Try:  pip install -r requirements/dev.txt"
fi

# Pick up settings the same way run_dev.sh does.
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings.dev}"

say "Using DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE}"

# ── 1. Show pending migrations ────────────────────────────────────
say "Checking for pending migrations…"
PLAN_OUT="$(python manage.py showmigrations --plan 2>&1 || true)"
echo "${PLAN_OUT}" | grep -E '^\[ \]' || echo "  (none — head is clean)"

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
  • accounts.0009  — Drop orphan messaging_* tables (app removed)
  • accounts.0010  — Drop leads_emailcampaign + leads_campaignrecipient
  • analytics.0008 — Drop FK columns on TrackedLink + LinkClick
  • leads.0005     — Remove EmailCampaign + CampaignRecipient from
                     model state (tables dropped in accounts.0010)
  • billing.0005   — Plan choices reshape (Subscription)
  • llm_ranking.0012 — Plackett-Luce brand_strengths + Beta-Binomial
                      mention_rate_smoothed on LLMRankingAudit
  • llm_ranking.0013 — region + citation_countries on Audit + Result
  • rag.0001       — KnowledgeSource + KnowledgeChunk (initial schema)
  • rag.0002       — index TimestampMixin.created_at (omitted in 0001)

  No data migrations are required. Existing Subscription / User rows
  on "starter" continue to resolve via the legacy alias kept in
  PLAN_LIMITS (core.utils.constants), so nothing breaks for current
  users.
NOTE
