# ════════════════════════════════════════════════════════════════════
#  S3 buckets.
#
#  1. backups — where scripts/backup_db.sh writes. This is Phase 0 and
#     should exist before anything else in this configuration.
#  2. assets  — static files and media. Phase 3 fixes the Django
#     STORAGES config that currently makes S3 dead code, and Phase 5
#     fronts this bucket with CloudFront.
#
#  Bucket names are globally unique across all of AWS, so both are
#  suffixed with the account ID.
# ════════════════════════════════════════════════════════════════════

data "aws_caller_identity" "current" {}

locals {
  bucket_suffix = data.aws_caller_identity.current.account_id
}

# ── Backups ─────────────────────────────────────────────────────────

resource "aws_s3_bucket" "backups" {
  bucket = "${local.name}-backups-${local.bucket_suffix}"
  tags   = { Name = "${local.name}-backups" }
}

# Versioning is the guard against the failure mode where a broken
# backup job overwrites a good backup with a truncated one. Combined
# with backup_db.sh writing timestamped keys, it means nothing
# overwrites anything by accident.
resource "aws_s3_bucket_versioning" "backups" {
  bucket = aws_s3_bucket.backups.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "backups" {
  bucket                  = aws_s3_bucket.backups.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Retention lives here, not in backup_db.sh. A lifecycle policy is
# declarative and auditable; deletion logic inside a cron job means a
# bug in that job can destroy history.
resource "aws_s3_bucket_lifecycle_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id

  rule {
    id     = "tier-and-expire"
    status = "Enabled"

    filter {
      prefix = "postgres/"
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER_IR"
    }

    expiration {
      days = 365
    }

    # Old versions exist only to survive an accidental overwrite. They
    # do not need a year.
    noncurrent_version_expiration {
      noncurrent_days = 30
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# ── Static and media assets ─────────────────────────────────────────

resource "aws_s3_bucket" "assets" {
  bucket = "${local.name}-assets-${local.bucket_suffix}"
  tags   = { Name = "${local.name}-assets" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "assets" {
  bucket = aws_s3_bucket.assets.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Private even for static files. Phase 5 puts CloudFront in front with
# an Origin Access Control, so the bucket itself never needs to be
# public — which is also what AWS_DEFAULT_ACL="private" in
# config/settings/prod.py:43 already assumes.
resource "aws_s3_bucket_public_access_block" "assets" {
  bucket                  = aws_s3_bucket.assets.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_cors_configuration" "assets" {
  bucket = aws_s3_bucket.assets.id

  cors_rule {
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = ["https://${var.domain_name}", "https://www.${var.domain_name}"]
    allowed_headers = ["*"]
    max_age_seconds = 3600
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "assets" {
  bucket = aws_s3_bucket.assets.id

  rule {
    id     = "abort-multipart"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}
