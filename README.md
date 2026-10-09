# Pillarscan

Pillarscan scans an AWS account with read-only access and reports what it finds, ranked by severity, across three Well-Architected pillars: Security, Reliability and Cost Optimization.

It is a work in progress. The scanner runs as a command-line tool today; the dashboard, API and connect-account flow come next.

## Run the scanner

Requires Python 3.12 or newer. Commands are for PowerShell.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python -m scanner --profile <aws-profile> --out findings.json
```

The scanner only calls read APIs (`Get*`, `List*`, `Describe*`). The `SecurityAudit` and `ViewOnlyAccess` managed policies are enough to run it.

`findings.json` contains real account IDs and ARNs, so it is git-ignored.

## Checks

| Check | Pillar | Severity |
|---|---|---|
| `iam_root_mfa`: root account without MFA | Security | Critical |
| `iam_user_mfa`: IAM user with a console password and no MFA | Security | High |
| `iam_access_key_age`: active access key older than 90 days | Security | Medium |

Each check is one file in [scanner/checks](scanner/checks), named after its `check_id`. A check that cannot run produces a finding with status `error` and the scan carries on.

## Tests

```powershell
pytest
```

Tests run against [moto](https://github.com/getmoto/moto), which mocks AWS in memory. They never touch a real account.
