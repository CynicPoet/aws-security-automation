# pause-project.ps1 — Pause the project to minimize AWS costs
# Disables EventBridge rule so no new executions start.
# Resources remain deployed; re-enable with resume-project.ps1

param(
    [string]$Region = "us-east-1"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "`n=== Pausing Security Automation ===" -ForegroundColor Yellow
Write-Host "Disabling EventBridge rule to stop new executions..." -ForegroundColor Yellow

aws events disable-rule --name securityhub-finding-rule --region $Region

Write-Host "`n[OK] EventBridge rule disabled." -ForegroundColor Green
Write-Host "     Lambda, Step Functions, SNS, and API Gateway remain deployed." -ForegroundColor Gray
Write-Host "     No new executions will start until you run resume-project.ps1" -ForegroundColor Gray

# Estimated cost while paused
Write-Host @"

Estimated cost while PAUSED:
  - Secrets Manager: ~`$0.40/mo
  - CloudWatch log retention: ~`$0.10/mo
  - Security Hub: ~`$0.10/mo
  - All compute (Lambda, Step Functions, API GW): `$0.00 (no invocations)
  Total: ~`$0.60/mo
"@
