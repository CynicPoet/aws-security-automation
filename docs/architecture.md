# System Architecture

## Overview

This system implements a Security Orchestration, Automation, and Response (SOAR) pattern on AWS.
It detects security misconfigurations via AWS Security Hub, uses an AI model to triage and route
findings, and executes pre-written remediation playbooks — either automatically or after admin
approval, depending on severity and context.

---

## High-Level Flow

```
AWS Resources                    Security Hub
(S3, IAM, VPC)  ──findings──►  (FSBP / CIS rules)
                                      │
                              EventBridge Rule
                          (securityhub-finding-rule)
                                      │
                                      ▼
                            Step Functions
                        (SecurityRemediationStateMachine)
                                      │
                          ┌───────────┴───────────┐
                          │                       │
                    AI Analyzer              False Positive?
                  (Gemini 2.5 Flash)         ──► Suppress
                          │
              ┌───────────┴───────────┐
              │                       │
       Safe to auto?           Needs approval?
              │                       │
    ┌─────────┴──────┐       NotifyAdmin (SNS)
    │                │           + API GW
  S3 fix  IAM/VPC fix      (approve / reject)
    │                │              │
    └────────┬───────┘         Admin clicks
             │                 email link
       VerifyRemediation            │
             │              ExecutePlaybook
       UpdateSecurityHub           │
             │              VerifyRemediation
           DONE             UpdateSecurityHub
                                  DONE
```

---

## Components

### EventBridge Rule
- Name: `securityhub-finding-rule`
- Triggers on: Security Hub findings with `Compliance.Status=FAILED`, `Workflow.Status=NEW`,
  `Severity.Label` in [MEDIUM, HIGH, CRITICAL], `RecordState=ACTIVE`
- Target: `SecurityRemediationStateMachine`

### Step Functions (State Machine)
- Name: `SecurityRemediationStateMachine`
- Type: STANDARD (for full audit trail)
- States: ParseFinding → AIAnalysis → IsFalsePositive → IsSafeToAutoRemediate →
  DetermineResourceType → Remediate → VerifyRemediation → UpdateSecurityHub
- Admin approval path uses `waitForTaskToken` with 1-hour heartbeat timeout

### AI Analyzer Lambda
- Name: `security-auto-ai-analyzer`
- Uses Gemini 2.5 Flash (configurable; Claude also supported)
- Called via `urllib.request` REST — no SDK dependencies
- Returns structured JSON: `risk_level`, `is_false_positive`, `safe_to_auto_remediate`,
  `recommended_playbook`, `recommended_actions`
- Safety overrides in `response_validator.py` override AI decisions for critical cases

### Remediation Lambdas
| Lambda | Fixes |
|--------|-------|
| `security-auto-s3-remediation` | Blocks all 4 Public Access settings, sets ACL private |
| `security-auto-iam-remediation` | Deactivates access keys, attaches emergency deny policy |
| `security-auto-vpc-remediation` | Revokes open-world (0.0.0.0/0 / ::/0) ingress rules |
| `security-auto-verification` | Confirms fix applied correctly before marking resolved |

### Notification Lambda
- Sends rich email via SNS with AI analysis summary and 1-click approve/reject links
- Task token URL-encoded into API Gateway URLs

### Approval Lambda + API Gateway
- API: `SecurityAutomationApprovalAPI`
- Endpoints: `GET /approve?token=TOKEN&action=N`, `GET /reject?token=TOKEN`, `GET /manual?token=TOKEN`
- On click: resumes Step Functions execution via `SendTaskSuccess`

### Security Hub
- Standards: CIS AWS Foundations v1.4, AWS Foundational Security Best Practices v1.0
- Updated to `RESOLVED` workflow status after successful remediation

### CloudWatch
- Log group: `/aws/security-automation` (90-day retention)
- Dashboard: `SecurityAutomation-LiveMonitor`
- Alarms: Step Functions failures, Lambda error rate

---

## Safety Design

The system can never auto-remediate resources tagged:
- `AutoRemediationExclude=true` — explicit opt-out
- `Environment=Production` — always requires human approval
- Default security groups — never modified (AWS restriction + safety)
- `ServiceAccount=true` or `Role=CI-Pipeline` — IAM remediation always escalates
- `PublicAccess=Intentional` — S3 buckets used for static websites suppressed

On AI failure or unexpected response, the system defaults to HIGH risk,
`safe_to_auto_remediate=False` — forcing human review. AI cannot override safety rules.

---

## Cost (Monthly, ~$0.70)

| Service | Cost |
|---------|------|
| Secrets Manager (1 secret) | $0.40 |
| Security Hub | $0.10 |
| CloudWatch Logs | $0.10 |
| Lambda / Step Functions / API GW | ~$0.00–0.05 (pay-per-use) |
| SNS | ~$0.01 |
| **Total** | **~$0.61–0.70/mo** |
