# AWS Cloud Security Automation

> AI-powered security incident detection and automated remediation on AWS — B.Tech capstone project

[![Terraform Validate](https://github.com/CynicPoet/aws-security-automation/actions/workflows/terraform-validate.yml/badge.svg)](https://github.com/CynicPoet/aws-security-automation/actions/workflows/terraform-validate.yml)

---

## What This Does

Monitors AWS resources via Security Hub, uses Gemini AI to triage findings, and automatically
remediates misconfigurations — or routes them to a human admin for approval — within seconds.

**MTTR reduction: ~88%** (100 minutes manual → ~20 seconds automated for Category A)

### Live Demo Flow

```
Security Hub finding (e.g. S3 bucket public)
        │
        ▼ < 5 seconds
EventBridge → Step Functions
        │
        ▼ 3–8 seconds
AI Analysis (Gemini 2.5 Flash)
 - False positive? → Suppress
 - Safe to auto-fix? → Fix automatically
 - High risk? → Email admin with 1-click approve/reject
        │
        ▼
Remediation Lambda executes playbook
        │
        ▼
Verification confirms fix → Security Hub updated to RESOLVED
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  AWS Security Hub  (FSBP + CIS standards)                       │
│         │ finding                                                │
│         ▼                                                        │
│  EventBridge Rule (securityhub-finding-rule)                    │
│         │                                                        │
│         ▼                                                        │
│  Step Functions (SecurityRemediationStateMachine)               │
│    ├─ AI Analyzer Lambda (Gemini 2.5 Flash)                     │
│    ├─ S3 Remediation Lambda                                     │
│    ├─ IAM Remediation Lambda                                    │
│    ├─ VPC Remediation Lambda                                    │
│    ├─ Verification Lambda                                       │
│    ├─ Notification Lambda → SNS → Admin Email                  │
│    └─ Approval Handler Lambda ← API Gateway (approve/reject)   │
│                                                                  │
│  CloudWatch (/aws/security-automation) + Dashboard              │
└─────────────────────────────────────────────────────────────────┘
```

See [docs/architecture.md](docs/architecture.md) for full details.

---

## Quick Start

### Prerequisites

- AWS CLI v2 configured (`aws configure`)
- Terraform >= 1.5
- PowerShell 7+ (Windows) or pwsh (Mac/Linux)
- A Gemini API key (free at [aistudio.google.com](https://aistudio.google.com))

### Deploy

```powershell
git clone https://github.com/CynicPoet/aws-security-automation.git
cd aws-security-automation

.\scripts\deploy.ps1 -AdminEmail "you@example.com"
```

### After Deploy (one-time manual steps)

1. **Confirm SNS email**: Check inbox, click "Confirm subscription"
2. **Set AI API key**:
```powershell
aws secretsmanager put-secret-value `
  --secret-id security-automation/ai-api-key `
  --secret-string '{"api_key":"YOUR_GEMINI_KEY","provider":"gemini"}'
```

### Run the Demo

```powershell
.\scripts\demo.ps1
```

Creates 6 intentionally misconfigured resources. Watch them get remediated in the AWS Console:
- **Step Functions** → `SecurityRemediationStateMachine` → Executions
- **CloudWatch** → Dashboards → `SecurityAutomation-LiveMonitor`

---

## Demo Scenarios

| ID | Resource | Tag | Expected Result |
|----|----------|-----|----------------|
| A1 | S3 bucket (public-read) | Environment=Test | Auto-remediated ~20s |
| A2 | Security group SSH open | Environment=Test | Auto-remediated ~20s |
| A3 | Security group all-open | Environment=Test | Auto-remediated ~20s |
| B1 | IAM user + admin key | Role=CI-Pipeline | Admin approval email sent |
| B2 | Security group RDP open | Environment=Production | Admin approval email sent |
| FP | S3 bucket (public website) | PublicAccess=Intentional | Suppressed — no action |

---

## Safety Design

The AI **cannot** auto-remediate resources tagged:

| Tag / Condition | Effect |
|-----------------|--------|
| `AutoRemediationExclude=true` | Always escalate to admin |
| `Environment=Production` | Always escalate to admin |
| Default security group | Never touch |
| `ServiceAccount=true` | IAM remediation always escalates |
| `Role=CI-Pipeline` | IAM remediation always escalates |

On AI failure → system defaults to HIGH risk, escalate (fail-safe, not fail-open).

---

## Cost

**~$0.70/month** at rest.

The dominant cost is Secrets Manager ($0.40/secret/month). Lambda, Step Functions, and API
Gateway are all pay-per-invocation with generous free tiers — effectively $0 at demo scale.

Use `.\scripts\pause-project.ps1` between sessions to disable the EventBridge rule (~$0.60/mo).

---

## Project Structure

```
aws-security-automation/
├── terraform/
│   ├── main.tf                    # Root module wiring all child modules
│   ├── providers.tf               # AWS + archive providers
│   ├── variables.tf               # admin_email, aws_region, ai_provider, ai_model
│   ├── modules/
│   │   ├── iam/                   # 7 IAM roles (least-privilege)
│   │   ├── budget/                # Cost alert at $1/mo
│   │   ├── security-hub/          # FSBP + CIS + AWS Config recorder
│   │   ├── cloudwatch/            # Log group + dashboard + alarms
│   │   ├── sns/                   # Admin alert topic
│   │   ├── api-gateway/           # Approval REST API (/approve /reject /manual)
│   │   ├── lambda-remediation/    # S3, IAM, VPC, Verification playbooks
│   │   ├── lambda-ai-analyzer/    # Gemini/Claude triage + safety overrides
│   │   ├── lambda-notification/   # Rich email with approval links
│   │   ├── lambda-approval/       # Step Functions task token handler
│   │   ├── step-functions/        # State machine ASL + CW logging
│   │   └── eventbridge/           # Security Hub → Step Functions trigger
│   └── simulation/                # Demo misconfigurations (standalone root)
├── scripts/
│   ├── deploy.ps1                 # Full stack deployment
│   ├── destroy.ps1                # Full teardown
│   ├── demo.ps1                   # Create/destroy simulation resources
│   ├── pause-project.ps1          # Disable EventBridge (cost saving)
│   └── resume-project.ps1         # Re-enable EventBridge
├── docs/
│   ├── architecture.md            # Detailed system design
│   ├── manual-vs-auto-mttr.md     # MTTR comparison analysis
│   ├── demo-guide.md              # Step-by-step demo instructions
│   ├── judge-qa.md                # Evaluator Q&A preparation
│   └── cost-log.md                # Monthly cost breakdown
└── tests/
    └── test_response_validator.py  # Safety override unit tests
```

---

## AI Provider Switching

Switch between Gemini and Claude with zero code changes:

```powershell
# Switch to Claude
aws secretsmanager put-secret-value `
  --secret-id security-automation/ai-api-key `
  --secret-string '{"api_key":"YOUR_CLAUDE_KEY","provider":"claude"}'

# Update variable (or re-deploy with -AIProvider claude)
```

---

## Teardown

```powershell
.\scripts\destroy.ps1 -AdminEmail "you@example.com"
```

---

## Documentation

- [Architecture](docs/architecture.md)
- [MTTR Analysis](docs/manual-vs-auto-mttr.md)
- [Demo Guide](docs/demo-guide.md)
- [Judge Q&A](docs/judge-qa.md)
- [Cost Log](docs/cost-log.md)
