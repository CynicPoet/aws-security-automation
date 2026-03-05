# Security Automation — Knowledge Base

## CONTINUATION GUIDE (read this first on new chat)
1. Prompt: `c:\Storage\Projects\Cloud_automation\Project_prompt.txt`
2. Repo: `c:\Storage\Projects\Cloud_automation\aws-security-automation\`
3. GitHub: `https://github.com/CynicPoet/aws-security-automation`
4. Run `terraform validate` in `terraform/` first — must say "Success"
5. VS Code errors = Terraform LS cache issue, not real. Fix: Ctrl+Shift+P → Terraform: Restart Language Server
6. NO Lambda Layers needed — all Python uses stdlib + boto3 only (Gemini/Claude via urllib.request)
7. Archive provider: hashicorp/archive ~> 2.4 (already in providers.tf)

## Current Stage: Stage 5 — SNS + API Gateway (NEXT TO BUILD)

---

## Stage Summary

| Stage | Name | Status | Git Hash |
|-------|------|--------|----------|
| 0 | Scaffold | ✅ | 655d078 |
| 1 | IAM + Budget | ✅ | dc1a945 |
| 2 | Security Hub + Config | ✅ | e84f697 |
| 3 | CloudWatch | ✅ | c7d498f |
| 4 | Lambda (7 functions) | ✅ | adedb14 |
| 5 | SNS + API Gateway | 🔲 NEXT | — |
| 6 | Step Functions | 🔲 | — |
| 7 | EventBridge | 🔲 | — |
| 8 | Simulation Module | 🔲 | — |
| 9 | MTTR Docs | 🔲 | — |
| 10 | Scripts + Polish | 🔲 | — |

---

## Module Map (all wired in terraform/main.tf)

| Module Call | Directory | Key Outputs |
|------------|-----------|-------------|
| module.iam | ./modules/iam | 7 role ARNs ✅ |
| module.budget | ./modules/budget | (no outputs) ✅ |
| module.security_hub | ./modules/security-hub | (no outputs) ✅ |
| module.cloudwatch | ./modules/cloudwatch | log_group_name ✅ |
| module.sns | ./modules/sns | admin_alerts_topic_arn (stub "") |
| module.lambda_remediation | ./modules/lambda-remediation | s3/iam/vpc/verification ARNs ✅ |
| module.lambda_ai_analyzer | ./modules/lambda-ai-analyzer | function_arn ✅ |
| module.lambda_notification | ./modules/lambda-notification | function_arn ✅ |
| module.lambda_approval | ./modules/lambda-approval | function_arn, function_name ✅ |
| module.api_gateway | ./modules/api-gateway | base_url (stub "") |
| module.step_functions | ./modules/step-functions | state_machine_arn (stub "") |
| module.eventbridge | ./modules/eventbridge | (no outputs) |

---

## Naming Conventions (EXACT — do not change)

| Resource | Name |
|----------|------|
| State Machine | SecurityRemediationStateMachine |
| EventBridge Rule | securityhub-finding-rule |
| Lambda S3 fix | security-auto-s3-remediation |
| Lambda IAM fix | security-auto-iam-remediation |
| Lambda VPC fix | security-auto-vpc-remediation |
| Lambda AI | security-auto-ai-analyzer |
| Lambda Notify | security-auto-notification |
| Lambda Approval | security-auto-approval-handler |
| Lambda Verify | security-auto-verification |
| SNS Topic | security-automation-admin-alerts |
| API Gateway | SecurityAutomationApprovalAPI |
| CW Log Group | /aws/security-automation |
| CW Dashboard | SecurityAutomation-LiveMonitor |
| Secrets Manager | security-automation/ai-api-key |
| IAM roles | SecurityAutomation-{StepFunctionsRole,LambdaRemediationRole,LambdaAIAnalyzerRole,LambdaApprovalRole,LambdaNotificationRole,LambdaVerificationRole,EventBridgeRole} |

---

## Stage 4 Key Design Decisions (Lambda)

- Python source only: stdlib + boto3, NO external packages, NO Lambda Layers
- Gemini called via `urllib.request` REST POST to `generativelanguage.googleapis.com`
- Claude called via `urllib.request` REST POST to `api.anthropic.com`
- Secrets Manager: `security-automation/ai-api-key` — value = `{"api_key":"KEY","provider":"gemini"}`
  - `ignore_changes = [secret_string]` so Terraform won't overwrite user-set key
- Safety overrides in `response_validator.py` (AI CANNOT bypass):
  - AutoRemediationExclude=true → never auto-remediate
  - Environment=Production → always escalate
  - default SG → never modify
  - ServiceAccount=true / Role=CI-Pipeline → always escalate
- All playbooks: VALIDATE → SAFETY CHECK → LOG → EXECUTE → VERIFY → LOG (idempotent)
- Approval handler: GET /approve?token=TOKEN&action=N, /reject?token=TOKEN, /manual?token=TOKEN
- Task token URL-encoded into approval links by send_notification.py

---

## Stage 5 — What to Build

### SNS Module (`terraform/modules/sns/main.tf`)
- `aws_sns_topic` named `security-automation-admin-alerts`
- `aws_sns_topic_subscription` — email protocol, endpoint = var.admin_email
- Output: `admin_alerts_topic_arn`

### API Gateway Module (`terraform/modules/api-gateway/main.tf`)
- REST API named `SecurityAutomationApprovalAPI`
- Resources: `/approve` GET, `/reject` GET, `/manual` GET
- Integration: Lambda proxy to `security-auto-approval-handler`
- Stage: `prod`
- Lambda permission: allow API GW to invoke the approval Lambda
- Output: `base_url` = `https://{id}.execute-api.us-east-1.amazonaws.com/prod`

---

## Stage 6 — What to Build (Step Functions)

### State Machine ASL (`terraform/modules/step-functions/state-machine.asl.json`)
Flow:
1. ParseFinding → LogFindingReceived
2. AIAnalysis (Lambda: ai-analyzer)
3. Choice: is_false_positive? → SuppressFinding → END
4. Choice: safe_to_auto_remediate?
   - YES → DetermineResourceType → Choice(S3/IAM/VPC) → Remediate* → VerifyRemediation → UpdateSecurityHub → END
   - NO → NotifyAdmin → WaitForApproval (heartbeat callback, 1hr timeout)
     - APPROVED → ExecuteApprovedPlaybook → VerifyRemediation → UpdateSecurityHub → END
     - REJECTED → SuppressFinding → END
     - TIMEOUT → LogTimeout → NotifyAdminTimeout → END
5. Catch all errors → HandleError → END

### Step Functions Terraform (`terraform/modules/step-functions/main.tf`)
- `aws_sfn_state_machine` named `SecurityRemediationStateMachine`
- Type: STANDARD
- CW logging enabled (ALL level)
- Definition from `templatefile("state-machine.asl.json", {...lambda ARNs...})`

---

## Stage 7 — EventBridge Rule

File: `terraform/modules/eventbridge/main.tf`
- Rule: `securityhub-finding-rule`
- Event pattern:
```json
{
  "source": ["aws.securityhub"],
  "detail-type": ["Security Hub Findings - Imported"],
  "detail": {
    "findings": {
      "Compliance": {"Status": ["FAILED"]},
      "Workflow": {"Status": ["NEW"]},
      "Severity": {"Label": ["MEDIUM", "HIGH", "CRITICAL"]},
      "RecordState": ["ACTIVE"]
    }
  }
}
```
- Target: Step Functions state machine ARN
- Role: EventBridge IAM role

---

## Stage 8 — Simulation Module

File: `terraform/simulation/main.tf`
Resources (all tagged Environment=Test for Category A):
- A1: S3 bucket with public-read ACL (`secauto-test-public-{random4}`)
- A2: SG with SSH port 22 open to 0.0.0.0/0 (`secauto-test-open-ssh`)
- A3: SG with ALL traffic from 0.0.0.0/0 (`secauto-test-open-all`)
- B1: IAM user + active key + AdministratorAccess (`secauto-test-risky-user`, tagged Role=CI-Pipeline)
- B2: SG with RDP 3389 open, tagged Environment=Production (`secauto-test-open-rdp`)
- FP: S3 bucket with public-read ACL BUT tagged PublicAccess=Intentional,Purpose=StaticWebsite (`secauto-test-fp-website-{random4}`)

---

## CRITICAL POST-DEPLOY STEPS (after first terraform apply)

1. **Confirm SNS subscription**: Check email and click "Confirm subscription" link
2. **Set AI API key**:
```powershell
aws secretsmanager put-secret-value `
  --secret-id security-automation/ai-api-key `
  --secret-string '{"api_key":"YOUR_GEMINI_KEY_HERE","provider":"gemini"}'
```
3. **Verify**: Run `terraform plan` → should show 0 changes

