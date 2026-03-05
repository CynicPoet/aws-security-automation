# deploy.ps1 — Full deployment of AWS Security Automation
# Run from repo root: .\scripts\deploy.ps1 -AdminEmail "you@example.com"

param(
    [Parameter(Mandatory = $true)]
    [string]$AdminEmail,

    [string]$Region = "us-east-1",
    [string]$AIProvider = "gemini",
    [string]$AIModel = "gemini-2.5-flash-preview-05-20"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$TF_DIR = "$PSScriptRoot\..\terraform"

Write-Host "`n=== AWS Security Automation — Deploy ===" -ForegroundColor Cyan

# 1. Validate Terraform format
Write-Host "`n[1/5] Checking Terraform format..." -ForegroundColor Yellow
terraform -chdir=$TF_DIR fmt -check -recursive
if ($LASTEXITCODE -ne 0) {
    Write-Host "Format issues found. Running terraform fmt..." -ForegroundColor Yellow
    terraform -chdir=$TF_DIR fmt -recursive
}

# 2. Init
Write-Host "`n[2/5] Initializing Terraform..." -ForegroundColor Yellow
terraform -chdir=$TF_DIR init

# 3. Validate
Write-Host "`n[3/5] Validating configuration..." -ForegroundColor Yellow
terraform -chdir=$TF_DIR validate

# 4. Plan
Write-Host "`n[4/5] Planning deployment..." -ForegroundColor Yellow
terraform -chdir=$TF_DIR plan `
    -var="admin_email=$AdminEmail" `
    -var="aws_region=$Region" `
    -var="ai_provider=$AIProvider" `
    -var="ai_model=$AIModel" `
    -out=tfplan

# 5. Apply
Write-Host "`n[5/5] Applying (this takes ~2-3 minutes)..." -ForegroundColor Yellow
terraform -chdir=$TF_DIR apply tfplan
Remove-Item "$TF_DIR\tfplan" -ErrorAction SilentlyContinue

Write-Host "`n=== Deployment Complete ===" -ForegroundColor Green
Write-Host @"

NEXT STEPS (manual, one-time):
  1. Check your email ($AdminEmail) and click "Confirm subscription" for SNS
  2. Set your AI API key in Secrets Manager:

     aws secretsmanager put-secret-value ``
       --secret-id security-automation/ai-api-key ``
       --secret-string '{\"api_key\":\"YOUR_KEY_HERE\",\"provider\":\"$AIProvider\"}'

  3. Deploy simulation resources (optional demo):
     .\scripts\demo.ps1 -AdminEmail $AdminEmail
"@
