# System Architecture

## Overview

This system implements a Security Orchestration, Automation, and Response (SOAR) pattern on AWS.
It ingests security findings (via Simulation Lab for demos, or real AWS Security Hub in production),
uses an AI model to triage and route each finding, and executes pre-written remediation playbooks —
either automatically or after admin approval depending on risk level and resource context.

---

## Finding Ingestion: Demo vs Production

### Demo Mode (this deployment)

```
Dashboard Simulation Lab
  |-- creates real misconfigured AWS resource (S3 bucket, SG, IAM user)
  |-- injects Security Hub-shaped finding JSON
  v
Step Functions: SecurityRemediationStateMachine
  (EventBridge rule exists but is DISABLED by default)
```

### Production Mode

```
AWS Resources (S3, EC2, IAM, VPC)
  |-- state changes recorded by AWS Config
  v
Security Hub evaluates against CIS v1.4 / FSBP standards
  |-- generates finding on compliance failure
  v
EventBridge Rule: securityhub-finding-rule
  |-- filter: Compliance.Status=FAILED, Workflow.Status=NEW,
  |           Severity in [MEDIUM, HIGH, CRITICAL], RecordState=ACTIVE
  v
Step Functions: SecurityRemediationStateMachine
```

Both paths enter the same Step Functions pipeline from this point.

---

## Pipeline Flow

```
Step Functions: SecurityRemediationStateMachine
        |
        +-- ParseFinding
        |     extracts resource_type, resource_id, severity, tags
        |
        +-- AIAnalysis  (security-auto-ai-analyzer)
        |     calls Gemini or Claude with finding + live resource context
        |     returns: risk_level, is_false_positive, safe_to_auto_remediate,
        |              recommended_playbook, recommended_actions
        |     safety overrides applied (AI cannot bypass — see Safety Design)
        |
        +-- IsFalsePositive?
        |     yes → Suppress (no action, finding marked SUPPRESSED)
        |
        +-- IsSafeToAutoRemediate?
        |
        |   YES path (Category A — auto-remediate)
        |     |
        |     +-- DetermineResourceType → route to playbook Lambda
        |     |     AwsS3Bucket       → security-auto-s3-remediation
        |     |     AwsIamAccessKey   → security-auto-iam-remediation
        |     |     AwsEc2SecurityGroup → security-auto-vpc-remediation
        |     |
        |     +-- VerifyRemediation (security-auto-verification)
        |     +-- DynamoDB updated: RESOLVED
        |
        |   NO path (Category B — admin approval required)
        |     |
        |     +-- NotifyAdmin (security-auto-notification)
        |     |     stores task token in DynamoDB
        |     |     sends rich HTML email via SNS with:
        |     |       AI analysis summary, risk assessment,
        |     |       1-click Approve / Reject / Manual links
        |     |
        |     +-- waitForTaskToken (HeartbeatSeconds=3600)
        |     |
        |     +-- Admin clicks email link
        |     |     API Gateway → security-auto-approval-handler
        |     |     → sfn.send_task_success(taskToken, outcome)
        |     |
        |     +-- ExecuteApprovedPlaybook → VerifyRemediation
        |     +-- DynamoDB updated: APPROVED / REJECTED / MANUAL_REVIEW
```

---

## Components

### Dashboard (security-auto-dashboard)

The primary interface for the entire system — no AWS Console needed for normal operation.

**URL:** `https://{api-gateway-id}.execute-api.{region}.amazonaws.com/prod/dashboard`

Key capabilities:
- Real-time findings table with status, severity, AI analysis
- Finding detail modal: ARN, account ID, region, AI analysis breakdown, remediation steps
- Pipeline ON/OFF toggle (enables/disables EventBridge rule)
- AI toggle (enable/disable AI API calls — useful during development)
- AI provider hot-swap: switch between Gemini and Claude models with no redeploy
- Simulation Lab: create/destroy the 5 demo scenarios on demand
- Batch AI Remediation: force-remediate all pending findings with retry + failure context feedback
- Per-finding AI Runbook: Generate → Apply inline → Undo
- Terminate button: async self-destruct of all infrastructure from within Lambda

**API Routes:**

| Method | Path | Description |
|--------|------|-------------|
| GET | /dashboard | HTML page |
| GET | /dashboard/api/findings | List all findings |
| DELETE | /dashboard/api/findings | Clear all findings |
| GET/PUT | /dashboard/api/settings | Email notifications, auto-remediation, AI toggle |
| GET/POST | /dashboard/api/control | Pipeline status / shutdown / start / terminate |
| POST | /dashboard/api/action | Approve / reject / manual (finding_id in body) |
| POST | /dashboard/api/email | Resend approval email |
| POST/DELETE | /dashboard/api/simulate | Create simulation case / cleanup |
| GET/POST | /dashboard/api/remediate-all | Batch status / start batch remediation |
| GET/PUT | /dashboard/api/ai-config | Current AI provider+model / update config |
| POST | /dashboard/api/ai-models | Validate API key + return available models |
| POST | /dashboard/api/ai-runbook | Generate AI runbook for a finding |
| POST | /dashboard/api/apply-runbook | Execute inline remediation from runbook |
| POST | /dashboard/api/undo-runbook | Restore pre-remediation state |

---

### AI Analyzer (security-auto-ai-analyzer)

- Default provider: Gemini 2.0 Flash (overridable via dashboard — no redeploy)
- Fallback chain: gemini-2.0-flash → gemini-2.0-flash-lite → gemini-1.5-flash
- Also supports Claude: Haiku 4.5, Sonnet 4.6, Opus 4.6
- Called via `urllib.request` REST — no SDK, no Lambda Layers
- Reads live resource context (S3 ACL settings, SG rules, IAM key metadata) before analysis
- Returns structured JSON: `risk_level`, `is_false_positive`, `safe_to_auto_remediate`,
  `recommended_playbook`, `recommended_actions`, `analysis`, `escalation_reason`
- Safety overrides in `response_validator.py` run after AI response — AI cannot bypass them

**AI Toggle:** When disabled (via dashboard settings), analyzer returns keyword-based fallback
immediately — no API call made. Useful during development to preserve free tier quota.

**Hot-swap:** Provider and model stored in DynamoDB `security-automation-settings`. Read at
invocation time — changes take effect on next finding with zero infrastructure changes.

---

### Remediation Lambdas

| Lambda | Resource Type | Action |
|--------|---------------|--------|
| `security-auto-s3-remediation` | AwsS3Bucket | Enables all 4 Block Public Access settings |
| `security-auto-iam-remediation` | AwsIamAccessKey | Deactivates access keys |
| `security-auto-vpc-remediation` | AwsEc2SecurityGroup | Revokes open-world ingress rules (0.0.0.0/0, ::/0) |
| `security-auto-verification` | All | Confirms fix applied before marking RESOLVED |

All playbooks follow: VALIDATE → SAFETY CHECK → LOG → EXECUTE → VERIFY → LOG (idempotent).

---

### AI Runbook Engine (dashboard Lambda)

Separate from the Step Functions pipeline — operates directly from the dashboard on any finding.

- **Generate:** fetches live resource state via boto3 (S3 block config, SG rules, IAM key list),
  sends to AI with the finding context, gets back step-by-step remediation plan as JSON
- **Apply (inline):** for S3/SG/IAM — executes boto3 calls directly, captures pre-state for undo
- **Apply (advisory):** for other resource types (DynamoDB, RDS, KMS, etc.) — runbook contains
  CLI/Console steps for manual admin execution; marked MANUAL_REVIEW not FAILED
- **Undo:** restores pre-remediation state (re-enables S3 public access, re-adds SG rules,
  re-enables IAM keys)

---

### Notification Lambda (security-auto-notification)

- Sends rich HTML email via SNS with AI analysis summary
- Embeds 1-click Approve / Reject / Manual Review links (API Gateway URLs with task token)
- Stores task token in DynamoDB `findings` table for dashboard to retrieve

---

### Approval Lambda + API Gateway

- REST API: `SecurityAutomationApprovalAPI`
- Endpoints: `GET /approve`, `GET /reject`, `GET /manual` (task token in query string)
- On click: calls `sfn.send_task_success(taskToken, outcome)` → resumes Step Functions
- Dashboard: `POST /dashboard/api/action` with `{finding_id, action}` in JSON body
  (ARNs contain slashes — can't use path params)

---

### DynamoDB Tables

**security-automation-findings** (PK: `finding_id`)

Fields: `resource_type`, `resource_id`, `severity`, `title`, `description`, `ai_analysis`,
`recommended_actions`, `risk_level`, `status`, `task_token`, `created_at`, `updated_at`,
`ttl_epoch` (30-day auto-expire), `environment`, `action_taken`, `runbook`, `runbook_status`,
`runbook_logs`, `undo_data`

Status values: `PENDING_APPROVAL` | `AUTO_REMEDIATED` | `RESOLVED` | `APPROVED` | `REJECTED`
| `MANUAL_REVIEW` | `SUPPRESSED` | `FALSE_POSITIVE` | `FAILED`

**security-automation-settings** (PK: `setting_key`)

Keys: `email_notifications`, `auto_remediation`, `ai_analysis_enabled`, `ai_provider`,
`ai_model`, `batch_remediation_status`

---

### EventBridge Rule

- Name: `securityhub-finding-rule`
- State: **DISABLED** by default (demo uses direct Step Functions invocation)
- Filter: `Compliance.Status=FAILED`, `Workflow.Status=NEW`,
  `Severity.Label` in [MEDIUM, HIGH, CRITICAL], `RecordState=ACTIVE`
- Target: `SecurityRemediationStateMachine`
- Enable via dashboard "Start Pipeline" button or `POST /api/control {"action": "start"}`

---

### CloudWatch

- Log group: `/aws/security-automation` (90-day retention)
- State machine logs: `/aws/states/SecurityRemediationStateMachine` (30-day retention)
- Dashboard: `SecurityAutomation-LiveMonitor`

---

## Safety Design

Enforced in `response_validator.py` — runs after every AI response. AI cannot bypass these:

| Condition | Effect |
|-----------|--------|
| `AutoRemediationExclude=true` tag | Force `safe_to_auto_remediate=False` |
| `Environment=Production` tag | Force `safe_to_auto_remediate=False` |
| Default VPC security group | Force `safe_to_auto_remediate=False` |
| `ServiceAccount=true` tag | Force `safe_to_auto_remediate=False` |
| `Role=CI-Pipeline` tag | Force `safe_to_auto_remediate=False` |
| `recommended_playbook` not in approved list | Force to `manual` |
| AI returns malformed JSON | Default to HIGH risk, escalate (fail-safe) |
| AI API unreachable | Keyword-based fallback routing — pipeline never blocks |

---

## IAM Roles (Least-Privilege)

| Role | Used by |
|------|---------|
| `SecurityAutomation-StepFunctionsRole` | State machine execution |
| `SecurityAutomation-LambdaRemediationRole` | s3/iam/vpc remediation + verification |
| `SecurityAutomation-LambdaAIAnalyzerRole` | AI analyzer (Secrets Manager read, DynamoDB read) |
| `SecurityAutomation-LambdaApprovalRole` | Approval handler (SFN SendTaskSuccess) |
| `SecurityAutomation-LambdaNotificationRole` | Notification (SNS, DynamoDB, SFN) |
| `SecurityAutomation-LambdaVerificationRole` | Verification (S3/SG/IAM read, DynamoDB write) |
| `SecurityAutomation-EventBridgeRole` | EventBridge → SFN StartExecution |
| `SecurityAutomation-LambdaDashboardRole` | Dashboard (full control: DynamoDB, SFN, EC2, S3, IAM, SNS, EventBridge, Secrets Manager, Lambda, API Gateway) |

---

## Terraform Module Map

| Module | Directory | Key resources |
|--------|-----------|---------------|
| `module.iam` | `./modules/iam` | 8 IAM roles |
| `module.dynamodb` | `./modules/dynamodb` | findings + settings tables |
| `module.budget` | `./modules/budget` | monthly cost alert |
| `module.security_hub` | `./modules/security-hub` | Security Hub account activation |
| `module.cloudwatch` | `./modules/cloudwatch` | log group + dashboard |
| `module.sns` | `./modules/sns` | admin alerts topic |
| `module.lambda_remediation` | `./modules/lambda-remediation` | 4 playbook Lambdas |
| `module.lambda_ai_analyzer` | `./modules/lambda-ai-analyzer` | AI triage Lambda |
| `module.lambda_notification` | `./modules/lambda-notification` | email notification Lambda |
| `module.lambda_approval` | `./modules/lambda-approval` | approval handler Lambda |
| `module.lambda_dashboard` | `./modules/lambda-dashboard` | dashboard + all API routes |
| `module.api_gateway` | `./modules/api-gateway` | REST API |
| `module.step_functions` | `./modules/step-functions` | state machine |
| `module.eventbridge` | `./modules/eventbridge` | Security Hub → SFN rule |

---

## Cost (Demo Mode, Config Removed)

| Service | Monthly Cost |
|---------|-------------|
| API Gateway | ~$0.01 (REST API flat fee) |
| Secrets Manager | ~$0.01 (while deployed) |
| Lambda / Step Functions / DynamoDB / SNS / EventBridge | ~$0.00 (pay-per-use) |
| Security Hub | $0.00 (account activation only, no standards) |
| AWS Config | $0.00 (removed — see [Cost Engineering Decision](../README.md#cost-engineering-decision)) |
| **Total** | **~$0.02/month** |

In production with Config enabled (restricted to 5 resource types): ~$0.10–0.20/month.
