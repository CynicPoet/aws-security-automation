# demo.ps1 — Deploy simulation resources and watch the automation run
# Run from repo root: .\scripts\demo.ps1

param(
    [string]$Region = "us-east-1",
    [switch]$Destroy
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$SIM_DIR = "$PSScriptRoot\..\terraform\simulation"

if ($Destroy) {
    Write-Host "`n=== Removing Simulation Resources ===" -ForegroundColor Yellow
    terraform -chdir=$SIM_DIR destroy -auto-approve
    Write-Host "Simulation resources removed." -ForegroundColor Green
    exit 0
}

Write-Host "`n=== Security Automation Demo ===" -ForegroundColor Cyan
Write-Host "Creating intentionally misconfigured resources..." -ForegroundColor Yellow

# Init if needed
if (-not (Test-Path "$SIM_DIR\.terraform")) {
    terraform -chdir=$SIM_DIR init
}

terraform -chdir=$SIM_DIR apply -auto-approve

Write-Host "`n=== Simulation Resources Created ===" -ForegroundColor Green
Write-Host @"

Resources deployed:
  [CAT-A] S3 bucket with public-read ACL      → Expect: AUTO-REMEDIATED in ~20s
  [CAT-A] Security group: SSH open to 0.0.0.0/0 → Expect: AUTO-REMEDIATED in ~20s
  [CAT-A] Security group: ALL traffic open     → Expect: AUTO-REMEDIATED in ~20s
  [CAT-B] IAM user + admin key (Role=CI-Pipeline) → Expect: APPROVAL EMAIL sent
  [CAT-B] Security group: RDP open (Production) → Expect: APPROVAL EMAIL sent
  [FALSE+] S3 bucket tagged PublicAccess=Intentional → Expect: SUPPRESSED, no action

Watch it work:
  - AWS Console → Step Functions → SecurityRemediationStateMachine → Executions
  - CloudWatch → Log Insights → /aws/security-automation
  - Check email for admin approval requests (Category B)

To reset demo (destroy + recreate):
  .\scripts\demo.ps1 -Destroy
  .\scripts\demo.ps1

"@
