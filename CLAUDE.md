# Pillarscan

A self-service AWS posture review tool: it scans an AWS account with read-only access and reports findings ranked by severity across three AWS Well-Architected pillars (Security, Reliability, Cost Optimization). Inspired by refraxion.io, but with its own name, design and code.

## Purpose and audience

- This is a **portfolio project**, not a business. The owner will record videos of it and show it to recruiters.
- Priorities, in order: (1) a live demo anyone can open without an AWS account, (2) clean, readable code that shows cloud and security understanding, (3) a clear README with an architecture diagram.
- Working name is **Pillarscan**. A web search found no existing product with that name. Domain and social handles have NOT been checked yet (owner to check `pillarscan.dev` / `pillarscan.io`).
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
- The CLI can scan through the audit role: `--role-arn` with `--external-id` (both required together; `scanner/session.py`). The role template is `onboarding/pillarscan-role.yaml`. It has passed `cfn-lint` but has NOT been deployed to the real account, so a scan with only `SecurityAudit` + `ViewOnlyAccess` is still unproven.
- CI is `.github/workflows/ci.yml`: pytest on Python 3.12 and 3.13, `cfn-lint` on the role template, and the site's lint, type-check and build. No AWS access in CI yet.
- Not yet deployed to Vercel.
- **Next step: deploy `web/` to Vercel** (owner links the GitHub repo with root directory `web`, keeping "include files outside the root directory" on so `sample-data/` is available at build). Then stage 3, the backend.

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
