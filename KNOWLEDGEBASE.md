# Security Automation — Knowledge Base

## Stage 0 — Repository & Local Setup — COMPLETED ✅
**Date:** 2026-03-05
**Resources:** Local only — no AWS resources created
**Terraform files:**
- `terraform/providers.tf` — AWS + random providers, default tags
- `terraform/variables.tf` — All root variables with validation
- `terraform/main.tf` — Root module wiring all child modules
- `terraform/outputs.tf` — Key output values
- `terraform/backend.tf` — Local backend (tfstate)
- `terraform/terraform.tfvars.example` — Template for secrets
- All 12 module stubs (variables.tf + main.tf + outputs.tf)
- `terraform/simulation/` stub
- `.github/workflows/terraform-validate.yml`

**Infra state:** No AWS resources deployed yet
**Decisions:**
- Local backend for now; S3 backend can be added later
- All variables have validation blocks
- `admin_email` is required (no default — must be set in tfvars)
- `lambda-remediation` module handles all 4 fns: s3, iam, vpc, verification

**Issues:** VS Code shows "No declaration found" errors after creating new files — Terraform Language Server cache not refreshing. Fix: `Ctrl+Shift+P` → `Terraform: Restart Language Server`. `terraform validate` confirms code is actually valid.

---

## Stage 1 — IAM Roles & Budget Alert — COMPLETED ✅
**Date:** 2026-03-05
**Git hash:** dc1a945
**Terraform files:**
- `terraform/modules/iam/main.tf` — 7 IAM roles + inline policies
- `terraform/modules/iam/outputs.tf` — 7 role ARN outputs
- `terraform/modules/budget/main.tf` — Monthly cost budget with 2 notifications

**IAM Roles created:**
| Role Name | Purpose |
|-----------|---------|
| SecurityAutomation-LambdaRemediationRole | S3/IAM/VPC remediation Lambdas |
| SecurityAutomation-LambdaVerificationRole | Post-remediation verification Lambda |
| SecurityAutomation-LambdaAIAnalyzerRole | AI context gathering + Secrets Manager |
| SecurityAutomation-LambdaNotificationRole | SNS publish for admin alerts |
| SecurityAutomation-LambdaApprovalRole | Step Functions callback (SendTaskSuccess) |
| SecurityAutomation-StepFunctionsRole | Invoke all security-auto-* Lambdas |
| SecurityAutomation-EventBridgeRole | Start SecurityRemediationStateMachine |

**Budget:** `security-auto-monthly-budget` — alerts at 80% actual + 100% forecasted to admin_email

**Decisions:**
- All IAM policies are inline (not managed) for simplicity and auditability
- Least-privilege: each role scoped to minimum required permissions
- Lambda log permissions scoped to `/aws/security-automation` log group only
- AI Analyzer Secrets Manager permission scoped to `security-automation/ai-api-key*` ARN
- Step Functions Lambda invoke scoped to `security-auto-*` function name prefix

**Validation:** `terraform validate` ✅

---

## Stage 2 — Security Hub + AWS Config — COMPLETED ✅
**Date:** 2026-03-05
**Terraform files:**
- `terraform/modules/security-hub/main.tf` — Security Hub + Config recorder + delivery

**AWS Resources defined:**
| Resource | Name/Value |
|----------|-----------|
| Security Hub | Enabled on account |
| CIS Benchmark | v1.4.0 standard subscription |
| FSBP | AWS Foundational Security Best Practices v1.0.0 |
| Config S3 Bucket | `security-auto-config-logs-{account_id}` |
| Config IAM Role | `SecurityAutomation-AWSConfigRole` |
| Config Recorder | `security-auto-recorder` — all resources + global |
| Delivery Channel | `security-auto-delivery-channel` → S3 bucket |

**Decisions:**
- S3 bucket for Config logs: public access blocked, AES256 encrypted, `force_destroy=true` for easy teardown
- Bucket policy scoped with `AWS:SourceAccount` condition (prevents confused deputy)
- Config recorder: `all_supported = true` + `include_global_resource_types = true`
- Separate IAM role for Config (attached AWS managed `AWS_ConfigRole` + inline S3 policy)

**Validation:** `terraform validate` ✅

---

## CONTINUATION GUIDE (if chat resets)
1. Read `Project_prompt.txt` at `c:\Storage\Projects\Cloud_automation\Project_prompt.txt`
2. Working dir: `c:\Storage\Projects\Cloud_automation\aws-security-automation\`
3. GitHub repo: `https://github.com/CynicPoet/aws-security-automation`
4. Current stage: Starting **Stage 3 — CloudWatch Log Group + Dashboard**
5. Run `terraform validate` in `terraform/` — should say "Success"
6. All VS Code "No declaration found" errors = Language Server cache, not real — ignore or restart LS
