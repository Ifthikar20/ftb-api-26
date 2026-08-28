"""End-to-end RAG evaluation: python path vs chroma path on REAL data.

Unlike scripts/vector_bench.py (random vectors, latency only), this runs
the actual product code on actual text:

  ingest_url(text=...)  ->  chunker  ->  OpenAI embeddings  ->  Postgres
                                     \\-> chroma mirror (on_commit hook)
  retrieve(query)       ->  backend path vs python path, side by side

measuring three things:
  1. QUALITY   - gold queries with known correct documents: does each
                 path return what a human would expect? Recall@1/@5, MRR.
  2. AGREEMENT - do the two paths return the same chunks in the same
                 order with the same scores?
  3. LATENCY   - full retrieve() wall time, and retrieval-only time with
                 the query-embedding call factored out, so the OpenAI
                 network cost is not misattributed to either store.

Uses the cansee_test scratch database (never dev data) and a
scratch chroma dir. Costs a fraction of a cent in OpenAI embeddings.

Run:  ./venv/Scripts/python.exe scripts/rag_eval.py
"""
import os
import statistics
import sys
import time
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

SCRATCH_CHROMA = str(REPO / ".chroma-eval")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")
os.environ["RAG_VECTOR_BACKEND"] = "chroma"
os.environ["RAG_CHROMA_PATH"] = SCRATCH_CHROMA

import django  # noqa: E402

django.setup()

import shutil  # noqa: E402
from unittest.mock import patch  # noqa: E402

from django.core.management import call_command  # noqa: E402
from django.db import connection  # noqa: E402
from django.test.utils import override_settings  # noqa: E402

# ── Corpus: Cansee-flavoured documents with topic labels ──────────
# Each entry: (topic, title, text). Topics are the gold labels - a
# query is "answered correctly" when the top hit's document carries the
# expected topic.
GOLD_DOCS = [
    ("returns", "Returns policy",
     "Customers can return any order within 30 days of delivery for a full "
     "refund. Refunds are issued to the original payment method within five "
     "business days of the returned item arriving at our warehouse."),
    ("returns", "Exchange process",
     "To exchange an item for a different size, start a return in the "
     "account portal and place a new order. Exchanges ship free and the "
     "refund for the original item follows the standard returns window."),
    ("pricing", "Pro plan pricing",
     "The Pro plan costs 49 dollars per month billed monthly, or 490 "
     "dollars per year on the annual plan, which works out to two months "
     "free. Every paid plan includes unlimited team seats."),
    ("pricing", "Free plan limits",
     "The Free plan includes one project, five-prompt audits, two audits "
     "per month and a small monthly AI allowance. When a limit is reached, "
     "audits pause until the monthly reset. Nobody is ever locked out."),
    ("shipping", "Shipping times",
     "Standard shipping takes three to five business days within the "
     "continental United States. Express shipping arrives in one to two "
     "business days. International delivery typically takes seven to "
     "fourteen days depending on customs."),
    ("security", "Data encryption",
     "All customer data is encrypted at rest using AES-256 and in transit "
     "with TLS 1.3. Field-level encryption additionally protects OAuth "
     "tokens and API credentials stored in the database."),
    ("security", "Account protection",
     "Accounts are protected by login throttling and automatic lockout "
     "after repeated failed attempts. We support time-based one-time "
     "passwords for two-factor authentication on every plan."),
    ("visibility", "AI visibility tracking",
     "Cansee asks the major AI assistants the questions your buyers ask "
     "and records whether your brand is mentioned, how it is described, "
     "and which competitors appear alongside it in each answer."),
    ("visibility", "Share of voice metric",
     "Share of voice measures how often your brand appears in AI answers "
     "for your tracked prompts compared with competitors. A rising share "
     "of voice means models mention you more often for buyer questions."),
    ("integrations", "Slack integration",
     "Connect a Slack workspace to receive hot lead alerts, weekly growth "
     "digests and audit completions in any channel. The bot supports "
     "slash commands for asking about traffic without leaving Slack."),
    ("integrations", "Search Console sync",
     "Linking Google Search Console imports daily impressions, clicks and "
     "position for every query. The nightly sync keeps twelve months of "
     "history and powers the search insights dashboard."),
    ("analytics", "Visitor tracking pixel",
     "The tracking pixel is a small script that records pageviews, "
     "sessions and referrers on your website. It respects privacy by "
     "hashing IP addresses and never storing raw personal identifiers."),
    ("analytics", "Bounce rate definition",
     "A bounce is a session that views a single page and leaves. The "
     "dashboard computes bounce rate as bounced sessions divided by total "
     "sessions across the selected period."),
    ("support", "Contacting support",
     "Reach the support team through the in-app chat bubble or by email "
     "at any time. Paid plans receive responses within one business day; "
     "critical incidents are handled around the clock."),
]

# Filler documents on unrelated topics create realistic index pressure
# so the gold queries have something to be wrong about.
FILLER_TOPICS = [
    "The quarterly engineering offsite covered service reliability and the "
    "migration of build pipelines to faster runners with cached layers.",
    "Our office recycling program now includes compost bins on every "
    "floor and quarterly e-waste collection events for old hardware.",
    "The design team standardised on an eight point spacing system and a "
    "shared token palette across marketing and product surfaces.",
    "Sales onboarding was refreshed with call recordings, objection "
    "handling playbooks and a shadowing rotation in the first month.",
    "The company book club is reading a history of container shipping "
    "and meets on alternating Thursdays over lunch.",
]

GOLD_QUERIES = [
    ("How long do I have to send something back for a refund?", "returns"),
    ("What does the paid subscription cost per month?", "pricing"),
    ("What are the limits on the free tier?", "pricing"),
    ("When will my package arrive with standard delivery?", "shipping"),
    ("How is my stored data protected?", "security"),
    ("Do you support two factor authentication?", "security"),
    ("How do you measure whether AI models mention my brand?", "visibility"),
    ("What does share of voice mean?", "visibility"),
    ("Can I get lead alerts in Slack?", "integrations"),
    ("How does the Google Search Console connection work?", "integrations"),
    ("What exactly does the pixel record about visitors?", "analytics"),
    ("How is bounce rate calculated?", "analytics"),
    ("How do I get help from a human?", "support"),
    ("Can I swap an item for another size?", "returns"),
]


def ensure_schema():
    with connection.cursor() as cur:
        cur.execute("SELECT to_regclass('rag_knowledge_chunk')")
        if cur.fetchone()[0] is None:
            print("Scratch DB has no schema; running migrate --run-syncdb once...")
            call_command("migrate", "--run-syncdb", verbosity=0)


def reset_state():
    from apps.accounts.models import User

    shutil.rmtree(SCRATCH_CHROMA, ignore_errors=True)
    User.objects.filter(email__startswith="rag-eval-").delete()  # cascades


def build_fixtures():
    from apps.accounts.models import User
    from apps.websites.models import Website

    user = User.objects.create_user(
        email=f"rag-eval-{uuid.uuid4().hex[:8]}@example.com",
        password="EvalPass123!", full_name="Rag Eval",
    )
    site = Website.objects.create(
        user=user, name="EvalCo", url="https://evalco.example.com",
        industry="SaaS", pixel_key=uuid.uuid4(), is_active=True,
    )
    decoy = Website.objects.create(
        user=user, name="DecoyCo", url="https://decoyco.example.com",
        industry="SaaS", pixel_key=uuid.uuid4(), is_active=True,
    )
    return user, site, decoy


def ingest_corpus(user, site, decoy):
    from apps.rag.models import KnowledgeChunk
    from apps.rag.services.ingest_service import ingest_url

    docs = [(t, title, text) for t, title, text in GOLD_DOCS]
    docs += [("filler", f"Note {i}", txt)
             for i, txt in enumerate(FILLER_TOPICS * 8)]  # 40 filler docs

    url_topic = {}
    t0 = time.perf_counter()
    for i, (topic, title, text) in enumerate(docs):
        url = f"paste://eval/{i}"
        res = ingest_url(user=user, website=site, url=url,
                         kind="docs", title=title, text=text)
        assert res.chunk_count > 0, f"ingest produced no chunks for {title}"
        url_topic[url] = topic
    for i in range(10):
        ingest_url(user=user, website=decoy, url=f"paste://decoy/{i}",
                   kind="docs", title=f"Decoy {i}",
                   text="Entirely unrelated decoy content about sailing "
                        f"regattas and harbour tides, variant {i}.")
    ingest_s = time.perf_counter() - t0

    sample = KnowledgeChunk.objects.filter(website=site).first()
    model = sample.embedding_model
    n = KnowledgeChunk.objects.filter(website=site).count()
    print(f"Ingested {len(docs)} docs -> {n} chunks in {ingest_s:.1f}s "
          f"(embedding model: {model})")
    if model != "text-embedding-3-small":
        print("\n*** WARNING: real OpenAI embeddings were NOT used (fell back "
              f"to {model}). Quality numbers below are meaningless for "
              "paraphrase queries - investigate before trusting them. ***\n")
    return url_topic


def run_path(name, user, site, url_topic, cached_vecs):
    """Run all gold queries through retrieve() on the current backend
    setting. Returns metrics dict."""
    from apps.rag.services.retriever import retrieve

    hits_at_1 = hits_at_5 = 0
    rr = []
    full_lat, iso_lat = [], []
    per_query = []

    for q, want in GOLD_QUERIES:
        t0 = time.perf_counter()
        retrieve(user=user, website=site, query=q, top_k=5)  # timed, discarded
        full_lat.append(time.perf_counter() - t0)

        # Retrieval-only timing: bypass the OpenAI query-embedding call
        # with the cached vector so the store is measured, not the network.
        with patch("apps.rag.services.retriever.embed_one",
                   return_value=(cached_vecs[q], "cached", len(cached_vecs[q]))):
            t0 = time.perf_counter()
            hits_iso = retrieve(user=user, website=site, query=q, top_k=5)
            iso_lat.append(time.perf_counter() - t0)

        got = [url_topic.get(h.source_url, "?") for h in hits_iso]
        ok1 = bool(got) and got[0] == want
        ok5 = want in got
        hits_at_1 += ok1
        hits_at_5 += ok5
        rr.append(1.0 / (got.index(want) + 1) if ok5 else 0.0)
        per_query.append((q, want, got[:3], ok1,
                          [h.chunk_id for h in hits_iso],
                          [round(h.score, 4) for h in hits_iso]))

    n = len(GOLD_QUERIES)
    return {
        "name": name,
        "recall1": hits_at_1 / n, "recall5": hits_at_5 / n,
        "mrr": sum(rr) / n,
        "full_p50": statistics.median(full_lat) * 1000,
        "iso_p50": statistics.median(iso_lat) * 1000,
        "iso_max": max(iso_lat) * 1000,
        "per_query": per_query,
    }


def main():
    ensure_schema()
    reset_state()
    user, site, decoy = build_fixtures()
    url_topic = ingest_corpus(user, site, decoy)

    # Pre-embed every query once (real OpenAI) for the isolated timing.
    from apps.rag.services import vector_backends
    from apps.rag.services.embedder import embed_one

    cached = {}
    for q, _ in GOLD_QUERIES:
        vec, _m, _d = embed_one(q, user=user, website=site)
        cached[q] = vec

    print("\nRunning gold queries through BOTH paths...\n")
    chroma = run_path("chroma", user, site, url_topic, cached)

    vector_backends.reset_backend_for_tests()
    with override_settings(RAG_VECTOR_BACKEND="python"):
        python = run_path("python", user, site, url_topic, cached)
    vector_backends.reset_backend_for_tests()

    # Agreement between the two paths on ids and scores.
    id_agree = score_close = 0
    for (qc, pc) in zip(chroma["per_query"], python["per_query"], strict=True):
        if qc[4] == pc[4]:
            id_agree += 1
        if len(qc[5]) == len(pc[5]) and all(
                abs(a - b) < 5e-4 for a, b in zip(qc[5], pc[5], strict=True)):
            score_close += 1

    n = len(GOLD_QUERIES)
    print("=" * 74)
    print(f"{'':24}{'CHROMA (index)':>22}{'PYTHON (postgres)':>26}")
    print("-" * 74)
    for label, key, fmt in [
        ("Recall@1", "recall1", "{:.0%}"), ("Recall@5", "recall5", "{:.0%}"),
        ("MRR", "mrr", "{:.3f}"),
        ("retrieve() p50 (full)", "full_p50", "{:.1f} ms"),
        ("retrieval-only p50", "iso_p50", "{:.2f} ms"),
        ("retrieval-only worst", "iso_max", "{:.2f} ms"),
    ]:
        print(f"{label:24}{fmt.format(chroma[key]):>22}"
              f"{fmt.format(python[key]):>26}")
    print("-" * 74)
    print(f"{'top-5 ids identical':24}{id_agree}/{n} queries")
    print(f"{'scores within 5e-4':24}{score_close}/{n} queries")
    print("=" * 74)

    misses = [p for p in chroma["per_query"] if not p[3]]
    if misses:
        print("\nQueries where chroma's TOP hit was not the expected topic:")
        for q, want, got, _, _, _ in misses:
            print(f"  want={want:12} got={got}  <- {q}")
    print("\nScratch DB rows and .chroma-eval left in place for inspection; "
          "rerun resets both.")


if __name__ == "__main__":
    main()
