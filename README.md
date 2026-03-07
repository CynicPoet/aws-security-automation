# AWS Cloud Security Automation

> AI-powered security finding triage, automated remediation, and real-time dashboard on AWS

[![Terraform Validate](https://github.com/CynicPoet/aws-security-automation/actions/workflows/terraform-validate.yml/badge.svg)](https://github.com/CynicPoet/aws-security-automation/actions/workflows/terraform-validate.yml)

---

## What This Does

Ingests security findings (simulated or real Security Hub), uses AI (Gemini or Claude) to triage
each finding, then either auto-remediates or routes to a human admin for 1-click approval — all
within seconds. A web dashboard provides real-time visibility, manual controls, and AI-generated
runbooks for every finding.

**MTTR reduction: ~88%** (100 minutes manual → ~20 seconds automated for Category A findings)

### Production vs. Demo Mode

| | Production | Demo (this repo) |
|---|---|---|
| Finding source | AWS Config → Security Hub → EventBridge | Simulated findings injected directly into Step Functions |
| Config recorder | `all_supported = true` (all resource types) | **Removed** — see [Cost Engineering Decision](#cost-engineering-decision) |
| Security Hub standards | CIS v1.4, FSBP enabled | Account-level only (no standards) |
| Everything else | Identical | Identical |

The remediation pipeline, AI analysis, approval workflow, dashboard, and runbook engine are
fully functional in both modes. Only the finding *source* differs.

---

## Key Features

- **AI Triage** — Gemini or Claude analyzes every finding: risk level, false positive detection, safe-to-auto-remediate decision, natural language justification
- **Auto-remediation** — S3 public access, security group rules, IAM access keys fixed automatically in ~20 seconds
- **Human-in-the-loop** — High-risk findings trigger approval email with 1-click approve/reject links; Step Functions `waitForTaskToken` holds execution until admin responds
- **Real-time Dashboard** — Web UI showing all findings, statuses, AI analysis details, and controls
- **AI Runbook Engine** — Per-finding: generate runbook → apply inline → undo if needed
- **Batch AI Remediation** — Force-remediate all pending findings at once with configurable retry and failure context feedback
- **AI Provider Hot-swap** — Switch between Gemini and Claude models from the dashboard with no redeploy
- **Simulation Lab** — 5 built-in scenarios (A1-B2) to demo the full pipeline without real misconfigurations
- **Auto-TTL** — Optional: self-destruct all infrastructure after N hours (set at deploy time, prevents post-demo billing)
- **Safety Overrides** — Hardcoded rules the AI cannot bypass (Production tag, CI-Pipeline role, default SGs)

---

## Architecture

### Production Flow

```
AWS Resources change
        |
        v
AWS Config (records change items)
        |
        v
Security Hub evaluates against CIS v1.4 / FSBP standards
        |  finding generated
        v
EventBridge Rule (securityhub-finding-rule)
        |
        v  [same pipeline below]
```

### Demo Flow (this repo)

```
Simulation Lab (dashboard) creates misconfigured resource
        |
        v  finding injected directly
Step Functions: SecurityRemediationStateMachine
        |
        +-- ParseFinding
        |
        +-- AI Analyzer Lambda (Gemini / Claude)
        |       - false positive? suppress
        |       - safe to auto-fix? -> Remediation Lambda
        |       - high risk? -> Notification Lambda -> Admin Email
        |                            |
        |                     1-click approve/reject
        |                     (API Gateway -> Approval Lambda)
        |
        +-- Remediation Lambda (S3 / SG / IAM playbooks)
        |
        +-- Verification Lambda (confirms fix applied)
        |
        +-- Dashboard updated (DynamoDB -> Lambda -> REST API)
```

### Module Map

```
terraform/
  modules/
    iam/                   # 8 IAM roles, all least-privilege
    dynamodb/              # findings + settings tables
    security-hub/          # Security Hub account activation
    cloudwatch/            # Log group + dashboard
    sns/                   # Admin alert topic
    api-gateway/           # REST API (/approve /reject /dashboard/*)
    lambda-remediation/    # S3, IAM, VPC, Verification playbooks
    lambda-ai-analyzer/    # Gemini/Claude triage + safety overrides
    lambda-notification/   # Rich email with approve/reject links
    lambda-approval/       # Step Functions task token handler
    lambda-dashboard/      # Web dashboard + all API routes
    step-functions/        # State machine ASL
    eventbridge/           # Security Hub -> Step Functions (DISABLED by default)
    budget/                # Cost alert + hard-deny IAM action at $5
```

---

## Quick Start

### Prerequisites

- Terraform >= 1.5
- Python 3.x with boto3 (`pip install boto3`)
- PowerShell 7+ (Windows) or pwsh (Mac/Linux)
- AWS IAM user with sufficient permissions
- A Gemini API key (free at [aistudio.google.com](https://aistudio.google.com)) or Claude API key

### Deploy

```powershell
git clone https://github.com/CynicPoet/aws-security-automation.git
cd aws-security-automation

# Copy and fill in credentials
copy scripts\config.ps1.example scripts\config.ps1
# Edit scripts\config.ps1: AWS keys, region, admin email, Gemini/Claude key

.\scripts\quickdeploy.ps1
```

`quickdeploy.ps1` runs 6 steps:
1. Terraform fmt check
2. Terraform validate
3. Terraform apply (~2–3 minutes)
4. Outputs dashboard URL
5. Stores AI API key in Secrets Manager
6. Prompts for auto-terminate timer (recommended: 4h for demos)

### After Deploy

1. **Confirm SNS subscription** — check `admin_email` inbox, click "Confirm subscription"
2. **Open dashboard URL** printed by quickdeploy
3. Pipeline is **DISABLED by default** — click "Start Pipeline" in the dashboard to enable real Security Hub routing

---

## Dashboard

The dashboard is the primary interface. All controls are available from the UI — no AWS Console needed for normal operation.

**URL:** `https://{api-gateway-id}.execute-api.us-east-1.amazonaws.com/prod/dashboard`

### Header Controls

| Control | Function |
|---------|---------|
| Pipeline ON/OFF | Enable/disable EventBridge rule for real Security Hub findings |
| AI toggle | Enable/disable AI API calls (use OFF during development to save tokens) |
| AI config button | Hot-swap AI provider/model (Gemini or Claude) with API key validation |
| Remediate All | Batch AI remediation of all pending findings with progress tracking |
| Simulation Lab | Create/delete the 5 demo scenarios |
| Refresh | Reload findings |
| Terminate | Async self-destruct: deletes all infrastructure from within Lambda |

### Finding Detail Modal

Click any finding to open the detail modal:
- Full resource metadata (ARN, account ID, region, timestamps)
- AI analysis: risk level, safe_to_auto_remediate, escalation reason
- Remediation details: method + step-by-step actions
- Runbook panel: Generate → Apply → Undo (inline boto3 for S3/SG/IAM; advisory CLI steps for other resource types)

---

## Demo Scenarios

Run from the **Simulation Lab** panel in the dashboard.

| ID | Resource | Severity | Expected Result |
|----|----------|----------|-----------------|
| A1 | S3 bucket — public access enabled | HIGH | Auto-remediated ~20s |
| A2 | Security group — SSH open to 0.0.0.0/0 | HIGH | Auto-remediated ~20s |
| A3 | Security group — all traffic open | CRITICAL | Auto-remediated ~20s |
| B1 | IAM user — Role=CI-Pipeline | HIGH | Admin approval email sent |
| B2 | Security group — RDP open, Environment=Production | CRITICAL | Admin approval email sent |

Category A findings are auto-remediated. Category B trigger the human-approval workflow.

---

## Safety Design

The AI cannot override these rules (enforced in `response_validator.py`):

| Condition | Effect |
|-----------|--------|
| `AutoRemediationExclude=true` tag | Always escalate to admin |
| `Environment=Production` tag | Always escalate to admin |
| Default security group | Never modify |
| `ServiceAccount=true` tag | IAM remediation always escalates |
| `Role=CI-Pipeline` tag | IAM remediation always escalates |
| AI returns malformed JSON | Default to HIGH risk, escalate (fail-safe) |
| AI API failure | Keyword-based fallback routing, never fail-open |

---

## Cost Engineering Decision

### What was removed and why

During development, `security-hub/main.tf` had:

```hcl
recording_group {
  all_supported                 = true
  include_global_resource_types = true
}
```

This recorded **every resource change account-wide** at $0.003/item. With normal development
activity (Lambda deploys, SG changes, S3 modifications), this generated 1,633 recorded items
in one period — a $4.90 charge that dominated the entire bill.

**Decision:** Remove Config and Security Hub standards subscriptions from the demo environment.
Config is not needed for the simulation-based demo — findings are injected directly into Step
Functions. Removing it drops the demo cost from ~$5/month to ~$0.00.

### What this trades off

In a real deployment, the finding pipeline works as follows:
- AWS Config records resource state changes
- Security Hub evaluates them against CIS v1.4 / FSBP compliance rules
- Non-compliant findings are published and EventBridge routes them to this pipeline

That end-to-end flow is fully implemented in the architecture (EventBridge rule, Security Hub
account activation, all IAM permissions in place). The demo simply uses simulated findings
at the injection point instead of real Security Hub findings.

### Interview answer

> "In a real deployment, Config records resource changes and Security Hub evaluates them against
> CIS/FSBP standards, generating findings that EventBridge routes to my pipeline. For the demo
> I removed Config and standards subscriptions because Config's all-resources recording was
> generating $5/month in charges — more than the rest of the infrastructure combined. The
> remediation pipeline, AI analysis, approval workflow, and dashboard are all fully functional.
> The finding injection point changed from real Security Hub to simulated events. This was a
> deliberate cost-vs-fidelity tradeoff for a demo environment."

---

## AI Provider

Switch between Gemini and Claude from the dashboard — no redeploy needed.

**Via dashboard:** Click the "AI" button in the header → select provider → paste API key → validate → pick model → save.

**Supported models:**
- Gemini: fetches live model list from Google API (filtered to `generateContent`-capable models)
- Claude: Haiku 4.5, Sonnet 4.6, Opus 4.6

**Default:** Gemini 2.0 Flash → 2.0 Flash Lite → 1.5 Flash (fallback chain)

Settings (provider, model) are stored in DynamoDB. API key is stored in Secrets Manager.
Changes take effect on the next finding — no Lambda redeploy required.

---

## Auto-TTL (Post-demo Safety)

At the end of `quickdeploy.ps1`, you are prompted:

```
Auto-terminate after how many hours? [0 = manual only, recommended: 4]
```

Entering a number creates a one-time EventBridge cron rule (`security-auto-ttl`) that fires
at `now + N hours` and invokes the dashboard Lambda's `__terminate` handler. This deletes:
Step Functions, DynamoDB tables, Lambda functions, SNS, EventBridge rules, CloudWatch logs,
Secrets Manager secret, API Gateway, and finally itself.

This ensures billing stops automatically after a demo even if you forget to run quickdestroy.

---

## Cost

**~$0.01–0.02/month** while deployed (demo mode, Config removed).

| Service | Cost |
|---------|------|
| API Gateway | ~$0.01/month (REST API flat fee, prorated) |
| Secrets Manager | ~$0.01/month (while deployed; deleted on terminate) |
| Lambda / Step Functions / SNS / EventBridge | ~$0.00 (pay-per-invocation, free tier) |
| AWS Config | $0.00 (removed from demo) |
| Security Hub | $0.00 (account activation only, no standards) |
| **Total** | **~$0.02/month** |

**Budget guard:** An AWS Budgets action is configured to attach a `BudgetExceededDenyAll` IAM
deny policy to the deployer user if monthly spend reaches $5. This acts as a hard circuit
breaker against unexpected charges.

---

## Teardown

```powershell
.\scripts\quickdestroy.ps1
```

Or use the **Terminate** button in the dashboard (async self-destruct from within Lambda).

`quickdestroy.ps1` runs 6 steps: stops SFN executions → removes Config → disables Security Hub
standards → deletes simulation resources → Terraform destroy → post-cleanup (CW logs, EventBridge).
Shows a resource discovery scan before confirming deletion.

---

## Project Structure

```
aws-security-automation/
├── terraform/
│   ├── main.tf                        # Root module, wires all child modules
│   ├── providers.tf                   # AWS + archive providers
│   ├── variables.tf                   # admin_email, aws_region, ai_provider, ai_model
│   └── modules/
│       ├── iam/                       # 8 IAM roles (least-privilege)
│       ├── budget/                    # $5 hard-limit budget + deny-all action
│       ├── security-hub/              # Security Hub account activation (no Config, no standards)
│       ├── dynamodb/                  # findings + settings tables
│       ├── cloudwatch/                # Log group + dashboard
│       ├── sns/                       # Admin alert topic
│       ├── api-gateway/               # REST API (/approve /reject /dashboard/*)
│       ├── lambda-remediation/        # S3, IAM, VPC, Verification playbooks
│       ├── lambda-ai-analyzer/        # Gemini/Claude triage + safety overrides
│       ├── lambda-notification/       # Rich HTML email with approval links
│       ├── lambda-approval/           # Step Functions task token handler
│       ├── lambda-dashboard/          # Web dashboard + all /api/* routes
│       ├── step-functions/            # State machine ASL + CW logging
│       └── eventbridge/               # Security Hub -> Step Functions (DISABLED by default)
├── scripts/
│   ├── quickdeploy.ps1                # One-click deploy (6 steps including auto-TTL)
│   ├── quickdestroy.ps1               # Full teardown with resource discovery scan
│   ├── config.ps1                     # Local credentials (gitignored)
│   └── config.ps1.example             # Template
├── docs/
│   ├── architecture.md                # Detailed system design
│   ├── manual-vs-auto-mttr.md         # MTTR comparison analysis
│   ├── demo-guide.md                  # Step-by-step demo instructions
│   ├── judge-qa.md                    # Evaluator Q&A preparation
│   └── cost-log.md                    # Monthly cost breakdown + incident log
└── tests/
    └── test_response_validator.py     # Safety override unit tests
```

---

## Documentation

- [Architecture](docs/architecture.md)
- [MTTR Analysis](docs/manual-vs-auto-mttr.md)
- [Demo Guide](docs/demo-guide.md)
- [Judge Q&A](docs/judge-qa.md)
- [Cost Log](docs/cost-log.md)
