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

**Issues:** VS Code shows "No declaration found" errors after creating new files — this is the Terraform Language Server cache not refreshing. Fix: `Ctrl+Shift+P` → `Terraform: Restart Language Server`. `terraform validate` confirms code is actually valid.

**Next:** Stage 2 — Security Hub + AWS Config

---

## Stage 1 — IAM Roles & Budget Alert — COMPLETED ✅
**Date:** 2026-03-05
**Resources:** No AWS resources deployed yet (deployed in Stage apply)
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
- Least-privilege: each role only gets what it needs
- Lambda log permissions scoped to `/aws/security-automation` log group only
- AI Analyzer Secrets Manager permission scoped to `security-automation/ai-api-key*` ARN
- Step Functions Lambda invoke scoped to `security-auto-*` function name prefix

**Validation:** `terraform init` ✅ | `terraform validate` ✅ (Success)

**Next:** Stage 2 — Security Hub + AWS Config

---

## CONTINUATION GUIDE (if chat resets)
1. Read `Project_prompt.txt` at `c:\Storage\Projects\Cloud_automation\Project_prompt.txt`
2. Working dir: `c:\Storage\Projects\Cloud_automation\aws-security-automation\`
3. Current stage: Starting **Stage 2 — Security Hub + AWS Config**
4. Run `terraform validate` in `terraform/` to confirm baseline is clean
5. GitHub repo: needs to be created — run in PowerShell:
   `gh auth login` then `gh repo create aws-security-automation --public --source=. --remote=origin --push`
6. All VS Code "No declaration found" errors = Language Server cache issue, not real errors
