# ════════════════════════════════════════════════════════════════════
#  IAM — the instance profile the EC2 box assumes.
#
#  This replaces the static AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY
#  pair in .env.prod (config/settings/prod.py:38-39). Leave both env
#  vars EMPTY after this lands: boto3 falls through to the instance
#  role automatically, and a role cannot be copied out of a file the
#  way a long-lived key can.
#
#  Every policy below is scoped to specific resources. None uses "*"
#  on a resource that holds data.
# ════════════════════════════════════════════════════════════════════

resource "aws_iam_role" "app" {
  name = "${local.name}-app"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })

  tags = { Name = "${local.name}-app" }
}

resource "aws_iam_instance_profile" "app" {
  name = "${local.name}-app"
  role = aws_iam_role.app.name
}

# ── Backups: write-and-read, never delete ───────────────────────────
#
# Deliberately no s3:DeleteObject. Retention is handled by the bucket
# lifecycle rule, so a compromised or buggy instance cannot erase the
# backup history. Ransomware that can encrypt your database should not
# also be able to delete the copies of it.
resource "aws_iam_role_policy" "backups" {
  name = "${local.name}-backups"
  role = aws_iam_role.app.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:PutObject", "s3:GetObject", "s3:ListBucket"]
        Resource = [
          aws_s3_bucket.backups.arn,
          "${aws_s3_bucket.backups.arn}/*",
        ]
      },
    ]
  })
}

# ── Assets: full object access, needed by collectstatic ─────────────

resource "aws_iam_role_policy" "assets" {
  name = "${local.name}-assets"
  role = aws_iam_role.app.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject", "s3:GetObject", "s3:DeleteObject",
          "s3:ListBucket", "s3:PutObjectAcl",
        ]
        Resource = [
          aws_s3_bucket.assets.arn,
          "${aws_s3_bucket.assets.arn}/*",
        ]
      },
    ]
  })
}

# ── Secrets Manager: read only the secrets this project owns ────────
#
# Includes the RDS-managed master password secret, which AWS creates
# automatically because rds.tf sets manage_master_user_password.
resource "aws_iam_role_policy" "secrets" {
  name = "${local.name}-secrets"
  role = aws_iam_role.app.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"]
        Resource = [
          "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${local.name}/*",
          aws_db_instance.main.master_user_secret[0].secret_arn,
        ]
      },
    ]
  })
}

# ── CloudWatch Logs ─────────────────────────────────────────────────
#
# Phase 3 drops the RotatingFileHandler config in
# config/settings/prod.py:46-68, which currently writes audit.log and
# security.log to an unmounted /app/logs with a combined 22.5GB
# rotation ceiling. Logs go to stdout and the CloudWatch agent ships
# them here instead.
resource "aws_iam_role_policy" "logs" {
  name = "${local.name}-logs"
  role = aws_iam_role.app.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup", "logs:CreateLogStream",
          "logs:PutLogEvents", "logs:DescribeLogStreams",
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/${var.project}/*"
      },
      {
        # The CloudWatch agent reads its own config from Parameter
        # Store and publishes metrics, which are not resource-scoped.
        Effect   = "Allow"
        Action   = ["cloudwatch:PutMetricData", "ec2:DescribeTags"]
        Resource = "*"
      },
    ]
  })
}

# ── SSM Session Manager ─────────────────────────────────────────────
#
# This is what retires the .pem. Session Manager gives an audited shell
# with no inbound port open, no key pair on the instance, and no
# private key sitting in a OneDrive-synced folder. Phase 6 switches the
# GitHub Actions deploy from SSH to `ssm send-command` over OIDC.
resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.app.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# ── ECR pull (Phase 6) ──────────────────────────────────────────────
#
# Today images are built ON the EC2 box (scripts/deploy.sh:431) and the
# deploy artifact is `git reset --hard`, so there is no immutable
# artifact and no real rollback. Phase 6 builds in CI and pulls here.
resource "aws_iam_role_policy_attachment" "ecr_read" {
  role       = aws_iam_role.app.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}
