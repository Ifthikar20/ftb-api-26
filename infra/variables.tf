# ════════════════════════════════════════════════════════════════════
#  Inputs. Defaults are sized for the "under $100/mo" budget agreed in
#  the migration plan. Every default that costs money is called out.
# ════════════════════════════════════════════════════════════════════

variable "aws_region" {
  description = "Region for every resource. Keep the app and its data in one region."
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name, used in resource names and tags."
  type        = string
  default     = "prod"
}

variable "project" {
  description = "Short name prefixed onto every resource."
  type        = string
  default     = "fetchbot"
}

# ── Network ─────────────────────────────────────────────────────────

variable "vpc_cidr" {
  description = "VPC address range. /16 leaves plenty of room to add subnets later."
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = <<-EOT
    Public subnets: route 0.0.0.0/0 to the Internet Gateway.
    The ALB and the EC2 instance live here. Two are required because
    an ALB will not create with fewer than two Availability Zones.
  EOT
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = <<-EOT
    Private subnets: NO route to the internet at all. RDS and
    ElastiCache live here and need no outbound access.

    This is what lets us skip a NAT gateway (~$32/mo, roughly a third
    of the whole budget). If compute ever moves to Fargate in these
    subnets, a NAT gateway or VPC endpoints become mandatory.
  EOT
  type        = list(string)
  default     = ["10.0.11.0/24", "10.0.12.0/24"]
}

variable "admin_cidr_blocks" {
  description = <<-EOT
    CIDRs allowed to reach the EC2 instance on port 22.
    Leave empty (the default) and use SSM Session Manager instead —
    no open SSH port, no long-lived .pem to rotate or leak.
  EOT
  type        = list(string)
  default     = []
}

variable "cloudflare_ipv4_cidrs" {
  description = <<-EOT
    Cloudflare's published IPv4 ranges. Only these may reach the ALB
    on 443, so nobody can bypass Cloudflare by hitting the ALB name
    directly. Refresh from https://www.cloudflare.com/ips-v4 — this
    list does change.
  EOT
  type        = list(string)
  default = [
    "173.245.48.0/20", "103.21.244.0/22", "103.22.200.0/22",
    "103.31.4.0/22", "141.101.64.0/18", "108.162.192.0/18",
    "190.93.240.0/20", "188.114.96.0/20", "197.234.240.0/22",
    "198.41.128.0/17", "162.158.0.0/15", "104.16.0.0/13",
    "104.24.0.0/14", "172.64.0.0/13", "131.0.72.0/22",
  ]
}

# ── Database ────────────────────────────────────────────────────────

variable "db_instance_class" {
  description = "RDS instance class. db.t4g.micro is ~$12/mo and gives ~112 max_connections."
  type        = string
  default     = "db.t4g.micro"
}

variable "db_engine_version" {
  description = <<-EOT
    Must match the source Postgres major version exactly. The current
    container runs postgres:16-alpine, and the Phase 4 logical
    replication cutover depends on the versions lining up.
  EOT
  type        = string
  default     = "16.4"
}

variable "db_allocated_storage" {
  description = "GB of gp3 storage. Autoscales up to db_max_allocated_storage."
  type        = number
  default     = 20
}

variable "db_max_allocated_storage" {
  description = "Storage autoscaling ceiling, so a runaway table cannot fill the disk silently."
  type        = number
  default     = 100
}

variable "db_multi_az" {
  description = <<-EOT
    false by default, deliberately. Multi-AZ adds ~$12/mo for automatic
    failover, but the urgent gap this migration closes is BACKUPS, not
    failover — and Single-AZ RDS already gives automated snapshots and
    point-in-time recovery, which is infinitely more than a Docker
    volume with nothing. Flip to true when revenue justifies it; it is
    an in-place change.
  EOT
  type        = bool
  default     = false
}

variable "db_backup_retention_days" {
  description = "Automated backup retention. Also the point-in-time-recovery window."
  type        = number
  default     = 7
}

variable "db_name" {
  description = "Database name. Matches DB_NAME in .env.prod."
  type        = string
  default     = "growthpilot"
}

variable "db_username" {
  description = <<-EOT
    Master username. Kept as 'postgres' to match the existing
    .env.prod, so the cutover changes DB_HOST and DB_PASSWORD only.
    ('postgres' is permitted on RDS; only 'rdsadmin' is reserved.)
  EOT
  type        = string
  default     = "postgres"
}

# ── Cache ───────────────────────────────────────────────────────────

variable "redis_node_type" {
  description = "ElastiCache node type. cache.t4g.micro is ~$12/mo with 0.5GB."
  type        = string
  default     = "cache.t4g.micro"
}

# ── Compute ─────────────────────────────────────────────────────────

variable "ec2_instance_type" {
  description = "Matches the current box. Bump to t3.medium as the first scaling step."
  type        = string
  default     = "t3.small"
}

variable "ec2_root_volume_gb" {
  description = <<-EOT
    Root volume. The current box runs close to full: two ~1.3GB Docker
    images, no multi-stage build, and deploy.sh has a --clean prune
    step that exists only to work around this. 40GB removes the
    pressure for ~$2/mo.
  EOT
  type        = number
  default     = 40
}

variable "ec2_key_name" {
  description = <<-EOT
    Optional EC2 key pair name for SSH. Leave null to provision no key
    at all and rely on SSM Session Manager, which is the target state
    once Phase 6 lands.
  EOT
  type        = string
  default     = null
}

variable "domain_name" {
  description = "Public hostname. Used for the ACM certificate in Phase 5."
  type        = string
  default     = "fetchbot.ai"
}
