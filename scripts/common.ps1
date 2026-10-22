# Shared by deploy.ps1 and destroy.ps1. Dot-source it; do not run it alone.
#
# Works in Windows PowerShell 5.1 and PowerShell 7.

$ErrorActionPreference = "Stop"
$env:AWS_PAGER = ""

$RepoRoot = Split-Path -Parent $PSScriptRoot
$InfraRoot = Join-Path $RepoRoot "infra"

function Invoke-Native {
    # Runs an external program and stops the script if it fails. PowerShell
    # does not stop on a failed program by itself, only on its own errors.
    #
    # Output goes straight to the screen. Otherwise it would become part of
    # the return value of whichever function called this. -Interactive
    # leaves the console alone, so a prompt such as Terraform's "Enter a
    # value:" shows before it waits for an answer.
    param(
        [Parameter(Mandatory)][string]$File,
        [string[]]$Arguments = @(),
        [switch]$Interactive
    )
    if ($Interactive) { & $File @Arguments } else { & $File @Arguments | Out-Host }
    if ($LASTEXITCODE -ne 0) {
        throw "$File $($Arguments -join ' ') failed with exit code $LASTEXITCODE"
    }
}

function Assert-Tools {
    foreach ($tool in @("aws", "terraform")) {
        if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
            throw "$tool is not installed or not on PATH."
        }
    }
}

function Use-AwsLogin {
    # Terraform cannot read the credentials `aws login` caches. The AWS CLI
    # can hand them over as plain environment variables, which every tool
    # understands. They are short-lived (an hour at most) and live only in
    # this PowerShell session.
    param([Parameter(Mandatory)][string]$AwsProfile)

    # Windows PowerShell 5.1 turns a program's error output into a
    # script-stopping error when it is captured, so relax that here.
    $ErrorActionPreference = "Continue"
    $exported = & aws configure export-credentials --profile $AwsProfile --format powershell 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "No usable credentials for profile '$AwsProfile'. Run: aws login --profile $AwsProfile"
    }
    $exported | Out-String | Invoke-Expression
    # With keys in the environment, a profile name would only compete with them.
    Remove-Item Env:AWS_PROFILE -ErrorAction SilentlyContinue

    $identity = & aws sts get-caller-identity --output json | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { throw "The exported credentials were refused by AWS." }
    return $identity
}

function Get-StateAddresses {
    # The resources Terraform has recorded in a folder's state, one per line.
    param([Parameter(Mandatory)][string]$Directory)
    $ErrorActionPreference = "Continue"
    $addresses = & terraform "-chdir=$Directory" state list 2>$null
    if ($LASTEXITCODE -ne 0) { return @() }
    return @($addresses | Where-Object { $_ })
}

function Assert-LambdaBuild {
    # Terraform zips build/scanner and build/api, and reads them even when
    # destroying. Build them if they are missing.
    $scanner = Join-Path (Join-Path $RepoRoot "build") "scanner"
    $api = Join-Path (Join-Path $RepoRoot "build") "api"
    if (-not ((Test-Path $scanner) -and (Test-Path $api))) {
        Write-Host "Building the Lambda packages..."
        Invoke-Native -File python -Arguments @((Join-Path $PSScriptRoot "build_lambdas.py"))
    }
}
