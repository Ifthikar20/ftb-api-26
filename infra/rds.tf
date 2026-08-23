# ════════════════════════════════════════════════════════════════════
#  RDS PostgreSQL — the point of the whole migration.
#
#  Today Postgres runs in a container writing to the `postgres_data`
#  Docker volume on one EC2 instance, with no backup of any kind. This
#  replaces that with automated daily snapshots, point-in-time
#  recovery, encryption at rest, and a one-command restore.
#
#  It sits in the private subnets, so it has no route to or from the
#  internet, and sg-rds admits traffic only from sg-app.
# ════════════════════════════════════════════════════════════════════

resource "aws_db_subnet_group" "main" {
  name       = "${local.name}-db"
  subnet_ids = aws_subnet.private[*].id
  tags       = { Name = "${local.name}-db" }
}

resource "aws_db_parameter_group" "main" {
  name   = "${local.name}-pg16"
  family = "postgres16"

  # Reject any non-TLS connection. Pairs with DB_SSLMODE=require in
  # config/settings/prod.py, which currently defaults to the much
  # weaker 'prefer'.
  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }

  # Log slow queries. The pixel ingestion path issues roughly eight
  # sequential statements per tracked pageview, so this is how you will
  # actually see that cost once real traffic arrives.
  parameter {
    name  = "log_min_duration_statement"
    value = "1000"
  }

  parameter {
    name  = "log_connections"
    value = "1"
  }

  # NOTE for Phase 4: rds.logical_replication is deliberately NOT set.
  # It is required only when RDS is the PUBLISHER, and in the cutover
  # RDS is the SUBSCRIBER — it connects out to the container Postgres.
  # Turning it on raises WAL volume for no benefit here. Add it later
  # if you ever replicate out of RDS.

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_db_instance" "main" {
  identifier = "${local.name}-postgres"

  engine         = "postgres"
  engine_version = var.db_engine_version
  instance_class = var.db_instance_class

  # gp3 gives a baseline 3000 IOPS at any size, so a 20GB volume is not
  # throttled the way an equivalent gp2 volume would be.
  storage_type          = "gp3"
  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = var.db_max_allocated_storage
  storage_encrypted     = true

  db_name  = var.db_name
  username = var.db_username

  # AWS generates the password and stores it in Secrets Manager itself.
  # The alternative puts the password in Terraform state in plaintext,
  # which then needs the same protection as the database.
  manage_master_user_password = true

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  parameter_group_name   = aws_db_parameter_group.main.name
  publicly_accessible    = false
  port                   = 5432

  multi_az = var.db_multi_az

  # This is the line that closes the gap DEPLOY.md has been pretending
  # was already closed. Retention doubles as the PITR window.
  backup_retention_period = var.db_backup_retention_days
  backup_window           = "07:00-08:00" # UTC, before the 09:00 report tasks
  maintenance_window       = "sun:08:30-sun:09:30"
  copy_tags_to_snapshot   = true

  # Minor version upgrades have broken extensions before. Take them
  # deliberately, in a window you chose.
  auto_minor_version_upgrade = false
  apply_immediately          = false

  deletion_protection       = true
  skip_final_snapshot       = false
  final_snapshot_identifier = "${local.name}-postgres-final"

  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  performance_insights_enabled          = true
  performance_insights_retention_period = 7 # free tier

  tags = { Name = "${local.name}-postgres" }

  lifecycle {
    # Storage autoscaling changes this value out-of-band; without the
    # ignore, every later plan wants to shrink the volume back.
    ignore_changes = [allocated_storage]
  }
}

# ── After `terraform apply`, before the Phase 4 cutover ─────────────
#
# pgvector is not a Terraform resource. Connect from the EC2 instance
# and enable it once:
#
#   CREATE EXTENSION IF NOT EXISTS vector;
#
# This is what lets apps/rag stop shipping every 1536-float embedding
# over the wire as JSON and let Postgres compute the distance instead.
