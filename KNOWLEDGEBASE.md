# Security Automation — Knowledge Base

## Stage 0 — Repository & Local Setup — COMPLETED ✅
**Date:** 2026-03-05 | **Git hash:** 655d078
- Root Terraform files, all 12 module stubs, .gitignore, GitHub Actions CI

---

## Stage 1 — IAM Roles & Budget Alert — COMPLETED ✅
**Date:** 2026-03-05 | **Git hash:** dc1a945
- 7 least-privilege IAM roles (remediation, verification, AI, notification, approval, step functions, eventbridge)
- Monthly budget: 80% actual + 100% forecasted alerts

---

## Stage 2 — Security Hub + AWS Config — COMPLETED ✅
**Date:** 2026-03-05 | **Git hash:** e84f697
- Security Hub: CIS v1.4 + FSBP v1.0 standards
- Config: recorder (all resources), delivery → S3 bucket (AES256, access blocked)
- Config IAM role: AWS_ConfigRole managed + inline S3

---

## Stage 3 — CloudWatch — COMPLETED ✅
**Date:** 2026-03-05 | **Git hash:** c7d498f
- Log group: `/aws/security-automation` (90-day retention)
- Dashboard: `SecurityAutomation-LiveMonitor` (5 rows: SF executions, Lambda errors, duration, SH findings, log insights)
- Alarms: step-functions-failed (>=1), lambda-errors (>=3 aggregate)

---

## Stage 4 — Lambda Functions (7 total) — COMPLETED ✅
**Date:** 2026-03-05
**Files changed:**
- `terraform/providers.tf` — added hashicorp/archive ~> 2.4
- `terraform/modules/lambda-remediation/main.tf` — 4 Lambda functions + CW log groups
- `terraform/modules/lambda-remediation/outputs.tf` — real ARN outputs
- `terraform/modules/lambda-remediation/src/utils.py` — StructuredLogger, update_finding_workflow, ARN parsers
- `terraform/modules/lambda-remediation/src/s3_remediation.py`
- `terraform/modules/lambda-remediation/src/iam_remediation.py`
- `terraform/modules/lambda-remediation/src/vpc_remediation.py`
- `terraform/modules/lambda-remediation/src/verification.py`
- `terraform/modules/lambda-ai-analyzer/main.tf` — AI Lambda + Secrets Manager secret
- `terraform/modules/lambda-ai-analyzer/outputs.tf` — real ARN output
- `terraform/modules/lambda-ai-analyzer/src/ai_analyzer.py`
- `terraform/modules/lambda-ai-analyzer/src/infrastructure_context.py`
- `terraform/modules/lambda-ai-analyzer/src/response_validator.py`
- `terraform/modules/lambda-ai-analyzer/src/providers/__init__.py`
- `terraform/modules/lambda-ai-analyzer/src/providers/base_provider.py`
- `terraform/modules/lambda-ai-analyzer/src/providers/gemini_provider.py`
- `terraform/modules/lambda-ai-analyzer/src/providers/claude_provider.py`
- `terraform/modules/lambda-ai-analyzer/src/requirements.txt`
- `terraform/modules/lambda-notification/main.tf`
- `terraform/modules/lambda-notification/outputs.tf`
- `terraform/modules/lambda-notification/src/send_notification.py`
- `terraform/modules/lambda-approval/main.tf`
- `terraform/modules/lambda-approval/outputs.tf`
- `terraform/modules/lambda-approval/src/approval_handler.py`

**Lambda Functions:**
| Name | Handler | Timeout | Purpose |
|------|---------|---------|---------|
| security-auto-s3-remediation | s3_remediation.lambda_handler | 60s | Block S3 public access |
| security-auto-iam-remediation | iam_remediation.lambda_handler | 60s | Deactivate IAM keys + deny policy |
| security-auto-vpc-remediation | vpc_remediation.lambda_handler | 60s | Revoke 0.0.0.0/0 SG rules |
| security-auto-verification | verification.lambda_handler | 60s | Post-remediation check |
| security-auto-ai-analyzer | ai_analyzer.lambda_handler | 60s | Gemini/Claude analysis |
| security-auto-notification | send_notification.lambda_handler | 30s | SNS admin email |
| security-auto-approval-handler | approval_handler.lambda_handler | 10s | API GW callback → Step Functions |

**Key Design Decisions:**
- NO external Python packages — all HTTP to Gemini/Claude via stdlib `urllib.request`
  → no Lambda Layers, no pip install at deploy time, just `archive_file` data sources
- AI provider is swappable with 2 variable changes (ai_provider + ai_model in tfvars)
- Secrets Manager secret `security-automation/ai-api-key` created with placeholder value
  → after first `terraform apply`, update manually (see post-deploy step below)
- Hardcoded safety overrides in response_validator.py that AI CANNOT bypass:
  - AutoRemediationExclude=true tag → never auto-remediate
  - Environment=Production tag → always escalate to admin
  - Default VPC security group → never modify
  - ServiceAccount=true or Role=CI-Pipeline → always escalate
- Each remediation playbook: VALIDATE → SAFETY CHECK → LOG → EXECUTE → VERIFY → LOG
- All playbooks are idempotent (safe to run multiple times)

**CRITICAL POST-DEPLOY STEP (after Stage apply):**
Update the AI API key in Secrets Manager:
```powershell
aws secretsmanager put-secret-value `
  --secret-id security-automation/ai-api-key `
  --secret-string '{"api_key":"YOUR_GEMINI_KEY_HERE","provider":"gemini"}'
```

**Validation:** `terraform init -upgrade` ✅ | `terraform validate` ✅

---

## Stage 5 — SNS + API Gateway — NEXT

---

## CONTINUATION GUIDE (if chat resets)
1. Read `Project_prompt.txt` at `c:\Storage\Projects\Cloud_automation\Project_prompt.txt`
2. Working dir: `c:\Storage\Projects\Cloud_automation\aws-security-automation\`
3. GitHub repo: `https://github.com/CynicPoet/aws-security-automation`
4. Current stage: Starting **Stage 5 — SNS + API Gateway**
5. Run `terraform validate` in `terraform/` — must say "Success"
6. VS Code "No declaration found" errors = Terraform LS cache, not real errors
7. Archive provider is now included (hashicorp/archive ~> 2.4)
8. No Lambda Layers needed — all Python code uses stdlib + boto3 only
