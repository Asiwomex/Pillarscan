<#
.SYNOPSIS
    Removes everything Pillarscan created in AWS, in the right order.

.DESCRIPTION
    1. infra/platform   Turns deletion protection off, then destroys the
                        Lambdas, API, table, user pool, queues, schedule,
                        alarms, the audit role and its external ID.
    2. infra/bait       Destroys the deliberately misconfigured resources.
    3. infra/bootstrap  Destroys the Terraform state bucket, emptying every
                        version in it first. Only with -IncludeBootstrap,
                        because the next deploy can reuse the bucket.

    Then it asks AWS for anything still tagged project=pillarscan or
    project=pillarscan-bait, for Pillarscan IAM roles and for role stacks
    made from the onboarding template, and exits with an error if it finds
    any. Run it in the folder you cloned, after `aws login`.

.EXAMPLE
    .\scripts\destroy.ps1
.EXAMPLE
    .\scripts\destroy.ps1 -IncludeBootstrap
.EXAMPLE
    .\scripts\destroy.ps1 -CheckOnly    # only look for leftovers
#>
[CmdletBinding()]
param(
    [string]$AwsProfile = "pillarscan",
    [switch]$IncludeBootstrap,
    [switch]$CheckOnly,
    # Skip the confirmation prompts.
    [switch]$Yes
)

. (Join-Path $PSScriptRoot "common.ps1")

$Regions = @("us-east-1", "us-east-2")
$PlatformDir = Join-Path $InfraRoot "platform"
$BaitDir = Join-Path $InfraRoot "bait"
$BootstrapDir = Join-Path $InfraRoot "bootstrap"

function Initialize-Folder {
    # Returns $false if Terraform cannot reach the folder's state.
    param([string]$Directory, [string[]]$Extra = @())
    $ErrorActionPreference = "Continue"
    & terraform "-chdir=$Directory" init -input=false -reconfigure @Extra | Out-Null
    return ($LASTEXITCODE -eq 0)
}

function Sync-State {
    # Bring Terraform's record up to date with AWS before deciding anything.
    # Without this, a resource deleted by hand would look missing, and the
    # targeted apply below would create it again.
    param([string]$Directory)
    Invoke-Native -File terraform -Arguments @("-chdir=$Directory", "apply", "-refresh-only", "-input=false", "-auto-approve")
    return Get-StateAddresses $Directory
}

function Disable-Protection {
    # Deletion protection is a setting on the resource itself, so it has to
    # be switched off by an apply before a destroy can succeed.
    param([string]$Directory, [string[]]$State, [string[]]$Addresses)
    $present = @($Addresses | Where-Object { $State -contains $_ })
    if ($present.Count -eq 0) { return }
    $arguments = @("-chdir=$Directory", "apply", "-input=false", "-auto-approve", "-var", "protect=false")
    foreach ($address in $present) { $arguments += "-target=$address" }
    Invoke-Native -File terraform -Arguments $arguments
}

function Remove-Platform {
    Write-Host "`n== infra/platform" -ForegroundColor Cyan
    if (-not (Test-Path (Join-Path $PlatformDir "backend.hcl"))) {
        Write-Host "No backend.hcl, so it was never deployed from this folder. Skipping."
        return
    }
    if (-not (Initialize-Folder $PlatformDir @("-backend-config=backend.hcl"))) {
        Write-Warning "Cannot reach the platform's state (is the state bucket gone?). The check at the end will show anything left."
        return
    }
    Assert-LambdaBuild
    $state = Sync-State $PlatformDir
    if ($state.Count -eq 0) { Write-Host "Nothing deployed."; return }
    Disable-Protection $PlatformDir $state @("aws_dynamodb_table.scans", "aws_cognito_user_pool.this", "aws_s3_bucket.onboarding")
    Invoke-Native -File terraform -Arguments @("-chdir=$PlatformDir", "destroy", "-input=false", "-auto-approve", "-var", "protect=false")
}

function Remove-Bait {
    Write-Host "`n== infra/bait" -ForegroundColor Cyan
    if (-not (Initialize-Folder $BaitDir)) { throw "terraform init failed in infra/bait" }
    $state = Sync-State $BaitDir
    if ($state.Count -eq 0) { Write-Host "Nothing deployed."; return }
    Invoke-Native -File terraform -Arguments @("-chdir=$BaitDir", "destroy", "-input=false", "-auto-approve")
}

function Remove-Bootstrap {
    Write-Host "`n== infra/bootstrap" -ForegroundColor Cyan
    if (-not (Initialize-Folder $BootstrapDir)) { throw "terraform init failed in infra/bootstrap" }
    $state = Sync-State $BootstrapDir
    if ($state.Count -gt 0) {
        Disable-Protection $BootstrapDir $state @("aws_s3_bucket.state")
        Invoke-Native -File terraform -Arguments @("-chdir=$BootstrapDir", "destroy", "-input=false", "-auto-approve", "-var", "protect=false")
    }
    else {
        Write-Host "Nothing deployed."
    }
    # It names a bucket that no longer exists; deploy.ps1 writes a new one.
    Remove-Item (Join-Path $PlatformDir "backend.hcl") -ErrorAction SilentlyContinue
}

function Read-JsonList {
    # Two steps on purpose: Windows PowerShell 5.1 passes a parsed JSON
    # array down the pipeline as one object.
    param([object[]]$Text)
    $parsed = ($Text | Out-String) | ConvertFrom-Json
    return @($parsed | Where-Object { $_ })
}

function Find-Leftovers {
    Write-Host "`n== Checking for anything left" -ForegroundColor Cyan
    $left = @()

    foreach ($region in $Regions) {
        $text = & aws resourcegroupstaggingapi get-resources --region $region `
            --tag-filters "Key=project,Values=pillarscan,pillarscan-bait" `
            --query "ResourceTagMappingList[].ResourceARN" --output json
        if ($LASTEXITCODE -ne 0) { throw "Could not list tagged resources in $region." }
        $arns = Read-JsonList $text
        if (-not $IncludeBootstrap) {
            # Kept on purpose without -IncludeBootstrap.
            $arns = @($arns | Where-Object { $_ -notlike "arn:aws:s3:::pillarscan-tfstate-*" })
        }
        $left += $arns
    }

    # The tag lookup is not always prompt about IAM, so ask IAM directly.
    $text = & aws iam list-roles --output json `
        --query "Roles[?starts_with(RoleName, 'Pillarscan') || starts_with(RoleName, 'pillarscan')].Arn"
    if ($LASTEXITCODE -ne 0) { throw "Could not list IAM roles." }
    $left += Read-JsonList $text

    # Role stacks a signed-in user (you, in this account) made from the
    # onboarding template. Pillarscan can never delete these from inside
    # the app: it has read-only access by design.
    $text = & aws cloudformation list-stacks --region us-east-1 --output json `
        --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE UPDATE_ROLLBACK_COMPLETE ROLLBACK_COMPLETE IMPORT_COMPLETE `
        --query "StackSummaries[?starts_with(StackName, 'pillarscan-')].StackName"
    if ($LASTEXITCODE -ne 0) { throw "Could not list CloudFormation stacks." }
    $stacks = Read-JsonList $text

    if ($stacks.Count -gt 0) {
        Write-Host "Role stacks made from the onboarding template:"
        $stacks | ForEach-Object { Write-Host "  $_" }
        $answer = "n"
        if ($Yes) { $answer = "y" }
        elseif (-not $CheckOnly) { $answer = Read-Host "Delete these stacks too? (y/N)" }
        if ($answer -eq "y") {
            foreach ($stack in $stacks) {
                Invoke-Native -File aws -Arguments @("cloudformation", "delete-stack", "--region", "us-east-1", "--stack-name", $stack)
                Invoke-Native -File aws -Arguments @("cloudformation", "wait", "stack-delete-complete", "--region", "us-east-1", "--stack-name", $stack)
                Write-Host "  deleted $stack"
            }
            # Their roles are gone with them.
            $left = @($left | Where-Object { $_ -notlike "arn:aws:iam::*:role/PillarscanAuditRole-*" })
        }
        else {
            $left += $stacks | ForEach-Object { "cloudformation stack: $_" }
        }
    }

    $left = @($left | Sort-Object -Unique)
    if ($left.Count -eq 0) {
        Write-Host "Nothing from Pillarscan is left in this account." -ForegroundColor Green
        return $true
    }
    Write-Host "Still present:" -ForegroundColor Yellow
    $left | ForEach-Object { Write-Host "  $_" }
    Write-Host "Resources deleted in the last hour can linger in the tag lookup. Run '.\scripts\destroy.ps1 -CheckOnly' again later before deleting anything by hand."
    return $false
}

Assert-Tools
$identity = Use-AwsLogin -AwsProfile $AwsProfile
Write-Host "AWS account $($identity.Account), signed in as $($identity.Arn)"

if (-not $CheckOnly) {
    if (-not $Yes) {
        $what = "the platform and the bait"
        if ($IncludeBootstrap) { $what = "the platform, the bait and the Terraform state bucket" }
        Write-Host "This permanently deletes $what, including every stored scan and every user." -ForegroundColor Yellow
        $answer = Read-Host "Type 'destroy' to continue"
        if ($answer -ne "destroy") { Write-Host "Nothing was changed."; exit 1 }
    }
    Remove-Platform
    Remove-Bait
    if ($IncludeBootstrap) { Remove-Bootstrap }
    else { Write-Host "`nKept the Terraform state bucket (infra/bootstrap). Add -IncludeBootstrap to remove it too." }
}

if (Find-Leftovers) { exit 0 } else { exit 1 }
