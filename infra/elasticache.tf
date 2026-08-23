# ════════════════════════════════════════════════════════════════════
#  ElastiCache for Redis.
#
#  Redis carries THREE distinct workloads in this app, and that drives
#  every choice below:
#    - Django cache            db 0  (config/settings/base.py:230)
#    - Channels layer          db 0  (base.py:240-247)
#    - Celery broker           db 1  (base.py:250)
#
#  NON-CLUSTER MODE IS REQUIRED. Redis cluster mode supports only
#  database 0. Running this app against a cluster-mode endpoint would
#  silently collapse the broker onto the cache database, so Celery
#  messages and cache keys would share a keyspace and an eviction
#  policy. A single node keeps databases 0-15 available.
#
#  Eviction is a live hazard worth understanding: the current container
#  runs `--maxmemory-policy allkeys-lru`, which is correct for a cache
#  and wrong for a broker — under memory pressure Redis will happily
#  evict queued Celery tasks. See the policy note below.
# ════════════════════════════════════════════════════════════════════

resource "aws_elasticache_subnet_group" "main" {
  name       = "${local.name}-redis"
  subnet_ids = aws_subnet.private[*].id
  tags       = { Name = "${local.name}-redis" }
}

resource "aws_elasticache_parameter_group" "main" {
  name   = "${local.name}-redis7"
  family = "redis7"

  # noeviction, not allkeys-lru. If memory fills, writes fail loudly
  # instead of Redis quietly discarding queued Celery tasks. A cache
  # miss is recoverable; a dropped task is a customer-visible bug that
  # leaves no trace.
  #
  # If this starts rejecting writes, that is the signal to move the
  # broker onto its own node or size up — not to switch back to LRU.
  parameter {
    name  = "maxmemory-policy"
    value = "noeviction"
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_elasticache_cluster" "main" {
  cluster_id = "${local.name}-redis"

  engine         = "redis"
  engine_version = "7.1"
  node_type      = var.redis_node_type

  # Exactly one node: this is what keeps it in non-cluster mode.
  num_cache_nodes = 1

  parameter_group_name = aws_elasticache_parameter_group.main.name
  subnet_group_name    = aws_elasticache_subnet_group.main.name
  security_group_ids   = [aws_security_group.redis.id]
  port                 = 6379

  # Snapshots are cheap insurance for the Celery broker. The cache
  # itself is disposable, but in-flight task messages are not.
  snapshot_retention_limit = 3
  snapshot_window          = "06:00-07:00"
  maintenance_window       = "sun:09:30-sun:10:30"

  apply_immediately = false

  tags = { Name = "${local.name}-redis" }
}

# ── On in-transit encryption ────────────────────────────────────────
#
# Not enabled, deliberately. aws_elasticache_cluster does not support
# it; that needs aws_elasticache_replication_group, which costs more
# and would require the app to switch to rediss:// URLs plus TLS
# settings in django-redis and Celery. The node sits in a private
# subnet with no internet route, admitting only sg-app on 6379.
#
# Revisit if you ever put anything in Redis that would be damaging in
# plaintext on the VPC wire. Today it holds cache entries, rate-limit
# counters, and task payloads.
