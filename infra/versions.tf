# ════════════════════════════════════════════════════════════════════
#  Terraform + provider pins, and remote state.
#
#  State is kept in S3 with a DynamoDB lock table. Both must exist
#  BEFORE the first `terraform init` — see infra/README.md for the
#  one-time bootstrap. They are deliberately not managed by this
#  configuration: a config cannot create the bucket that holds its
#  own state.
# ════════════════════════════════════════════════════════════════════

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
  }

  # Partial config. Supply the rest via:
  #   terraform init -backend-config=backend.hcl
  backend "s3" {}
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "cansee"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
