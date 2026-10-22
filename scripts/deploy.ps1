<#
.SYNOPSIS
    Deploys Pillarscan to AWS from nothing, or updates a deployment.

.DESCRIPTION
    1. infra/bootstrap  Creates the Terraform state bucket, if needed, and
                        writes its name to infra/platform/backend.hcl.
    2. Lambda packages  Builds build/scanner and build/api.
    3. infra/platform   Creates or updates everything else.
    4. infra/bait       Only with -WithBait.

    Each `terraform apply` shows its plan and waits for you to type yes.
    Run it in the folder you cloned, after `aws login`, with the project's
    virtual environment active (the Lambda build uses its Python).

.EXAMPLE
    .\scripts\deploy.ps1
.EXAMPLE
    .\scripts\deploy.ps1 -WithBait
#>
[CmdletBinding()]
param(
    [string]$AwsProfile = "pillarscan",
    [switch]$WithBait
)

. (Join-Path $PSScriptRoot "common.ps1")

$PlatformDir = Join-Path $InfraRoot "platform"
$BaitDir = Join-Path $InfraRoot "bait"
$BootstrapDir = Join-Path $InfraRoot "bootstrap"

Assert-Tools
$identity = Use-AwsLogin -AwsProfile $AwsProfile
Write-Host "AWS account $($identity.Account), signed in as $($identity.Arn)"

Write-Host "`n== infra/bootstrap" -ForegroundColor Cyan
Invoke-Native -File terraform -Arguments @("-chdir=$BootstrapDir", "init", "-input=false")
Invoke-Native -Interactive -File terraform -Arguments @("-chdir=$BootstrapDir", "apply", "-input=false")
$bucket = (& terraform "-chdir=$BootstrapDir" output -raw state_bucket)
if ($LASTEXITCODE -ne 0 -or -not $bucket) { throw "The bootstrap has no state_bucket output." }
# backend.hcl is git-ignored: the bucket name is unique to this account.
Set-Content -Path (Join-Path $PlatformDir "backend.hcl") -Value "bucket = `"$bucket`"" -Encoding ascii
Write-Host "State bucket: $bucket"

Write-Host "`n== Lambda packages" -ForegroundColor Cyan
Invoke-Native -File python -Arguments @((Join-Path $PSScriptRoot "build_lambdas.py"))

Write-Host "`n== infra/platform" -ForegroundColor Cyan
Invoke-Native -File terraform -Arguments @("-chdir=$PlatformDir", "init", "-input=false", "-reconfigure", "-backend-config=backend.hcl")
Invoke-Native -Interactive -File terraform -Arguments @("-chdir=$PlatformDir", "apply", "-input=false")

if ($WithBait) {
    Write-Host "`n== infra/bait" -ForegroundColor Cyan
    Invoke-Native -File terraform -Arguments @("-chdir=$BaitDir", "init", "-input=false")
    Invoke-Native -Interactive -File terraform -Arguments @("-chdir=$BaitDir", "apply", "-input=false")
}

function Get-Output([string]$Name) {
    return (& terraform "-chdir=$PlatformDir" output -raw $Name)
}

$apiUrl = Get-Output "api_url"
$cognitoDomain = Get-Output "cognito_domain"
$clientId = Get-Output "cognito_client_id"
$poolId = Get-Output "user_pool_id"

Write-Host "`n== Done. Next steps" -ForegroundColor Green
Write-Host @"
1. Point the site at this deployment. In Vercel: Project > Settings >
   Environment Variables, set these for Production, then redeploy:
     NEXT_PUBLIC_API_URL            $apiUrl
     NEXT_PUBLIC_COGNITO_DOMAIN     $cognitoDomain
     NEXT_PUBLIC_COGNITO_CLIENT_ID  $clientId
   (Or update the fallbacks in web/lib/api.ts and web/lib/auth.ts.)

2. Invite yourself again; the user pool is new:
     aws cognito-idp admin-create-user --user-pool-id $poolId --username <your-email> --profile $AwsProfile

3. If alarm_email is set in infra/platform/terraform.tfvars, confirm the
   subscription email AWS sends, or alarms will not reach you.

To remove everything later:  .\scripts\destroy.ps1
"@
