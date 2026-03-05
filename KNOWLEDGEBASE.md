# Security Automation — Knowledge Base

## CONTINUATION GUIDE (read this first on new chat)
1. Prompt: `c:\Storage\Projects\Cloud_automation\Project_prompt.txt`
2. Repo: `c:\Storage\Projects\Cloud_automation\aws-security-automation\`
3. GitHub: `https://github.com/CynicPoet/aws-security-automation`
4. Run `terraform validate` in `terraform/` first — must say "Success"
5. VS Code errors = Terraform LS cache issue, not real. Fix: Ctrl+Shift+P → Terraform: Restart Language Server
6. NO Lambda Layers needed — all Python uses stdlib + boto3 only (Gemini/Claude via urllib.request)
7. Archive provider: hashicorp/archive ~> 2.4 (already in providers.tf)
8. CI GitHub Actions runs `terraform fmt -check -recursive` — always run `terraform fmt -recursive` before committing
9. Infrastructure is CURRENTLY DESTROYED — run `terraform apply` to redeploy

---

## ✅ PROJECT COMPLETE — All Issues Fixed
**Latest git hash: 049247c**

## One-Click Deploy/Destroy
- **Deploy**: `.\scripts\quickdeploy.ps1` — applies terraform, sets Gemini key, opens dashboard URL
- **Destroy**: `.\scripts\quickdestroy.ps1` — stops SFN executions, tears down all resources
- **Config**: copy `scripts\config.ps1.example` → `scripts\config.ps1` and fill in credentials (gitignored)

---

## Stage Summary

| Stage | Name | Status | Git Hash |
|-------|------|--------|----------|
| 0 | Scaffold | ✅ | 655d078 |
| 1 | IAM + Budget | ✅ | dc1a945 |
| 2 | Security Hub + Config | ✅ | e84f697 |
| 3 | CloudWatch | ✅ | c7d498f |
| 4 | Lambda (7 functions) | ✅ | adedb14 |
| 5 | SNS + API Gateway | ✅ | 48c6472 |
| 6 | Step Functions | ✅ | 95fa43f |
| 7 | EventBridge | ✅ | 95fa43f |
| 8 | Simulation Module | ✅ | 95fa43f |
| 9 | MTTR Docs | ✅ | fc4591b |
| 10 | Dashboard Redesign | ✅ | cb815f1 |
| 11 | Bug Fixes + Simulation Lab | ✅ | 322cdff |

---

## Module Map (all wired in terraform/main.tf)

| Module Call | Directory | Key Outputs |
|------------|-----------|-------------|
| module.iam | ./modules/iam | 7 role ARNs ✅ |
| module.budget | ./modules/budget | (no outputs) ✅ |
| module.security_hub | ./modules/security-hub | (no outputs) ✅ |
| module.cloudwatch | ./modules/cloudwatch | log_group_name ✅ |
| module.sns | ./modules/sns | admin_alerts_topic_arn ✅ |
| module.dynamodb | ./modules/dynamodb | findings_table_name, settings_table_name ✅ |
| module.lambda_remediation | ./modules/lambda-remediation | s3/iam/vpc/verification ARNs ✅ |
| module.lambda_ai_analyzer | ./modules/lambda-ai-analyzer | function_arn ✅ |
| module.lambda_notification | ./modules/lambda-notification | function_arn ✅ |
| module.lambda_approval | ./modules/lambda-approval | function_arn, function_name ✅ |
| module.lambda_dashboard | ./modules/lambda-dashboard | function_arn, function_name ✅ |
| module.api_gateway | ./modules/api-gateway | base_url ✅ |
| module.step_functions | ./modules/step-functions | state_machine_arn ✅ |
| module.eventbridge | ./modules/eventbridge | (no outputs) ✅ |

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
| Lambda Dashboard | security-auto-dashboard |
| SNS Topic | security-automation-admin-alerts |
| API Gateway | SecurityAutomationApprovalAPI |
| CW Log Group | /aws/security-automation |
| DynamoDB Findings | security-automation-findings |
| DynamoDB Settings | security-automation-settings |
| IAM roles | SecurityAutomation-{StepFunctionsRole,LambdaRemediationRole,LambdaAIAnalyzerRole,LambdaApprovalRole,LambdaNotificationRole,LambdaVerificationRole,EventBridgeRole,LambdaDashboardRole} |

---

## Key Design Decisions

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
- **Dashboard action buttons**: POST to `/dashboard/api/action` with `finding_id` in JSON body
  - NOT path params — ARNs contain slashes that break API Gateway routing
- **Step Functions task token**: Stored in DynamoDB `findings` table. Dashboard reads it and calls `sfn.send_task_success()`
- **Auto-remediated findings**: Each remediation Lambda (s3/iam/vpc) writes to DynamoDB at start with `AUTO_REMEDIATED` status
- **Verification Lambda**: Updates DynamoDB to `RESOLVED` after confirming fix
- **Pipeline shutdown**: Dashboard calls `events.disable_rule()` on `securityhub-finding-rule`
- **Simulation Lab**: Dashboard creates real AWS resources via boto3, starts Step Functions directly
  - No static simulation module needed — all on-demand from dashboard
- **Gemini model fallback chain**: gemini-2.0-flash → gemini-2.0-flash-lite → gemini-1.5-flash
  - Handles 429/RESOURCE_EXHAUSTED automatically
  - Max output tokens: 600 (was 1024) — sufficient for JSON response
  - Prompt optimized for token efficiency (~40% reduction)
- **Circular dependency fix**: `state_machine_arn` and `sns_topic_arn` computed as `locals` in root main.tf
  - Avoids cycle: lambda_dashboard → step_functions → lambda_notification → api_gateway → lambda_dashboard

---

## Dashboard Routes (API Gateway → lambda-dashboard)

| Method | Path | Function |
|--------|------|----------|
| GET | /dashboard | HTML page |
| GET | /dashboard/api/findings | List all findings |
| GET | /dashboard/api/settings | Get email toggle state |
| PUT | /dashboard/api/settings | Update email toggle |
| GET | /dashboard/api/control | Get pipeline status (ENABLED/DISABLED) |
| POST | /dashboard/api/action | Approve/reject/manual (finding_id in body) |
| POST | /dashboard/api/email | Resend email for a finding |
| POST | /dashboard/api/simulate | Create misconfiguration + start Step Functions |
| DELETE | /dashboard/api/simulate | Clean up simulation resource |
| POST | /dashboard/api/control | Shutdown/start pipeline |

---

## Simulation Lab Cases

| ID | Label | Severity | Category | AWS Resource Created |
|----|-------|----------|----------|---------------------|
| A1 | S3 Public Access | HIGH | Auto-remediated | S3 bucket with public access disabled |
| A2 | SSH Open to World | HIGH | Auto-remediated | Security group port 22 open |
| A3 | All Traffic Open | CRITICAL | Auto-remediated | Security group all ports open |
| B1 | IAM CI-Pipeline User | HIGH | Admin approval | IAM user tagged Role=CI-Pipeline |
| B2 | Production RDP Open | CRITICAL | Admin approval | SG tagged Environment=Production |

---

## Gemini API Token Limits (Free Tier)

| Model | RPM | TPM | TPD |
|-------|-----|-----|-----|
| gemini-2.0-flash | 15 | 1M | 1.5B |
| gemini-2.0-flash-lite | 30 | 1M | — |
| gemini-1.5-flash | 15 | 1M | 50K req/day |

Fallback chain in `gemini_provider.py` handles 429 errors automatically.

---

## CRITICAL POST-DEPLOY STEPS (after terraform apply)

1. **Confirm SNS subscription**: Check email and click "Confirm subscription" link
2. **Set AI API key**:
```powershell
aws secretsmanager put-secret-value `
  --secret-id security-automation/ai-api-key `
  --secret-string '{"api_key":"YOUR_GEMINI_KEY_HERE","provider":"gemini"}'
```
3. **Dashboard URL**: `https://f6bntx7jg3.execute-api.us-east-1.amazonaws.com/prod/dashboard`
4. **Verify**: Run `terraform plan` → should show 0 changes

---

## File Map (key files)

```
terraform/
  main.tf                          # Root wiring all 14 modules + locals for ARNs
  providers.tf                     # aws ~>5.0, random ~>3.5, archive ~>2.4
  variables.tf                     # admin_email (required), aws_region, ai_provider, ai_model
  modules/
    iam/main.tf                    # 8 IAM roles (includes LambdaDashboardRole with simulation perms)
    budget/main.tf                 # Monthly budget alert
    security-hub/main.tf           # FSBP + CIS + Config recorder
    cloudwatch/main.tf             # Log group + dashboard + 2 alarms
    sns/main.tf                    # SNS topic + email subscription
    dynamodb/main.tf               # findings table + settings table (email_notifications)
    api-gateway/main.tf            # REST API /approve /reject /manual /dashboard/{proxy+}
    lambda-remediation/src/        # s3_remediation.py, iam_remediation.py, vpc_remediation.py
                                   # verification.py, utils.py (write_finding_status added)
    lambda-ai-analyzer/src/        # ai_analyzer.py, response_validator.py, infrastructure_context.py
                                   # providers/gemini_provider.py (fallback chain, token optimization)
    lambda-notification/src/       # send_notification.py (DynamoDB write + conditional email)
    lambda-approval/src/           # approval_handler.py (email link handler)
    lambda-dashboard/src/          # dashboard_handler.py, dashboard_html.py
    step-functions/
      state-machine.asl.json       # Full ASL: ParseFinding→AI→Remediate/Escalate→Verify
      main.tf
    eventbridge/main.tf            # securityhub-finding-rule → Step Functions
scripts/
  deploy.ps1 / destroy.ps1 / demo.ps1 / pause-project.ps1 / resume-project.ps1
```

---

## DynamoDB Tables

### security-automation-findings
PK: `finding_id` (String)
Fields: resource_type, resource_id, severity, title, description, ai_analysis (JSON string),
        recommended_actions (JSON string), risk_level, status, task_token (if PENDING_APPROVAL),
        created_at, updated_at, ttl_epoch (30-day auto-expire), environment, action_taken

Status values: PENDING_APPROVAL | AUTO_REMEDIATED | RESOLVED | APPROVED | REJECTED |
               MANUAL_REVIEW | SUPPRESSED | FALSE_POSITIVE | FAILED

### security-automation-settings
PK: `setting_key` (String)
Pre-seeded: `{setting_key: "email_notifications", value: "false"}`
