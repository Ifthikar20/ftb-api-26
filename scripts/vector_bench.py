"""Head-to-head benchmark: where should FetchBot's RAG vectors live?

Four contenders, identical data and queries:

  status_quo  JSONB column in Postgres, cosine in a pure-Python loop.
              This is apps/rag/services/retriever.py today, reproduced
              faithfully (same cosine implementation, same fetch-all
              candidate selection).
  pgvector    vector(1536) column, ORDER BY embedding <=> query LIMIT k.
              Exact scan, no ANN index - the recommended target state.
  chroma      ChromaDB PersistentClient, one collection per tenant.
              The "local vector DB" approach, embedded, no server.
  numpy       Per-tenant matrix in RAM. Not deployable as-is; included
              as the physical ceiling so the others have a yardstick.

Corpus: 20 tenants x 1,000 chunks plus one 10,000-chunk tenant, all
1536-dim, seeded RNG so runs are reproducible. Vectors are random, which
is fine for LATENCY comparison (cosine cost does not depend on the
values) but says nothing about recall - all four compute exact cosine
here anyway.

Usage:
  ./venv/Scripts/python.exe scripts/vector_bench.py

Requires the throwaway pgvector container (never the dev database):
  docker run -d --name fetchbot-pgvector-bench -p 5433:5432 \
    -e POSTGRES_PASSWORD=bench -e POSTGRES_DB=bench pgvector/pgvector:pg16
"""
import json
import math
import os
import shutil
import statistics
import time

import numpy as np

PG = dict(host="localhost", port=5433, dbname="bench",
          user="postgres", password="bench")
DIM = 1536
TENANTS = 20
CHUNKS_PER_TENANT = 1_000
BIG_TENANT_CHUNKS = 10_000
TOP_K = 5
QUERIES_SMALL = 100   # spread over the 1k tenants
QUERIES_BIG = 10      # against the 10k tenant
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "..", ".chroma-bench")


# ── The app's actual cosine, verbatim from apps/rag/services/embedder.py ──
def cosine_similarity(a, b):
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b, strict=False):
        dot += x * y
        na += x * x
        nb += y * y
    if na == 0 or nb == 0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


def make_corpus():
    rng = np.random.default_rng(42)
    corpus = {}
    for t in range(TENANTS):
        n = BIG_TENANT_CHUNKS if t == 0 else CHUNKS_PER_TENANT
        corpus[f"tenant_{t}"] = rng.standard_normal((n, DIM)).astype(np.float32)
    return corpus


def make_queries(corpus):
    rng = np.random.default_rng(7)
    qs = []
    small = [t for t in corpus if corpus[t].shape[0] == CHUNKS_PER_TENANT]
    for i in range(QUERIES_SMALL):
        qs.append((small[i % len(small)], rng.standard_normal(DIM).astype(np.float32)))
    for _ in range(QUERIES_BIG):
        qs.append(("tenant_0", rng.standard_normal(DIM).astype(np.float32)))
    return qs


def pct(lat, p):
    return statistics.quantiles(lat, n=100)[p - 1] * 1000


def report(name, ingest_s, lat, extra=""):
    print(f"  {name:11}  ingest {ingest_s:7.1f}s   "
          f"query p50 {pct(lat, 50):8.2f} ms   p95 {pct(lat, 95):8.2f} ms   {extra}")


def main():
    import psycopg2
    from psycopg2.extras import execute_values

    print("Building corpus: 19 tenants x 1k chunks + 1 tenant x 10k, dim 1536")
    corpus = make_corpus()
    queries = make_queries(corpus)
    total = sum(m.shape[0] for m in corpus.values())
    print(f"Total vectors: {total:,}   queries: {len(queries)}\n")

    conn = psycopg2.connect(**PG)
    conn.autocommit = True
    cur = conn.cursor()

    # ── A. status quo: JSONB + Python loop ──────────────────────────
    cur.execute("DROP TABLE IF EXISTS jsonb_chunks")
    cur.execute("""CREATE TABLE jsonb_chunks (
        id serial PRIMARY KEY, tenant text NOT NULL, embedding jsonb NOT NULL)""")
    cur.execute("CREATE INDEX ON jsonb_chunks (tenant)")
    t0 = time.perf_counter()
    for tenant, mat in corpus.items():
        rows = [(tenant, json.dumps(v.tolist())) for v in mat]
        execute_values(cur, "INSERT INTO jsonb_chunks (tenant, embedding) VALUES %s",
                       rows, page_size=200)
    ingest_a = time.perf_counter() - t0

    lat_a = []
    for tenant, q in queries:
        qs = time.perf_counter()
        cur.execute("SELECT embedding FROM jsonb_chunks WHERE tenant = %s", (tenant,))
        cands = cur.fetchall()          # psycopg2 parses jsonb -> list per row
        qlist = q.tolist()
        scored = [(cosine_similarity(qlist, row[0]), i) for i, row in enumerate(cands)]
        scored.sort(reverse=True)
        _ = scored[:TOP_K]
        lat_a.append(time.perf_counter() - qs)
    report("status_quo", ingest_a, lat_a)

    # ── B. pgvector, exact scan ─────────────────────────────────────
    cur.execute("DROP TABLE IF EXISTS vec_chunks")
    cur.execute(f"""CREATE TABLE vec_chunks (
        id serial PRIMARY KEY, tenant text NOT NULL, embedding vector({DIM}) NOT NULL)""")
    cur.execute("CREATE INDEX ON vec_chunks (tenant)")
    t0 = time.perf_counter()
    for tenant, mat in corpus.items():
        rows = [(tenant, "[" + ",".join(f"{x:.6f}" for x in v) + "]") for v in mat]
        execute_values(cur, "INSERT INTO vec_chunks (tenant, embedding) VALUES %s",
                       rows, page_size=200)
    ingest_b = time.perf_counter() - t0

    lat_b = []
    for tenant, q in queries:
        qtxt = "[" + ",".join(f"{x:.6f}" for x in q) + "]"
        qs = time.perf_counter()
        cur.execute(
            "SELECT id, 1 - (embedding <=> %s::vector) AS score "
            "FROM vec_chunks WHERE tenant = %s "
            "ORDER BY embedding <=> %s::vector LIMIT %s",
            (qtxt, tenant, qtxt, TOP_K))
        _ = cur.fetchall()
        lat_b.append(time.perf_counter() - qs)
    cur.execute("SELECT pg_size_pretty(pg_total_relation_size('vec_chunks')), "
                "pg_size_pretty(pg_total_relation_size('jsonb_chunks'))")
    vec_sz, jsonb_sz = cur.fetchone()
    report("pgvector", ingest_b, lat_b, f"table {vec_sz} (jsonb table: {jsonb_sz})")

    # ── C. ChromaDB, collection per tenant ──────────────────────────
    import chromadb
    from chromadb.config import Settings

    shutil.rmtree(CHROMA_DIR, ignore_errors=True)
    client = chromadb.PersistentClient(
        path=CHROMA_DIR, settings=Settings(anonymized_telemetry=False))
    t0 = time.perf_counter()
    colls = {}
    for tenant, mat in corpus.items():
        coll = client.create_collection(tenant, metadata={"hnsw:space": "cosine"})
        for start in range(0, mat.shape[0], 500):
            batch = mat[start:start + 500]
            coll.add(ids=[f"{tenant}_{start + i}" for i in range(batch.shape[0])],
                     embeddings=batch.tolist())
        colls[tenant] = coll
    ingest_c = time.perf_counter() - t0

    lat_c = []
    for tenant, q in queries:
        qs = time.perf_counter()
        _ = colls[tenant].query(query_embeddings=[q.tolist()], n_results=TOP_K)
        lat_c.append(time.perf_counter() - qs)
    du = sum(os.path.getsize(os.path.join(r, f))
             for r, _, fs in os.walk(CHROMA_DIR) for f in fs) / 1e6
    report("chroma", ingest_c, lat_c, f"disk {du:.0f} MB")

    # ── D. numpy in-RAM ceiling ─────────────────────────────────────
    t0 = time.perf_counter()
    norms = {t: m / np.linalg.norm(m, axis=1, keepdims=True) for t, m in corpus.items()}
    ingest_d = time.perf_counter() - t0
    lat_d = []
    for tenant, q in queries:
        qs = time.perf_counter()
        qn = q / np.linalg.norm(q)
        scores = norms[tenant] @ qn
        _ = np.argpartition(scores, -TOP_K)[-TOP_K:]
        lat_d.append(time.perf_counter() - qs)
    report("numpy_ram", ingest_d, lat_d, "(ceiling, not deployable as-is)")

    # ── Agreement check: do pgvector and chroma return the same ids? ──
    tenant, q = queries[0]
    qtxt = "[" + ",".join(f"{x:.6f}" for x in q) + "]"
    cur.execute("SELECT id FROM vec_chunks WHERE tenant=%s "
                "ORDER BY embedding <=> %s::vector LIMIT %s", (tenant, qtxt, TOP_K))
    pg_top = [r[0] for r in cur.fetchall()]
    ch_top = colls[tenant].query(query_embeddings=[q.tolist()], n_results=TOP_K)["ids"][0]
    print(f"\n  sanity: pgvector top-{TOP_K} ids {pg_top}")
    print(f"          chroma   top-{TOP_K} ids {ch_top}")
    print("  (different id schemes; ordinal positions should correspond)")

    conn.close()


if __name__ == "__main__":
    main()
