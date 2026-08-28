# Cansee infrastructure

Terraform for the migration described in the AWS migration plan: managed
data layer (RDS + ElastiCache), EC2 compute retained, under $100/mo.

## Before you run anything

**A decision is required first.** The existing EC2 instance
(`100.31.135.211`) is almost certainly in the account's **default VPC**.
This configuration builds a **new** VPC. Resources in different VPCs
cannot reach each other without peering, so the current box cannot talk
to the new RDS instance as-is.

Three ways forward:

| Option | What it means | Verdict |
|---|---|---|
| **Replacement instance in the new VPC** | Add `ec2.tf`, launch a fresh box, migrate, flip Cloudflare DNS. Both stacks run in parallel until verified. | **Recommended.** It is also the cleanest path to the near-zero-downtime cutover, and gives you a rollback that is just "point DNS back". |
| VPC peering | Peer the default VPC to this one, keep the current box. | Works, adds a routing concept you now have to maintain forever, and leaves you on the default VPC. |
| RDS into the default VPC | Skip `vpc.tf` entirely. | Fastest, but you inherit the default VPC's flat public networking and none of the isolation this configuration exists to provide. |

Confirm which VPC the instance is actually in before choosing:

```bash
aws ec2 describe-instances --filters "Name=ip-address,Values=100.31.135.211" --query "Reservations[].Instances[].[InstanceId,VpcId,SubnetId]" --output table
```

## One-time bootstrap

Terraform state lives in S3 with a DynamoDB lock table. A configuration
cannot create the bucket that stores its own state, so these two are
made by hand, once. Replace `<ACCOUNT_ID>`:

```bash
aws s3api create-bucket --bucket cansee-tfstate-<ACCOUNT_ID> --region us-east-1
```

```bash
aws s3api put-bucket-versioning --bucket cansee-tfstate-<ACCOUNT_ID> --versioning-configuration Status=Enabled
```

```bash
aws dynamodb create-table --table-name cansee-tflock --attribute-definitions AttributeName=LockID,AttributeType=S --key-schema AttributeName=LockID,KeyType=HASH --billing-mode PAY_PER_REQUEST --region us-east-1
```

Then copy `backend.hcl.example` to `backend.hcl`, fill in the bucket
name, and initialise:

```bash
terraform init -backend-config=backend.hcl
```

`backend.hcl` and `terraform.tfvars` are gitignored. They contain no
secrets, but they are per-environment and should not be shared.

## Order of operations

The phases gate each other. Do not skip ahead.

**Phase 0 — backups, before anything else.** Apply only the S3 and IAM
pieces, attach the instance profile to the *existing* box, and get
`scripts/backup_db.sh` running on cron:

```bash
terraform apply -target=aws_s3_bucket.backups -target=aws_s3_bucket_versioning.backups -target=aws_s3_bucket_lifecycle_configuration.backups -target=aws_iam_instance_profile.app
```

Then, on the EC2 host, prove the backup actually restores:

```bash
BACKUP_S3_BUCKET=<bucket> bash scripts/backup_db.sh backup && BACKUP_S3_BUCKET=<bucket> bash scripts/backup_db.sh verify
```

`verify` downloads the newest dump, restores it into a throwaway
container, and asserts real row counts. A backup you have not restored
is a hypothesis, not a backup.

**Phase 1 — network.** `terraform apply`. Then confirm the isolation is
real. The private route table must contain **no** `0.0.0.0/0` entry:

```bash
aws ec2 describe-route-tables --route-table-ids $(terraform output -raw private_route_table_id 2>/dev/null || echo "") --query "RouteTables[].Routes[].DestinationCidrBlock" --output text
```

**Phase 2 — data layer.** RDS takes 10-15 minutes to create. Afterwards,
from the app instance, enable pgvector:

```bash
psql "host=$(terraform output -raw db_host) user=postgres dbname=cansee sslmode=require" -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

The connection must succeed from the EC2 instance and fail from
anywhere else. Test both — the second half is the part people skip.

**Phases 3-6** are application changes and `alb.tf` / `ec2.tf`, not yet
in this directory.

## What is here

| File | Purpose |
|---|---|
| `versions.tf` | Provider pins, S3 backend |
| `variables.tf` | All inputs, with the cost of each default called out |
| `vpc.tf` | VPC, subnets, IGW, route tables, S3 gateway endpoint |
| `security_groups.tf` | Four groups that reference each other, not IPs |
| `rds.tf` | Postgres 16, encrypted, 7-day PITR |
| `elasticache.tf` | Redis 7, single node, non-cluster mode |
| `s3.tf` | Backups bucket and assets bucket |
| `iam.tf` | Instance profile: S3, Secrets Manager, Logs, SSM, ECR |
| `outputs.tf` | The values that go into `.env.prod` |

Still to write: `ec2.tf`, `alb.tf`, `cloudfront.tf`, `ecr.tf`.

## Things that will bite you

- **`num_cache_nodes = 1` is load-bearing.** It keeps Redis in
  non-cluster mode. Cluster mode supports only database 0, and this app
  uses db 0 for the cache plus Channels and db 1 for the Celery broker.
  A cluster-mode endpoint would silently merge them.

- **`maxmemory-policy` is `noeviction`, not `allkeys-lru`.** The current
  container uses LRU, which is right for a cache and wrong for a broker:
  under memory pressure Redis will discard queued Celery tasks. Failing
  writes loudly is the better trade. If it starts rejecting writes,
  split the broker onto its own node rather than reverting.

- **The two `PHASE 4` rules in `security_groups.tf`** open port 5432
  between RDS and the app instance in both directions. Logical
  replication is pull-based, so the subscriber connects out to the
  publisher. Delete both once the cutover is verified.

- **`deletion_protection = true` on RDS.** `terraform destroy` will
  refuse. That is the point. Flip it deliberately if you ever mean it.

- **Leave `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` empty** in
  `.env.prod` after attaching the instance profile. boto3 falls through
  to the instance role, and a role cannot be exfiltrated from a file.

- **`performance_insights_enabled = true`** on `db.t4g.micro`. If the
  apply rejects it for the chosen instance class, set it to `false` —
  it is a nice-to-have, not load-bearing.

## Cost

Roughly **$73/mo**: EC2 ~$17, RDS Single-AZ ~$15, ElastiCache ~$12,
ALB ~$18, S3 + CloudFront ~$4, Secrets Manager ~$4, CloudWatch ~$3.

No NAT gateway, deliberately — it would add ~$32/mo, a third of the
budget, to give private subnets outbound internet that nothing here
needs. Multi-AZ RDS is off for the same reason; it is `db_multi_az =
true` when the extra ~$12/mo is worth automatic failover. The urgent
gap this closes is backups, not failover.
