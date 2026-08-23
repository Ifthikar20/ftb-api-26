# ════════════════════════════════════════════════════════════════════
#  Outputs — the values you paste into .env.prod at cutover.
# ════════════════════════════════════════════════════════════════════

output "vpc_id" {
  description = "VPC id."
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "Public subnets. ALB and the EC2 instance live here."
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "Private subnets. RDS and ElastiCache live here."
  value       = aws_subnet.private[*].id
}

output "private_route_table_id" {
  description = <<-EOT
    Phase 1 verification target. This table must contain ONLY the
    implicit local route. If a 0.0.0.0/0 entry ever appears here, the
    private subnets are no longer private.
  EOT
  value       = aws_route_table.private.id
}

output "app_security_group_id" {
  description = "Attach this to the EC2 instance."
  value       = aws_security_group.app.id
}

output "db_host" {
  description = "Set as DB_HOST in .env.prod. Address only, no port."
  value       = aws_db_instance.main.address
}

output "db_endpoint" {
  description = "host:port, for psql and the Phase 4 subscription connection string."
  value       = aws_db_instance.main.endpoint
}

output "db_master_secret_arn" {
  description = <<-EOT
    Secrets Manager ARN holding the RDS master password, generated and
    rotated by AWS. Read it with:
      aws secretsmanager get-secret-value --secret-id <arn> \
        --query SecretString --output text
  EOT
  value       = aws_db_instance.main.master_user_secret[0].secret_arn
}

output "redis_url" {
  description = <<-EOT
    Set as REDIS_URL in .env.prod (database 0 = Django cache and the
    Channels layer). CELERY_BROKER_URL uses the same host with /1.
  EOT
  value       = "redis://${aws_elasticache_cluster.main.cache_nodes[0].address}:${aws_elasticache_cluster.main.port}/0"
}

output "celery_broker_url" {
  description = "Set as CELERY_BROKER_URL in .env.prod. Database 1, kept separate from the cache."
  value       = "redis://${aws_elasticache_cluster.main.cache_nodes[0].address}:${aws_elasticache_cluster.main.port}/1"
}

output "backups_bucket" {
  description = "Set as BACKUP_S3_BUCKET for scripts/backup_db.sh."
  value       = aws_s3_bucket.backups.id
}

output "assets_bucket" {
  description = "Set as AWS_STORAGE_BUCKET_NAME in .env.prod once Phase 3 adds the STORAGES dict."
  value       = aws_s3_bucket.assets.id
}

output "app_instance_profile" {
  description = "Instance profile name to attach to the EC2 box."
  value       = aws_iam_instance_profile.app.name
}

# ── What to do with these ───────────────────────────────────────────
output "cutover_checklist" {
  description = "Ordered reminder of the Phase 4 env changes."
  value       = <<-EOT

    Phase 4 .env.prod changes (do NOT apply until replication has
    caught up and every sequence has been advanced):

      DB_HOST=<db_host output>
      DB_PASSWORD=<from db_master_secret_arn>
      DB_SSLMODE=require
      REDIS_URL=<redis_url output>
      CELERY_BROKER_URL=<celery_broker_url output>
      AWS_STORAGE_BUCKET_NAME=<assets_bucket output>
      AWS_ACCESS_KEY_ID=          # leave EMPTY, the instance role covers it
      AWS_SECRET_ACCESS_KEY=      # leave EMPTY

    Then remove the `db` and `redis` services from
    docker/docker-compose.prod.yml.

  EOT
}
