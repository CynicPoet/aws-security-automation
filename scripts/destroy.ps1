# destroy.ps1 — Tear down all AWS Security Automation resources
# Run from repo root: .\scripts\destroy.ps1 -AdminEmail "you@example.com"

param(
    [Parameter(Mandatory = $true)]
    [string]$AdminEmail,

    [string]$Region = "us-east-1"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$TF_DIR = "$PSScriptRoot\..\terraform"

Write-Host "`n=== AWS Security Automation — Destroy ===" -ForegroundColor Red
Write-Host "WARNING: This will delete ALL project resources including Lambda, Step Functions," -ForegroundColor Red
Write-Host "         IAM roles, SNS topic, API Gateway, and CloudWatch resources." -ForegroundColor Red

$confirm = Read-Host "`nType 'yes' to confirm destruction"
if ($confirm -ne "yes") {
    Write-Host "Aborted." -ForegroundColor Yellow
    exit 0
}

# Destroy simulation first if it exists
$SIM_DIR = "$PSScriptRoot\..\terraform\simulation"
if (Test-Path "$SIM_DIR\terraform.tfstate") {
    Write-Host "`n[1/2] Destroying simulation resources..." -ForegroundColor Yellow
    terraform -chdir=$SIM_DIR destroy -auto-approve
}

# Destroy main stack
Write-Host "`n[2/2] Destroying main stack..." -ForegroundColor Yellow
terraform -chdir=$TF_DIR destroy `
    -var="admin_email=$AdminEmail" `
    -var="aws_region=$Region" `
    -auto-approve

Write-Host "`n=== Destruction Complete ===" -ForegroundColor Green
Write-Host "All resources have been removed from AWS." -ForegroundColor Green
