# resume-project.ps1 — Resume the project after pausing
# Re-enables EventBridge rule so Security Hub findings trigger the workflow again.

param(
    [string]$Region = "us-east-1"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "`n=== Resuming Security Automation ===" -ForegroundColor Cyan
Write-Host "Re-enabling EventBridge rule..." -ForegroundColor Yellow

aws events enable-rule --name securityhub-finding-rule --region $Region

Write-Host "`n[OK] EventBridge rule enabled." -ForegroundColor Green
Write-Host "     Security Hub findings will now trigger the automation workflow." -ForegroundColor Gray
Write-Host "     Run .\scripts\demo.ps1 to create test findings." -ForegroundColor Gray
