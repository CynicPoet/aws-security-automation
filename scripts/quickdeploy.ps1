# quickdeploy.ps1 — One-click deploy for AWS Security Automation
# Usage: .\scripts\quickdeploy.ps1
# Credentials live in scripts\config.ps1 (gitignored)

$ErrorActionPreference = "Stop"
$SCRIPTS_DIR = $PSScriptRoot
$TF_DIR      = [System.IO.Path]::GetFullPath("$SCRIPTS_DIR\..\terraform")

# Load credentials from local config
$CONFIG = "$SCRIPTS_DIR\config.ps1"
if (-not (Test-Path $CONFIG)) {
    Write-Host "ERROR: scripts\config.ps1 not found. Copy from config.ps1.example and fill in your values." -ForegroundColor Red
    exit 1
}
. $CONFIG   # dot-source to import variables

# Apply to environment
$env:AWS_ACCESS_KEY_ID     = $AWS_ACCESS_KEY_ID
$env:AWS_SECRET_ACCESS_KEY = $AWS_SECRET_ACCESS_KEY
$env:AWS_DEFAULT_REGION    = $AWS_REGION

function Write-Step($n, $total, $msg) { Write-Host "`n[$n/$total] $msg" -ForegroundColor Yellow }
function Write-OK($msg)               { Write-Host "  OK  $msg" -ForegroundColor Green }
function Write-Info($msg)             { Write-Host "  --  $msg" -ForegroundColor Cyan  }

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  AWS Security Automation - Quick Deploy" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# ── STEP 1: FORMAT ────────────────────────────────────────────────────────────
Write-Step 1 6 "Terraform format check..."
terraform -chdir="$TF_DIR" fmt -check -recursive 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    terraform -chdir="$TF_DIR" fmt -recursive | Out-Null
    Write-Info "Auto-formatted terraform files"
}
Write-OK "Format OK"

# ── STEP 2: VALIDATE ──────────────────────────────────────────────────────────
Write-Step 2 6 "Validating configuration..."
terraform -chdir="$TF_DIR" validate
if ($LASTEXITCODE -ne 0) { Write-Host "Validation failed." -ForegroundColor Red; exit 1 }
Write-OK "Configuration valid"

# ── STEP 3: APPLY ─────────────────────────────────────────────────────────────
Write-Step 3 6 "Deploying infrastructure (~2-3 minutes)..."
terraform -chdir="$TF_DIR" apply `
    -var="admin_email=$ADMIN_EMAIL" `
    -var="aws_region=$AWS_REGION" `
    -auto-approve
if ($LASTEXITCODE -ne 0) { Write-Host "Apply failed." -ForegroundColor Red; exit 1 }
Write-OK "Infrastructure deployed"

# ── STEP 4: GET URL ───────────────────────────────────────────────────────────
Write-Step 4 6 "Getting dashboard URL..."
$base_url     = terraform -chdir="$TF_DIR" output -raw api_gateway_base_url
$dashboard_url = "$base_url/dashboard"
Write-OK "Dashboard URL: $dashboard_url"

# ── STEP 5: SET GEMINI KEY ────────────────────────────────────────────────────
Write-Step 5 6 "Setting AI API key..."
if ($GEMINI_API_KEY -ne "") {
    # Write Python to a temp file to avoid all PowerShell/Python string escaping issues
    $env:_SA_GEMINI_KEY = $GEMINI_API_KEY
    $tmpPy = "$env:TEMP\sa_gemini.py"
    $pyContent = @'
import boto3, json, os
sm = boto3.client("secretsmanager")
sm.put_secret_value(
    SecretId="security-automation/ai-api-key",
    SecretString=json.dumps({"api_key": os.environ["_SA_GEMINI_KEY"], "provider": "gemini"})
)
print("Gemini key saved.")
'@
    $pyContent | Set-Content -Path $tmpPy -Encoding UTF8
    py -3 $tmpPy
    Remove-Item $tmpPy -ErrorAction SilentlyContinue
    if ($LASTEXITCODE -eq 0) { Write-OK "Gemini API key set" }
    else { Write-Info "Gemini key step had warnings - continuing" }
    $env:_SA_GEMINI_KEY = ""
} else {
    Write-Info "No Gemini key in config.ps1 - AI uses smart fallback routing (still works)"
}

# ── STEP 6: AUTO-TTL ──────────────────────────────────────────────────────────
Write-Step 6 6 "Auto-terminate timer (press Enter to skip)..."
Write-Host ""
Write-Host "  This creates a one-time EventBridge rule that auto-destroys all" -ForegroundColor Gray
Write-Host "  infrastructure after N hours (useful after demos to avoid billing)." -ForegroundColor Gray
Write-Host ""
$ttlInput = Read-Host "  Auto-terminate after how many hours? [0 = manual only, recommended: 4]"
if ($ttlInput -eq "") { $ttlInput = "0" }
$ttlHours = [int]$ttlInput

if ($ttlHours -gt 0) {
    $env:_SA_TTL_HOURS = "$ttlHours"
    $env:_SA_AWS_REGION = $AWS_REGION
    $env:_SA_AWS_KEY = $AWS_ACCESS_KEY_ID
    $env:_SA_AWS_SEC = $AWS_SECRET_ACCESS_KEY

    $tmpTtl = "$env:TEMP\sa_ttl.py"
    $ttlPy = @'
import boto3, json, os
from datetime import datetime, timezone, timedelta

REGION  = os.environ["_SA_AWS_REGION"]
KEY     = os.environ["_SA_AWS_KEY"]
SEC     = os.environ["_SA_AWS_SEC"]
TTL_H   = int(os.environ["_SA_TTL_HOURS"])

creds = dict(region_name=REGION, aws_access_key_id=KEY, aws_secret_access_key=SEC)

# Find dashboard Lambda
lam = boto3.client("lambda", **creds)
dashboard_fn = None
pager = lam.get_paginator("list_functions")
for page in pager.paginate():
    for fn in page["Functions"]:
        if "security-auto" in fn["FunctionName"] and "dashboard" in fn["FunctionName"]:
            dashboard_fn = fn["FunctionName"]
            break
    if dashboard_fn:
        break

if not dashboard_fn:
    print("ERROR: dashboard Lambda not found")
    exit(1)

fn_arn     = lam.get_function(FunctionName=dashboard_fn)["Configuration"]["FunctionArn"]
account_id = boto3.client("sts", **creds).get_caller_identity()["Account"]
rule_arn   = f"arn:aws:events:{REGION}:{account_id}:rule/security-auto-ttl"

# Grant EventBridge permission to invoke Lambda
try:
    lam.add_permission(
        FunctionName=dashboard_fn,
        StatementId="AllowEventBridgeTTL",
        Action="lambda:InvokeFunction",
        Principal="events.amazonaws.com",
        SourceArn=rule_arn,
    )
except lam.exceptions.ResourceConflictException:
    pass  # permission already exists

# Create one-time cron rule
fire_at     = datetime.now(timezone.utc) + timedelta(hours=TTL_H)
cron_expr   = f"cron({fire_at.minute} {fire_at.hour} {fire_at.day} {fire_at.month} ? {fire_at.year})"
eb          = boto3.client("events", **creds)
eb.put_rule(Name="security-auto-ttl", ScheduleExpression=cron_expr, State="ENABLED",
            Description=f"Auto-terminate security automation after {TTL_H}h")
eb.put_targets(Rule="security-auto-ttl", Targets=[{
    "Id": "terminate-dashboard",
    "Arn": fn_arn,
    "Input": json.dumps({"__terminate": True}),
}])

local_time = fire_at.strftime("%Y-%m-%d %H:%M UTC")
print(f"AUTO_TTL_SET:{local_time}")
'@
    $ttlPy | Set-Content -Path $tmpTtl -Encoding UTF8
    $ttlResult = py -3 $tmpTtl 2>&1
    Remove-Item $tmpTtl -ErrorAction SilentlyContinue

    $env:_SA_TTL_HOURS = ""
    $env:_SA_AWS_REGION = ""
    $env:_SA_AWS_KEY = ""
    $env:_SA_AWS_SEC = ""

    $ttlLine = $ttlResult | Where-Object { $_ -match "^AUTO_TTL_SET:" }
    if ($ttlLine) {
        $fireTime = $ttlLine -replace "^AUTO_TTL_SET:", ""
        Write-OK "Auto-terminate scheduled at $fireTime (+${ttlHours}h)"
    } else {
        Write-Host "  WARN  TTL setup had issues: $ttlResult" -ForegroundColor Yellow
        Write-Info "Infrastructure will NOT auto-terminate — destroy manually when done"
    }
} else {
    Write-Info "Skipped — remember to run quickdestroy.ps1 or use the dashboard Terminate button when done"
}

# ── DONE ──────────────────────────────────────────────────────────────────────
Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  DEPLOYMENT COMPLETE" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Dashboard:" -ForegroundColor White
Write-Host "  $dashboard_url" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Checklist:" -ForegroundColor White
Write-Host "    1. Check $ADMIN_EMAIL -> click 'Confirm subscription'" -ForegroundColor Gray
Write-Host "    2. Open dashboard URL above" -ForegroundColor Gray
Write-Host "    3. Pipeline is DISABLED by default - click 'Start Pipeline' for real mode" -ForegroundColor Gray
Write-Host "    4. Use Simulation Lab to demo (Category A=auto-fix, B=admin approval)" -ForegroundColor Gray
if ($ttlHours -gt 0) {
    Write-Host "    5. Infrastructure auto-terminates at $fireTime" -ForegroundColor Yellow
} else {
    Write-Host "    5. Run .\scripts\quickdestroy.ps1 or use Terminate button when done" -ForegroundColor Gray
}
Write-Host ""

try { Start-Process $dashboard_url } catch {}
