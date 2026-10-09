# Pillarscan

Pillarscan scans an AWS account with read-only access and reports what it finds, ranked by severity, across three Well-Architected pillars: Security, Reliability and Cost Optimization.

It is a work in progress. The scanner and the dashboard work today, on sample data; the API and the connect-account flow come next.

## Run the scanner

Requires Python 3.12 or newer. Commands are for PowerShell.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python -m scanner --profile <aws-profile> --out findings.json
```

The scanner only calls read APIs (`Get*`, `List*`, `Describe*`). The `SecurityAudit` and `ViewOnlyAccess` managed policies are enough to run it.

`findings.json` contains real account IDs and ARNs, so it is git-ignored. To publish a scan as demo data, scrub it first:

```powershell
python -m scanner.scrub findings.json sample-data/findings.json
```

## Checks

All 22 checks, grouped by pillar.

| Check | What it flags | Pillar | Severity |
|---|---|---|---|
| `iam_root_mfa` | Root account without MFA | Security | Critical |
| `cloudtrail_multi_region` | CloudTrail not enabled in all regions | Security | High |
| `ec2_security_group_open_admin_ports` | Security group open to the internet on port 22 or 3389 | Security | High |
| `iam_policy_full_admin` | IAM policy granting * on * | Security | High |
| `iam_user_mfa` | IAM user without MFA | Security | High |
| `rds_public_access` | Publicly accessible RDS instance | Security | High |
| `s3_public_access_block` | S3 bucket without public access block | Security | High |
| `ebs_default_encryption` | EBS default encryption off | Security | Medium |
| `guardduty_enabled` | GuardDuty not enabled | Security | Medium |
| `iam_access_key_age` | Access key older than 90 days | Security | Medium |
| `rds_backup_retention` | RDS automated backups disabled | Reliability | High |
| `autoscaling_single_az` | Auto scaling group in a single availability zone | Reliability | Medium |
| `dynamodb_pitr` | DynamoDB table without point-in-time recovery | Reliability | Medium |
| `rds_multi_az` | RDS instance without Multi-AZ | Reliability | Medium |
| `lambda_dead_letter_queue` | Lambda function without a dead-letter queue | Reliability | Low |
| `s3_versioning` | S3 bucket without versioning | Reliability | Low |
| `ebs_unattached_volume` | Unattached EBS volume | Cost | Medium |
| `elb_no_targets` | Load balancer with no targets | Cost | Medium |
| `ebs_gp2_volume` | gp2 volume that could be gp3 | Cost | Low |
| `ebs_old_snapshot` | EBS snapshot older than 90 days | Cost | Low |
| `ec2_unassociated_eip` | Unassociated Elastic IP | Cost | Low |
| `logs_no_retention` | CloudWatch log group with no retention set | Cost | Low |

Each check is one file in [scanner/checks](scanner/checks), named after its `check_id`. A check that cannot run produces a finding with status `error` and the scan carries on. Checks run once per enabled region unless the service is global; pass `--regions us-east-1,us-east-2` to limit a scan.

## Dashboard

A Next.js app in [web](web) that shows a scan: a posture score, a score per pillar, failed checks by severity, and a filterable table with a detail panel that explains each finding and how to fix it. It opens straight into sample data, with no sign-in.

```powershell
cd web
pnpm install
pnpm dev
```

The score is the severity-weighted share of checks that passed; see [web/lib/score.ts](web/lib/score.ts).

## Sample data

The dashboard reads two files in [sample-data](sample-data):

- `demo-findings.json`: a fictional company's account. [generate_demo.py](sample-data/generate_demo.py) builds it by running the real scanner against mocked AWS, so every check has something to show without paying for RDS instances or load balancers.
- `findings.json`: a scan of this project's own AWS account, scrubbed. The misconfigured resources in it are created on purpose by [infra/bait](infra/bait).

## Tests

```powershell
pytest
```

Tests run against [moto](https://github.com/getmoto/moto), which mocks AWS in memory. They never touch a real account.
