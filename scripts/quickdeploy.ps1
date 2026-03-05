# quickdeploy.ps1 — One-click deploy for AWS Security Automation
# Usage: .\scripts\quickdeploy.ps1
# Credentials live in scripts\config.ps1 (gitignored)

$ErrorActionPreference = "Stop"
$SCRIPTS_DIR = $PSScriptRoot
$TF_DIR      = "$SCRIPTS_DIR\..\terraform"

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
Write-Step 1 5 "Terraform format check..."
terraform -chdir=$TF_DIR fmt -check -recursive 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    terraform -chdir=$TF_DIR fmt -recursive | Out-Null
    Write-Info "Auto-formatted terraform files"
}
Write-OK "Format OK"

# ── STEP 2: VALIDATE ──────────────────────────────────────────────────────────
Write-Step 2 5 "Validating configuration..."
terraform -chdir=$TF_DIR validate
if ($LASTEXITCODE -ne 0) { Write-Host "Validation failed." -ForegroundColor Red; exit 1 }
Write-OK "Configuration valid"

# ── STEP 3: APPLY ─────────────────────────────────────────────────────────────
Write-Step 3 5 "Deploying infrastructure (~2-3 minutes)..."
terraform -chdir=$TF_DIR apply `
    -var="admin_email=$ADMIN_EMAIL" `
    -var="aws_region=$AWS_REGION" `
    -auto-approve
if ($LASTEXITCODE -ne 0) { Write-Host "Apply failed." -ForegroundColor Red; exit 1 }
Write-OK "Infrastructure deployed"

# ── STEP 4: GET URL ───────────────────────────────────────────────────────────
Write-Step 4 5 "Getting dashboard URL..."
$base_url     = terraform -chdir=$TF_DIR output -raw api_gateway_base_url
$dashboard_url = "$base_url/dashboard"
Write-OK "Dashboard URL: $dashboard_url"

# ── STEP 5: SET GEMINI KEY ────────────────────────────────────────────────────
Write-Step 5 5 "Setting AI API key..."
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
Write-Host ""

try { Start-Process $dashboard_url } catch {}
