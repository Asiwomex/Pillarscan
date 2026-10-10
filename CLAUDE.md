# Pillarscan

A self-service AWS posture review tool: it scans an AWS account with read-only access and reports findings ranked by severity across three AWS Well-Architected pillars (Security, Reliability, Cost Optimization). Inspired by refraxion.io, but with its own name, design and code.

## Purpose and audience

- This is a **portfolio project**, not a business. The owner will record videos of it and show it to recruiters.
- Priorities, in order: (1) a live demo anyone can open without an AWS account, (2) clean, readable code that shows cloud and security understanding, (3) a clear README with an architecture diagram.
- The name is **Pillarscan** and the site's permanent address is https://pillarscan.lytaworks.com/ (owner's decision, 2026-10-10). No separate domain will be bought.
- Do not put "AWS" in the product name, and do not copy Refraxion's branding or visual design.

## Decisions already made (do not reopen without asking)

- **Write our own scanner.** Do not wrap Prowler. Prowler already ships its own web UI and API, so a wrapper adds little. Our own checks are the main thing a recruiter will look at.
- **One AWS account only.** The platform, the deliberately misconfigured "bait" resources, and the first scanned account are all the same account. The scanner still uses `sts:AssumeRole` with an external ID, so the cross-account code path is real.
- **Demo mode is required.** The landing page must open straight into a populated dashboard using scrubbed sample data, with no sign-in.
- **Keep cost near zero.** Target is well under $1 a month.

## Stack

| Layer | Choice | Runs on |
|---|---|---|
| Frontend | Next.js (App Router, whatever `create-next-app@latest` installs), TypeScript, Tailwind CSS, shadcn/ui | Vercel Hobby plan |
| Charts / tables | Recharts, TanStack Table | Frontend |
| API | Python 3.12+, FastAPI, packaged for Lambda | Lambda behind API Gateway HTTP API |
| Scanner | Python 3.12+, boto3, one file per check | Second Lambda, triggered through SQS |
| Database | DynamoDB, single table (accounts, scans, findings) | AWS |
| Auth | Amazon Cognito + API Gateway JWT authorizer | AWS |
| Onboarding | CloudFormation template that creates a read-only role with an external ID | Template in a public S3 bucket |
| Infrastructure | Terraform, remote state in S3 | Local machine and CI |
| CI/CD | GitHub Actions, AWS access through OIDC (no stored keys) | GitHub |
| Tests | pytest + moto (mocked AWS) | Local and CI |
| Monitoring | CloudWatch logs, one alarm on scanner errors | AWS |

Package managers: `pnpm` for the frontend, `uv` or `pip` + `venv` for Python (ask the owner which they prefer the first time it matters).

## Repo layout

```
pillarscan/
  web/          Next.js app
  api/          FastAPI service
  scanner/      checks/, engine, findings schema, CLI entry point
  infra/        Terraform
  onboarding/   CloudFormation template for the read-only role
  sample-data/  scrubbed scan output used by demo mode
  docs/         architecture diagram, screenshots
  .github/workflows/
```

## Findings schema

Every check returns zero or more findings in this shape. The frontend, API and database all use it, so change it deliberately.

```json
{
  "check_id": "s3_public_access_block",
  "title": "S3 bucket without public access block",
  "pillar": "security",
  "severity": "high",
  "status": "fail",
  "resource_arn": "arn:aws:s3:::example-bucket",
  "resource_type": "AWS::S3::Bucket",
  "region": "us-east-1",
  "account_id": "000000000000",
  "description": "What is wrong and why it matters.",
  "remediation": "Concrete steps to fix it.",
  "scanned_at": "2026-10-09T21:00:00Z"
}
```

- `pillar`: `security` | `reliability` | `cost`
- `severity`: `critical` | `high` | `medium` | `low`
- `status`: `pass` | `fail` | `error`

## Checks to implement first

Security
- Root account without MFA
- IAM users without MFA
- Access keys older than 90 days
- Policies granting `*` on `*`
- S3 buckets without public access block
- Security groups open to 0.0.0.0/0 on port 22 or 3389
- CloudTrail not enabled in all regions
- Publicly accessible RDS instances
- GuardDuty not enabled
- EBS default encryption off

Reliability
- RDS without Multi-AZ
- RDS automated backups disabled
- S3 versioning off
- DynamoDB tables without point-in-time recovery
- Lambda functions without a dead-letter queue
- Auto scaling groups in a single availability zone

Cost
- Unattached EBS volumes
- Unassociated Elastic IPs
- gp2 volumes that could be gp3
- Snapshots older than 90 days
- Load balancers with no targets
- CloudWatch log groups with no retention set

## Build order

1. **Scanner as a CLI.** `python -m scanner --profile <name> --out findings.json`. Engine discovers checks in `scanner/checks/`, runs them across regions, writes findings in the schema above. Every check has a moto test.
2. **Dashboard on that JSON.** Posture score, findings by pillar and severity, filterable table, detail panel with remediation. Deploy to Vercel in demo mode using `sample-data/`.
3. **Backend.** Terraform for DynamoDB, both Lambdas, SQS and API Gateway. Frontend reads from the API and shows scan history.
4. **Connect-account flow.** Cognito sign-in, the CloudFormation template, and a "run scan" button that assumes the role in the connected account.
5. **Polish.** GitHub Actions pipeline, README with architecture diagram, demo video.

Each stage must leave something showable. Do not start a later stage before the current one works end to end.

## Current status

- Repo: `github.com/Asiwomex/Pillarscan`. Python uses `pip` + `venv` (`.venv/`, Python 3.13 locally); `uv` is not installed.
- Stage 1 code is complete: findings schema (`scanner/findings.py`), check contract (`scanner/check.py`), engine and CLI, and all 22 checks in `scanner/checks/`, each with moto tests in `tests/scanner/` (run `pytest`). moto cannot model root MFA or Lambda dead-letter config, so those two pass cases use a botocore `Stubber`.
- The CLI writes `{"scan": {...metadata}, "findings": [...]}`; each finding follows the schema above.
- AWS access: CLI profile `pillarscan` (short-lived `aws login` credentials, which is why `botocore[crt]` is a dev dependency), default region `us-east-1`. Root and the IAM admin user both have MFA.
- First real scan done: 22 checks across 17 regions in under a minute, no errors.
- Bait lives in `infra/bait/` (Terraform, local git-ignored state, run with `AWS_PROFILE=pillarscan`): an empty bucket without a public access block, an unattached security group open on 22/3389, a 1 GB gp2 volume, and `pillarscan-bait-user` (no password, so not yet flagged).
- `python -m scanner.scrub findings.json sample-data/findings.json` produces the demo data; `sample-data/findings.json` exists (59 findings, 40 failing).
- AWS: the owner has one account and has just created an IAM admin user to use instead of root. MFA on root and on the IAM user may not be set up yet; ask before assuming.
- The console appeared to be set to `us-east-2`; confirm the default region with the owner.
- Development machine is Windows. Prefer commands that work in PowerShell or Git Bash, and say which.
- Demo data: `sample-data/demo-findings.json` is generated by `sample-data/generate_demo.py` (the real scanner run against moto, a fictional account covering all 22 checks). It is kept separate from the real scrubbed scan in `sample-data/findings.json`.
- Stage 2 dashboard built in `web/` (Next.js 16, Tailwind 4, shadcn/ui on Base UI, TanStack Table v9, Recharts 3; `pnpm` is installed globally). It reads both sample-data files at build time and is fully static. Design is specified in `DESIGN.md` at the repo root and the build follows it: a dark landing page (hero, how it works, checks, project status) around a light, flat dashboard that is embedded as the live demo, all in Instrument Sans, with each pillar drawn as a wall of blocks (one block per finding, teal when passing, severity-coloured when failing). The owner pointed at refraxion.io as the level of polish they want; take its structure and confidence, never its branding (prism, gradient text, starfield, Sora). The owner rejected the first version (cream paper, serif headlines, hairline rules) as not looking good; do not go back to it. `web/AGENTS.md` says to read `node_modules/next/dist/docs/` before changing Next.js code, because v16 differs from older versions.
- The site has a fixed top menu, a share image (`web/app/opengraph-image.tsx`), a favicon and a 404 page. Footer credits are fixed by the owner: "Built by Asiwome Boateng" linking to https://asiwomex.vercel.app/ and "Powered by LytaWorks" linking to https://lytaworks.com/ (all in `web/lib/links.ts`). The owner wants it to work well on phones.
- The CLI can scan through the audit role: `--role-arn` with `--external-id` (both required together; `scanner/session.py`). The role template is `onboarding/pillarscan-role.yaml`. It is deployed in the real account as CloudFormation stack `pillarscan-audit-role` (us-east-1). A scan through it ran all 22 checks with no errors, and a wrong external ID is refused. The role ARN and external ID are in the git-ignored `.env` at the repo root (`PILLARSCAN_ROLE_ARN`, `PILLARSCAN_EXTERNAL_ID`); never print or commit the external ID.
- CI is `.github/workflows/ci.yml`: pytest on Python 3.12 and 3.13, `cfn-lint` on the role template, and the site's lint and build (the build type-checks; a separate `tsc` step fails in CI because Next.js generates the `LayoutProps` global during the build). No AWS access in CI yet.
- Live at https://pillarscan.lytaworks.com/ (primary) and https://pillarscan.vercel.app/. Vercel deploys every push to `main`, so a push is a production release. Push one commit at a time and let its deployment finish before pushing the next: on 2026-10-10 a second push two minutes after the first made Vercel fail the second deployment within seconds (the first then deployed normally). Check with `gh api repos/Asiwomex/Pillarscan/commits/<sha>/statuses`.
- Lighthouse, phone profile, on the live site on 2026-10-09: performance 77, accessibility 97. The chart library is now loaded only when the chart scrolls into view (`web/components/service-chart-frame.tsx`), which measured 95 / 100 on a local production build. Re-measure the live site after it deploys.
- Stage 3 backend is applied and working (applied 2026-10-09). A scan requested through the queue lands in DynamoDB in about 20 seconds with no errors, and the API serves it. API base URL: https://kzowp5bd5l.execute-api.us-east-1.amazonaws.com (also the default in `web/lib/api.ts`). Pieces:
  - `scanner/store.py`: DynamoDB single-table storage (summary item per scan under `ACCOUNT#<id>`, one item per finding under `SCAN#<id>`, 90-day TTL). `scanner/score.py` mirrors `web/lib/score.ts`; change both together.
  - `scanner/lambda_handler.py`: scanner Lambda. Assumes the audit role with the external ID read from SSM, scans, scrubs (`SCRUB_OUTPUT=true`) and stores.
  - `api/`: FastAPI on Lambda via Mangum, read-only: `GET /health`, `GET /scans`, `GET /scans/{scan_id}` (`latest` works). Public until stage 4, which is why stored scans are scrubbed and the API only serves account `000000000000`.
  - `scripts/build_lambdas.py` builds `build/scanner` and `build/api` (Linux arm64 wheels) for Terraform to zip. Run it before `terraform plan`.
  - `infra/bootstrap/` creates the state bucket (local state). `infra/platform/` is the platform, with an S3 backend whose bucket name comes from the git-ignored `infra/platform/backend.hcl`.
  - Done by hand outside Terraform: the external ID is in SSM SecureString `/pillarscan/external-id`, and the `pillarscan-audit-role` stack now trusts the account root so the scanner Lambda's role can assume the role.
  - Running Terraform here: its S3 backend cannot read `aws login` credentials, so export them first: `eval "$(aws configure export-credentials --profile pillarscan --format env)"` and unset `AWS_PROFILE`. In Git Bash set `MSYS_NO_PATHCONV=1` for AWS CLI arguments that start with `/`.
  - `infra/platform/terraform.tfvars` (git-ignored) holds `alarm_email`. The owner must confirm the SNS subscription email before alarm emails arrive.
  - The dashboard's "Live account" option loads `/scans` and `/scans/latest` when first opened and falls back to `sample-data/findings.json` if the API fails.
  - `lambda_dead_letter_queue` now accepts an on-failure destination and leaves out functions that are only called synchronously or that read from a queue or stream, so the platform no longer flags its own Lambdas. The deployed scanner Lambda needs a `terraform apply` to pick this up.
  - The site has unit tests for the score formula (`pnpm test`, vitest), mirroring the Python cases.
- Owner decisions (2026-10-10): no console password on the bait user (they do not want an MFA failure in the real scan); stage 4 sign-in is invite only (sign-up closed, the owner creates users).
- Stage 4 is built (2026-10-10). Sign-in is by invitation through a Cognito user pool (`infra/platform/auth.tf`, pool `us-east-1_b632XdIY1`, self sign-up off). Pieces:
  - `scanner/accounts.py`: connected accounts under `USER#<sub>`, each with a generated external ID and role name suffix. Scans are owner-scoped in `scanner/store.py` (`ACCOUNT#<owner>`, `SCAN#<owner>#<scan_id>`); the public owner is `000000000000`, a user's is `<sub>:<aws account id>`.
  - API `/me/...` routes behind an API Gateway JWT authorizer; the API reads the user only from the verified token. Limits: 5 accounts per user, one scan request per account every 2 minutes.
  - `scanner/lambda_handler.py` handles both request kinds: `{}` (public, always scrubbed) and `{user_id, aws_account_id}` (private, unscrubbed).
  - The role template takes a `RoleNameSuffix`, and is served publicly from the `pillarscan-onboarding-*` bucket for CloudFormation's quick-create link. The scanner reports that bucket; that is expected.
  - Site: `/account` (`web/components/account/`, `web/lib/auth.ts` for PKCE sign-in). The Cognito domain and client ID are public values in `web/lib/auth.ts`.
  - Verified end to end by the owner on 2026-10-10: they signed in, connected their account, created the role and ran a scan; their screenshots show the private scan (42 of 67 checks failed, score 50). The findings table groups a finding repeated across regions into one row (`groupAcrossRegions` in `web/lib/findings.ts`).
  - The Lambda build with the `scanning` account status is deployed (2026-10-10). The owner's Cognito user is `asi@lytaworks.com`, created the same day and waiting for its first sign-in.
- Standing instruction from the owner (2026-10-10): for this project, do the work and keep pushing; do not wait for a separate go-ahead to commit and push.
- **Next step:** all five build stages are done. Remaining: the owner records the demo video; then add its link to the README and the site. Never write the owner's real AWS account ID into the repo, even though it appears in their screenshots.

## Rules

Security and secrets
- Never commit AWS account IDs, access keys, ARNs from the real account, or `.env` files. Use `000000000000` in examples and scrub `sample-data/`.
- The onboarding role attaches only the AWS managed policies `SecurityAudit` and `ViewOnlyAccess`. The scanner must never call a write API.
- Role assumption always passes an external ID.
- Prefer short-lived credentials (`aws login` in recent AWS CLI v2) over long-lived access keys.

Cost
- Do not call the Cost Explorer API (it is billed per request). Cost checks are resource-based.
- Never leave these running as bait: Elastic IPs, load balancers, RDS instances, NAT gateways. Test those checks with moto instead.
- Cheap bait is fine: empty buckets, unattached security groups, a 1 GB unattached volume, IAM users with no permissions. Never attach an open security group to a running instance.
- Tag everything: `project=pillarscan` for the platform, `project=pillarscan-bait` for bait.
- Ask before creating any AWS resource that is not covered by an always-free allowance.

Code
- One check per file in `scanner/checks/`, named after its `check_id`.
- A check that fails to run returns a finding with `status: "error"`; it must not crash the scan.
- Handle pagination on every list/describe call.
- Type hints throughout the Python code; TypeScript strict mode in the frontend.

Working style
- The owner is building this to learn as well as to show. Explain non-obvious AWS and security decisions briefly as you go.
- Ask before running anything against the real AWS account for the first time in a session.
