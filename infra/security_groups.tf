# ════════════════════════════════════════════════════════════════════
#  Security groups — stateful firewalls attached to resources.
#
#  The key idea: groups reference EACH OTHER, not IP addresses. "Allow
#  Postgres from whatever is in sg-app" keeps holding when the EC2 is
#  replaced, rebuilt, or scaled to several instances. An IP allowlist
#  would need editing every time.
#
#  Net effect: Postgres and Redis are unreachable from the internet by
#  construction, not by a setting somebody has to remember.
#
#  Rules are separate resources rather than inline blocks. Inline
#  ingress/egress on aws_security_group fights with anything that
#  touches the group out-of-band and produces permanent diffs.
# ════════════════════════════════════════════════════════════════════

# ── ALB ─────────────────────────────────────────────────────────────

resource "aws_security_group" "alb" {
  name        = "${local.name}-alb"
  description = "Public entry point. Cloudflare ingress only."
  vpc_id      = aws_vpc.main.id
  tags        = { Name = "${local.name}-alb" }
}

# Only Cloudflare may reach the ALB, so nobody can bypass Cloudflare's
# WAF and rate limiting by resolving the ALB hostname directly.
resource "aws_vpc_security_group_ingress_rule" "alb_https_cloudflare" {
  for_each = toset(var.cloudflare_ipv4_cidrs)

  security_group_id = aws_security_group.alb.id
  cidr_ipv4         = each.value
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
  description       = "HTTPS from Cloudflare"
}

resource "aws_vpc_security_group_ingress_rule" "alb_http_cloudflare" {
  for_each = toset(var.cloudflare_ipv4_cidrs)

  security_group_id = aws_security_group.alb.id
  cidr_ipv4         = each.value
  from_port         = 80
  to_port           = 80
  ip_protocol       = "tcp"
  description       = "HTTP from Cloudflare, redirected to HTTPS at the listener"
}

resource "aws_vpc_security_group_egress_rule" "alb_to_app" {
  security_group_id            = aws_security_group.alb.id
  referenced_security_group_id = aws_security_group.app.id
  from_port                    = 80
  to_port                      = 80
  ip_protocol                  = "tcp"
  description                  = "Forward to nginx on the app instance"
}

# ── Application instance ────────────────────────────────────────────

resource "aws_security_group" "app" {
  name        = "${local.name}-app"
  description = "EC2 running the Docker Compose stack."
  vpc_id      = aws_vpc.main.id
  tags        = { Name = "${local.name}-app" }
}

resource "aws_vpc_security_group_ingress_rule" "app_from_alb" {
  security_group_id            = aws_security_group.app.id
  referenced_security_group_id = aws_security_group.alb.id
  from_port                    = 80
  to_port                      = 80
  ip_protocol                  = "tcp"
  description                  = "nginx, ALB only"
}

# Empty by default. SSM Session Manager (granted in iam.tf) gives shell
# access with no inbound port, no key pair, and full CloudTrail audit —
# strictly better than SSH, and it retires the .pem entirely.
resource "aws_vpc_security_group_ingress_rule" "app_ssh" {
  for_each = toset(var.admin_cidr_blocks)

  security_group_id = aws_security_group.app.id
  cidr_ipv4         = each.value
  from_port         = 22
  to_port           = 22
  ip_protocol       = "tcp"
  description       = "SSH break-glass"
}

# PHASE 4 ONLY. Native logical replication is PULL-based: the
# subscriber (RDS) opens the connection to the publisher (the Postgres
# container on this instance). Without this pair of rules the
# CREATE SUBSCRIPTION in Phase 4 hangs with no useful error.
#
# Delete this rule and its egress counterpart once the cutover is
# verified and the old container is retired.
resource "aws_vpc_security_group_ingress_rule" "app_postgres_from_rds" {
  security_group_id            = aws_security_group.app.id
  referenced_security_group_id = aws_security_group.rds.id
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
  description                  = "PHASE 4: RDS subscribes to the container Postgres"
}

# Outbound is open because the app calls OpenAI, Anthropic, Gemini,
# Perplexity, xAI, DeepSeek, Polar, Slack, Discord, Google Search
# Console, SerpAPI and more. Worth knowing: apps/websites/tasks.py
# delivers tenant-configured webhooks to arbitrary URLs, so egress
# here is genuinely unbounded by design.
resource "aws_vpc_security_group_egress_rule" "app_all" {
  security_group_id = aws_security_group.app.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
  description       = "Outbound to third-party APIs"
}

# ── RDS ─────────────────────────────────────────────────────────────

resource "aws_security_group" "rds" {
  name        = "${local.name}-rds"
  description = "Postgres. Reachable only from the app instance."
  vpc_id      = aws_vpc.main.id
  tags        = { Name = "${local.name}-rds" }
}

resource "aws_vpc_security_group_ingress_rule" "rds_from_app" {
  security_group_id            = aws_security_group.rds.id
  referenced_security_group_id = aws_security_group.app.id
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
  description                  = "Postgres from the app instance only"
}

# PHASE 4 ONLY. Counterpart to app_postgres_from_rds above.
resource "aws_vpc_security_group_egress_rule" "rds_to_app_postgres" {
  security_group_id            = aws_security_group.rds.id
  referenced_security_group_id = aws_security_group.app.id
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
  description                  = "PHASE 4: subscriber connects out to the publisher"
}

# ── ElastiCache ─────────────────────────────────────────────────────

resource "aws_security_group" "redis" {
  name        = "${local.name}-redis"
  description = "Redis. Reachable only from the app instance."
  vpc_id      = aws_vpc.main.id
  tags        = { Name = "${local.name}-redis" }
}

resource "aws_vpc_security_group_ingress_rule" "redis_from_app" {
  security_group_id            = aws_security_group.redis.id
  referenced_security_group_id = aws_security_group.app.id
  from_port                    = 6379
  to_port                      = 6379
  ip_protocol                  = "tcp"
  description                  = "Redis from the app instance only"
}
