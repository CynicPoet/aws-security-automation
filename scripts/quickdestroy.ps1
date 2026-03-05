# quickdestroy.ps1 — One-click teardown for AWS Security Automation
# Usage: .\scripts\quickdestroy.ps1
# Credentials live in scripts\config.ps1 (gitignored)

$ErrorActionPreference = "Stop"
$SCRIPTS_DIR = $PSScriptRoot
$TF_DIR      = "$SCRIPTS_DIR\..\terraform"

$CONFIG = "$SCRIPTS_DIR\config.ps1"
if (-not (Test-Path $CONFIG)) {
    Write-Host "ERROR: scripts\config.ps1 not found." -ForegroundColor Red; exit 1
}
. $CONFIG

$env:AWS_ACCESS_KEY_ID     = $AWS_ACCESS_KEY_ID
$env:AWS_SECRET_ACCESS_KEY = $AWS_SECRET_ACCESS_KEY
$env:AWS_DEFAULT_REGION    = $AWS_REGION

# State machine ARN follows fixed naming — derive from account
$ACCOUNT_ID = (py -3 -c "
import boto3
sts = boto3.client('sts', region_name='$AWS_REGION',
    aws_access_key_id='$AWS_ACCESS_KEY_ID',
    aws_secret_access_key='$AWS_SECRET_ACCESS_KEY')
print(sts.get_caller_identity()['Account'])
" 2>$null)
$SM_ARN = "arn:aws:states:${AWS_REGION}:${ACCOUNT_ID}:stateMachine:SecurityRemediationStateMachine"

Write-Host "`n========================================" -ForegroundColor Red
Write-Host "  AWS Security Automation — Quick Destroy" -ForegroundColor Red
Write-Host "========================================" -ForegroundColor Red
Write-Host ""
$confirm = Read-Host "This will DELETE all AWS resources. Type 'yes' to continue"
if ($confirm -ne "yes") { Write-Host "Aborted." -ForegroundColor Yellow; exit 0 }

# Stop running Step Functions executions (avoids 5-minute delete timeout)
Write-Host "`n[1/2] Stopping running Step Functions executions..." -ForegroundColor Yellow
py -3 -c @"
import boto3
sfn = boto3.client('stepfunctions', region_name='$AWS_REGION',
    aws_access_key_id='$AWS_ACCESS_KEY_ID',
    aws_secret_access_key='$AWS_SECRET_ACCESS_KEY')
try:
    pager = sfn.get_paginator('list_executions')
    n = 0
    for page in pager.paginate(stateMachineArn='$SM_ARN', statusFilter='RUNNING'):
        for ex in page['executions']:
            try:
                sfn.stop_execution(executionArn=ex['executionArn'], cause='quickdestroy')
                n += 1
            except: pass
    print(f'Stopped {n} execution(s)')
except Exception as e:
    print(f'(skip — {e})')
"@ 2>&1

# Destroy
Write-Host "`n[2/2] Destroying all infrastructure..." -ForegroundColor Yellow
Push-Location $TF_DIR
try {
    terraform destroy `
        -var="admin_email=$ADMIN_EMAIL" `
        -var="aws_region=$AWS_REGION" `
        -auto-approve
    if ($LASTEXITCODE -ne 0) { Write-Host "Destroy had errors — check tfstate manually." -ForegroundColor Red; exit 1 }
} finally {
    Pop-Location
}

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  All resources destroyed. Zero cost." -ForegroundColor Green
Write-Host "  Re-deploy: .\scripts\quickdeploy.ps1" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Green
