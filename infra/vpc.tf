# ════════════════════════════════════════════════════════════════════
#  VPC — the private network everything else sits inside.
#
#  Three ideas do all the work here:
#
#  1. A SUBNET is an address range pinned to one Availability Zone (a
#     separate physical datacentre). We create two of each kind purely
#     because RDS subnet groups and ALBs both refuse to exist in a
#     single AZ.
#
#  2. "Public" and "private" are not properties of a subnet. They are
#     properties of the ROUTE TABLE attached to it. A public subnet has
#     a route 0.0.0.0/0 -> Internet Gateway. A private subnet has no
#     such route, so nothing in it can reach the internet and nothing
#     on the internet can reach it. That is the entire distinction.
#
#  3. There is deliberately NO NAT gateway. A NAT exists to give
#     private subnets outbound internet, and costs ~$32/mo plus data
#     processing. The only thing here needing outbound access is the
#     EC2 instance (OpenAI, Anthropic, Polar, Slack, Google), and it
#     sits in a public subnet with a direct IGW route. RDS and
#     ElastiCache need no outbound access whatsoever.
# ════════════════════════════════════════════════════════════════════

data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  name = "${var.project}-${var.environment}"

  # Pin to the first two AZs the account can actually use. Hardcoding
  # "us-east-1a" is a common way to get an unlaunchable config, since
  # AZ names are per-account aliases for different physical zones.
  azs = slice(data.aws_availability_zones.available.names, 0, 2)
}

resource "aws_vpc" "main" {
  cidr_block = var.vpc_cidr

  # Both required for RDS/ElastiCache endpoints to resolve by name
  # from inside the VPC. Without them you get an endpoint hostname
  # that nothing can look up.
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = { Name = local.name }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "${local.name}-igw" }
}

# ── Public subnets: ALB + EC2 ────────────────────────────────────────

resource "aws_subnet" "public" {
  count = length(var.public_subnet_cidrs)

  vpc_id            = aws_vpc.main.id
  cidr_block        = var.public_subnet_cidrs[count.index]
  availability_zone = local.azs[count.index]

  # The EC2 needs a routable address to reach the LLM APIs without a
  # NAT gateway. This is the trade that keeps us inside budget; the
  # instance is still firewalled to ALB-only ingress by sg-app.
  map_public_ip_on_launch = true

  tags = {
    Name = "${local.name}-public-${local.azs[count.index]}"
    Tier = "public"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "${local.name}-public" }
}

resource "aws_route" "public_internet" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.main.id
}

resource "aws_route_table_association" "public" {
  count          = length(aws_subnet.public)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# ── Private subnets: RDS + ElastiCache ───────────────────────────────

resource "aws_subnet" "private" {
  count = length(var.private_subnet_cidrs)

  vpc_id            = aws_vpc.main.id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = local.azs[count.index]

  tags = {
    Name = "${local.name}-private-${local.azs[count.index]}"
    Tier = "private"
  }
}

# This route table intentionally contains ONLY the implicit local
# route for the VPC CIDR. Adding a 0.0.0.0/0 entry here would silently
# undo the isolation these subnets exist to provide.
#
# Phase 1 verification: confirm this table has no 0.0.0.0/0 route.
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "${local.name}-private" }
}

resource "aws_route_table_association" "private" {
  count          = length(aws_subnet.private)
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

# ── S3 gateway endpoint ──────────────────────────────────────────────
#
# Free, unlike interface endpoints. Keeps S3 traffic (backups, static,
# media) on the AWS backbone rather than out through the IGW, which
# both avoids egress charges and means an instance could still reach
# S3 if it were ever moved to a private subnet.
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"

  route_table_ids = [
    aws_route_table.public.id,
    aws_route_table.private.id,
  ]

  tags = { Name = "${local.name}-s3-endpoint" }
}
