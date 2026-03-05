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

## ✅ PROJECT COMPLETE — All 11 Stages Done

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
| 10 | Scripts + Polish | ✅ | fc4591b |

---

## Module Map (all wired in terraform/main.tf)

| Module Call | Directory | Key Outputs |
|------------|-----------|-------------|
| module.iam | ./modules/iam | 7 role ARNs ✅ |
| module.budget | ./modules/budget | (no outputs) ✅ |
| module.security_hub | ./modules/security-hub | (no outputs) ✅ |
| module.cloudwatch | ./modules/cloudwatch | log_group_name ✅ |
| module.sns | ./modules/sns | admin_alerts_topic_arn ✅ |
| module.lambda_remediation | ./modules/lambda-remediation | s3/iam/vpc/verification ARNs ✅ |
| module.lambda_ai_analyzer | ./modules/lambda-ai-analyzer | function_arn ✅ |
| module.lambda_notification | ./modules/lambda-notification | function_arn ✅ |
| module.lambda_approval | ./modules/lambda-approval | function_arn, function_name ✅ |
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
| SNS Topic | security-automation-admin-alerts |
| API Gateway | SecurityAutomationApprovalAPI |
| CW Log Group | /aws/security-automation |
| CW Dashboard | SecurityAutomation-LiveMonitor |
| Secrets Manager | security-automation/ai-api-key |
| IAM roles | SecurityAutomation-{StepFunctionsRole,LambdaRemediationRole,LambdaAIAnalyzerRole,LambdaApprovalRole,LambdaNotificationRole,LambdaVerificationRole,EventBridgeRole} |

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
- Approval handler: GET /approve?token=TOKEN&action=N, /reject?token=TOKEN, /manual?token=TOKEN
- Task token URL-encoded into approval links by send_notification.py
- Step Functions waitForTaskToken with HeartbeatSeconds=3600 (1-hour timeout)
- Simulation: standalone Terraform root in `terraform/simulation/` — `terraform -chdir=terraform/simulation apply`

---

## CRITICAL POST-DEPLOY STEPS (after first terraform apply)

1. **Confirm SNS subscription**: Check email and click "Confirm subscription" link
2. **Set AI API key**:
```powershell
aws secretsmanager put-secret-value `
  --secret-id security-automation/ai-api-key `
  --secret-string '{"api_key":"YOUR_GEMINI_KEY_HERE","provider":"gemini"}'
```
3. **Deploy simulation**: `.\scripts\demo.ps1`
4. **Verify**: Run `terraform plan` → should show 0 changes

---

## File Map (key files)

```
terraform/
  main.tf                          # Root wiring all 12 modules
  providers.tf                     # aws ~>5.0, random ~>3.5, archive ~>2.4
  variables.tf                     # admin_email (required), aws_region, ai_provider, ai_model
  modules/
    iam/main.tf                    # 7 IAM roles
    budget/main.tf                 # $1/mo budget alert
    security-hub/main.tf           # FSBP + CIS + Config recorder
    cloudwatch/main.tf             # Log group + dashboard + 2 alarms
    sns/main.tf                    # SNS topic + email subscription
    api-gateway/main.tf            # REST API /approve /reject /manual → approval Lambda
    lambda-remediation/src/        # s3_remediation.py, iam_remediation.py, vpc_remediation.py, verification.py, utils.py
    lambda-ai-analyzer/src/        # ai_analyzer.py, response_validator.py, infrastructure_context.py, providers/
    lambda-notification/src/       # send_notification.py
    lambda-approval/src/           # approval_handler.py
    step-functions/
      state-machine.asl.json       # Full ASL with templatefile placeholders
      main.tf                      # aws_sfn_state_machine + CW log group
    eventbridge/main.tf            # securityhub-finding-rule → Step Functions
  simulation/
    main.tf                        # 6 demo misconfigurations
    outputs.tf                     # bucket names, SG IDs for verification
scripts/
  deploy.ps1                       # Full stack deploy
  destroy.ps1                      # Full teardown
  demo.ps1                         # Deploy/destroy simulation resources
  pause-project.ps1                # Disable EventBridge (cost saving)
  resume-project.ps1               # Re-enable EventBridge
docs/
  architecture.md                  # System design + flow diagram
  manual-vs-auto-mttr.md          # MTTR analysis (88% reduction)
  demo-guide.md                    # Step-by-step demo instructions
  judge-qa.md                      # Evaluator Q&A preparation
  cost-log.md                      # Monthly cost breakdown (~$0.70)
tests/
  test_response_validator.py       # Safety override unit tests
README.md                          # Project overview + quick start
```
