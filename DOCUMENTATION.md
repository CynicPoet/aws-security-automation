# AWS Security Automation System — Complete Project Documentation

> **Author:** Shivam Pokharkar  
> **Repository:** https://github.com/CynicPoet/aws-security-automation  
> **Region:** us-east-1  
> **Stack:** AWS Serverless · Terraform IaC · Python 3.11 · AI-Powered (Gemini / Claude)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Objectives & Success Metrics](#3-objectives--success-metrics)
4. [Technology Stack](#4-technology-stack)
5. [System Architecture Overview](#5-system-architecture-overview)
6. [Component Deep-Dive — Every Service Explained](#6-component-deep-dive--every-service-explained)
7. [Complete Data Flow — Step by Step](#7-complete-data-flow--step-by-step)
8. [Step Functions State Machine — All States](#8-step-functions-state-machine--all-states)
9. [AI Analysis Engine](#9-ai-analysis-engine)
10. [Operations Dashboard](#10-operations-dashboard)
11. [MTTR Reduction — Proof & Calculation](#11-mttr-reduction--proof--calculation)
12. [How This Differs From Other Solutions](#12-how-this-differs-from-other-solutions)
13. [Security & Safety Guardrails](#13-security--safety-guardrails)
14. [Rough Architecture Diagram — For Whiteboard Interviews](#14-rough-architecture-diagram--for-whiteboard-interviews)
15. [Interview Preparation — Architecture Walkthrough](#15-interview-preparation--architecture-walkthrough)
16. [Interview Q&A — All Questions & Answers](#16-interview-qa--all-questions--answers)
17. [Dependencies & Failure Mitigation](#17-dependencies--failure-mitigation)
18. [Monitoring & Observability](#18-monitoring--observability)
19. [Cost Analysis](#19-cost-analysis)
20. [Future Scope & Improvements](#20-future-scope--improvements)
21. [Appendix — Reference Tables](#21-appendix--reference-tables)

---

## 1. Executive Summary

The **AWS Security Automation System** is a fully serverless, AI-powered security operations platform built entirely on AWS. It automatically detects security misconfigurations reported by AWS Security Hub, uses a large language model (Google Gemini or Anthropic Claude) to analyze each finding for risk, false-positives, and remediation safety, then either auto-remediates the issue or routes it to a human administrator for approval — all within minutes.

The system reduces Mean Time to Remediate (MTTR) from an industry-average **4–8 hours** to under **5 minutes** for auto-remediated findings (a **~98% reduction**) and under **20 minutes** for admin-approved findings (a **~96% reduction**).

It is deployed as Infrastructure-as-Code using Terraform, costs approximately **$3–15/month** on AWS free/pay-per-use tiers, and requires zero standing servers.

---

## 2. Problem Statement

### The Challenge

Cloud security teams face a relentless stream of security findings from tools like AWS Security Hub. These findings range from critical misconfigurations (S3 buckets with public access, overly permissive security groups, compromised IAM credentials) to low-severity informational alerts and outright false positives.

### Pain Points in Manual Security Operations

| Pain Point | Impact |
|---|---|
| **Alert fatigue** | Security teams receive hundreds of findings daily; most are not reviewed in time |
| **Slow response** | Manual triage, approval chains, and implementation take 4–8 hours on average |
| **Human error** | Manual remediation scripts can misconfigure resources, causing outages |
| **No context awareness** | Teams remediate without knowing if the resource is production-tagged, a CI pipeline, or intentionally public |
| **No audit trail** | Ad-hoc fixes lack structured logging, making compliance reviews difficult |
| **False positives** | Teams waste hours investigating findings that are not actually security issues |
| **On-call burden** | Security engineers are paged at 2AM for findings that could be auto-resolved safely |
| **No consistency** | Different team members apply different remediation standards |

### Why This Matters

According to IBM's Cost of a Data Breach Report (2024), the average time to identify and contain a breach is **277 days**, and **75% of incidents** begin with a misconfiguration or compromised credential — both of which this system directly remediates. The Ponemon Institute reports that organizations with automated incident response save an average of **$1.76 million per breach**.

---

## 3. Objectives & Success Metrics

### Primary Objectives

1. **Automated Detection** — Ingest security findings from AWS Security Hub in real time via EventBridge
2. **AI-Powered Triage** — Use LLMs to assess risk level, detect false positives, and determine if auto-remediation is safe
3. **Context-Aware Remediation** — Gather live resource context (tags, configurations, usage patterns) before taking any action
4. **Human-in-the-Loop** — Route sensitive findings (production resources, CI pipelines, service accounts) to human administrators for approval
5. **Auditability** — Persist every finding, decision, and action in DynamoDB with full timestamps and undo capability
6. **Zero Infrastructure Overhead** — 100% serverless; no EC2, no containers, no maintenance

### Success Metrics

| Metric | Target | Achieved |
|---|---|---|
| MTTR — Auto path | < 5 minutes | ~2–4 minutes |
| MTTR — Approval path | < 30 minutes | ~15–20 minutes (admin response dependent) |
| False positive escalation | 0 false positives auto-remediated | Enforced by AI + hardcoded guardrails |
| Production resource safety | 0 production auto-remediations | Enforced by tag-based guardrail |
| Audit trail coverage | 100% of findings logged | Every finding persisted in DynamoDB |
| Infrastructure cost | < $20/month | ~$3–15/month at typical load |
| IaC coverage | 100% | All resources in Terraform |

---

## 4. Technology Stack

### AWS Services

| Service | Purpose |
|---|---|
| **AWS Security Hub** | Source of security findings (FAILED compliance, misconfigurations) |
| **Amazon EventBridge** | Event-driven trigger — routes Security Hub findings to Step Functions |
| **AWS Step Functions** | Orchestration engine — manages the full remediation workflow as a state machine |
| **AWS Lambda** (×8) | Serverless compute for AI analysis, remediation, notification, approval, and dashboard |
| **Amazon DynamoDB** (×2) | NoSQL persistence for findings and runtime configuration |
| **Amazon SNS** | Email notifications to admin with approval links |
| **Amazon API Gateway** | REST API for approval callbacks and dashboard web interface |
| **AWS Secrets Manager** | Secure storage of AI provider API keys (Gemini / Claude) |
| **Amazon CloudWatch Logs** | Centralized logging for all Lambdas and Step Functions |
| **AWS IAM** | Least-privilege role-based access control for every Lambda |

### External Services

| Service | Purpose |
|---|---|
| **Google Gemini API** | Primary AI provider for security finding analysis and runbook generation |
| **Anthropic Claude API** | Alternative AI provider (hot-swappable at runtime) |

### Infrastructure & Development Tools

| Tool | Purpose |
|---|---|
| **Terraform** | Infrastructure-as-Code — 100% of AWS resources defined and deployed |
| **Python 3.11** | Runtime for all Lambda functions |
| **GitHub** | Version control and CI/CD (Terraform validate on pull requests) |

---

## 5. System Architecture Overview

### Architecture Diagram

> Insert the final ChatGPT-generated architecture diagram here.
> File: `architecture-diagram.png`

The system is organized into five functional zones within the AWS Region `us-east-1`:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ AWS Region: us-east-1                                                        │
│                                                                              │
│  ┌─────────────┐  ┌──────────────────────┐  ┌────────────────────────────┐ │
│  │1. Event     │  │2. Orchestration &    │  │3. Remediation &            │ │
│  │   Ingestion │  │   AI Analysis        │  │   Verification             │ │
│  └─────────────┘  └──────────────────────┘  └────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │4. Notification & Approval                                              │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │5. Operations Dashboard (Full Width)                                    │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │   Data Layer: DynamoDB × 2 | Secrets Manager | CloudWatch Logs        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                              External: Gemini API | Claude API
```

### Two Execution Paths

```
PATH A (Auto-Remediation):
Security Hub → EventBridge → Step Functions → AI Analysis →
[Risk: Safe to auto] → Remediate (S3/IAM/VPC) → Verify → RESOLVED ✓

PATH B (Admin Approval):
Security Hub → EventBridge → Step Functions → AI Analysis →
[Risk: Needs approval] → Notify Admin (email) → Admin clicks link →
API Gateway → Approval Handler → Step Functions callback →
Remediate → Verify → RESOLVED ✓
```

---

## 6. Component Deep-Dive — Every Service Explained

### 6.1 AWS Security Hub

**What it does:** AWS Security Hub aggregates security findings from AWS services (GuardDuty, Config, Inspector, Macie) and partner tools into a single, standardized feed using the AWS Security Finding Format (ASFF).

**Role in this system:** Acts as the source of truth for security events. This system subscribes to findings that have:
- `Compliance.Status = FAILED`
- `Workflow.Status = NEW`
- `Severity = MEDIUM | HIGH | CRITICAL`
- `RecordState = ACTIVE`

**Why Security Hub and not GuardDuty directly?** Security Hub normalizes findings from many sources into a consistent ASFF format. This means the same pipeline handles findings from GuardDuty, AWS Config Rules, Inspector, and even custom finding providers — without code changes.

---

### 6.2 Amazon EventBridge

**Resource name:** `securityhub-finding-rule`  
**Default state:** DISABLED (prevents accidental auto-remediation in new deployments)  
**Target:** `SecurityRemediationStateMachine` (Step Functions)  
**Role:** `SecurityAutomation-EventBridgeRole`

**What it does:** EventBridge is a serverless event bus. It listens for Security Hub finding events matching the filter pattern and triggers a Step Functions execution for each one, passing the full finding JSON as input.

**Why EventBridge and not Lambda directly?** EventBridge provides:
- Native integration with Security Hub (no polling needed)
- Built-in filtering — only matching findings trigger execution
- Decoupled architecture — the trigger layer is independent of processing
- At-least-once delivery with built-in retry

**Key design decision:** The rule is DISABLED by default. Operators explicitly enable it via the dashboard or AWS Console. This prevents accidental auto-remediation immediately after a fresh deployment.

---

### 6.3 AWS Step Functions — `SecurityRemediationStateMachine`

**Type:** Standard Workflow (not Express)  
**Execution model:** One execution per security finding  
**Max execution duration:** 1 year (findings wait up to 1 hour for admin approval)

**What it does:** Step Functions is the orchestration backbone. It manages the entire lifecycle of a security finding — from initial AI analysis through remediation to verification — as a deterministic state machine. Every transition is logged, every state is durable, and the execution history is preserved.

**Why Step Functions and not Lambda chaining or SQS?**

| Alternative | Problem |
|---|---|
| Lambda calling Lambda | No visibility into execution state; failures are silent; no built-in retry |
| SQS queue chain | No state machine logic; hard to implement wait-for-approval pattern |
| Lambda + SQS + SNS | Complex wiring; no native audit trail; difficult to express conditional routing |
| Step Functions | Visual execution history, native waitForTaskToken, built-in retry, CloudWatch integration, conditional branching |

**Why Standard Workflow and not Express?**  
Standard Workflows support the `waitForTaskToken` callback pattern (pausing for 1 hour while waiting for human approval). Express Workflows have a maximum duration of 5 minutes and do not support task token callbacks.

---

### 6.4 Lambda: `security-auto-ai-analyzer`

**Memory:** 256 MB | **Timeout:** 60 seconds | **Runtime:** Python 3.11

**What it does:**
1. Reads AI provider configuration from DynamoDB (supports runtime hot-swap)
2. Retrieves the AI API key from Secrets Manager
3. Gathers live infrastructure context about the affected resource (S3 bucket settings, IAM user tags/keys, EC2 security group rules)
4. Constructs a structured prompt and calls Gemini or Claude
5. Validates the JSON response against a strict schema
6. Applies hardcoded safety overrides (production tags, CI pipelines cannot be auto-remediated regardless of what AI says)
7. Returns a structured analysis object to Step Functions

**Why 256 MB?** The infrastructure context gathering makes multiple AWS API calls synchronously. 256 MB provides enough headroom for boto3 connection pooling and JSON processing without hitting memory limits.

**Fallback behavior:** If AI call fails entirely, the Lambda uses keyword-based routing (checking finding title for known patterns) to make a safe decision rather than failing the entire pipeline.

---

### 6.5 Lambda: `security-auto-s3-remediation`

**Memory:** 128 MB | **Timeout:** 60 seconds

**What it does:**
1. Validates resource is not tagged `AutoRemediationExclude=true` or `Environment=Production`
2. Calls `s3.put_bucket_public_access_block()` with all four settings set to `True`:
   - `BlockPublicAcls: True`
   - `IgnorePublicAcls: True`
   - `BlockPublicPolicy: True`
   - `RestrictPublicBuckets: True`
3. Calls `s3.put_bucket_acl(ACL='private')` to revoke any public ACL grants
4. Writes the finding to DynamoDB with status `AUTO_REMEDIATED`

**Idempotency:** The `put_bucket_public_access_block` call is idempotent — calling it twice has the same effect as calling it once.

---

### 6.6 Lambda: `security-auto-iam-remediation`

**Memory:** 128 MB | **Timeout:** 60 seconds

**What it does:**
1. Calls `iam.list_access_keys()` to enumerate all active keys for the user
2. For each active key: calls `iam.update_access_key(Status='Inactive')` — this preserves the key for recovery but prevents it from being used
3. Attaches a deny-all inline policy named `SecurityAutomation-EmergencyDenyAll` that blocks all AWS actions regardless of other policies
4. Writes to DynamoDB with status `AUTO_REMEDIATED`

**Why deactivate keys instead of deleting?** Deletion is irreversible. Deactivation allows an administrator to re-enable a key if the finding was a false positive. This aligns with the system's core principle: **no deletions, all actions reversible**.

**The EmergencyDenyAll policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [{"Effect": "Deny", "Action": "*", "Resource": "*"}]
}
```
This is an explicit Deny which overrides all Allow statements, effectively isolating the user immediately.

---

### 6.7 Lambda: `security-auto-vpc-remediation`

**Memory:** 128 MB | **Timeout:** 60 seconds

**What it does:**
1. Calls `ec2.describe_security_groups()` to get all current ingress rules
2. Identifies rules with source CIDR `0.0.0.0/0` (IPv4 any) or `::/0` (IPv6 any)
3. Calls `ec2.revoke_security_group_ingress()` to remove exactly those over-permissive rules
4. Preserves rules that allow access from specific CIDRs, security groups, or prefix lists
5. Writes to DynamoDB with status `AUTO_REMEDIATED`

**Precision:** Only removes the specific over-permissive rules. Does not touch rules with specific CIDR ranges. This minimizes blast radius.

---

### 6.8 Lambda: `security-auto-verification`

**Memory:** 128 MB | **Timeout:** 60 seconds

**What it does:**
After any remediation (auto or admin-approved), the verification Lambda confirms the fix was actually applied:

- **S3:** Calls `get_bucket_public_access_block()` — checks all four flags are `True`
- **IAM:** Calls `list_access_keys()` — checks all keys are `Inactive`; calls `get_user_policy()` — checks `EmergencyDenyAll` policy is attached
- **VPC:** Calls `describe_security_groups()` — checks no `0.0.0.0/0` or `::/0` ingress rules remain

If verification passes:
- Calls `securityhub.batch_update_findings()` with `WorkflowStatus: RESOLVED`
- Updates DynamoDB finding to status `RESOLVED`

**Why a separate verification step?** Remediation calls can succeed at the API level but fail to take effect due to service propagation delays, permission boundaries, or SCP restrictions. The verification step closes this gap and provides audit evidence that the fix is confirmed.

---

### 6.9 Lambda: `security-auto-notification`

**Memory:** 128 MB | **Timeout:** 30 seconds

**What it does:**
This Lambda is invoked by Step Functions using the **waitForTaskToken** callback pattern:

1. Step Functions passes a one-time `task_token` alongside the finding data
2. The Lambda stores the finding in DynamoDB with `status=PENDING_APPROVAL` and the `task_token` embedded in the record
3. If the `email_notifications` setting is enabled, it constructs an HTML email with three clickable links:
   - **[Approve + Action ID]** → `GET /approve?token={encoded_token}&action={action_id}`
   - **[Reject]** → `GET /reject?token={encoded_token}`
   - **[Mark Manual]** → `GET /manual?token={encoded_token}`
4. Publishes the email via `sns.publish()` to `security-automation-admin-alerts`
5. Returns — Step Functions is now PAUSED, waiting for the task token callback

**The waitForTaskToken Pattern:**
```
Step Functions → Invoke Notification Lambda (passing task_token in payload)
                   ↓
              Lambda stores token in DynamoDB, sends email, returns
                   ↓
         Step Functions PAUSES (heartbeat timeout: 1 hour)
                   ↓
         Admin clicks email link → API Gateway → Approval Handler
                   ↓
         sfn.send_task_success(taskToken=...) → Step Functions RESUMES
```

**Why SNS instead of SES directly?** SNS provides a managed subscription list with email confirmation, retry logic, and easy unsubscription. SES would require additional domain verification and bounce handling.

---

### 6.10 Lambda: `security-auto-approval-handler`

**Memory:** 128 MB | **Timeout:** 10 seconds

**What it does:**
1. Receives an HTTP GET request from the admin clicking an email link
2. URL-decodes the `token` query parameter (the Step Functions task token)
3. Routes based on path:
   - `/approve` → calls `sfn.send_task_success(output={admin_decision: "APPROVED", approved_action: <int>})`
   - `/reject` → calls `sfn.send_task_success(output={admin_decision: "REJECTED"})`
   - `/manual` → calls `sfn.send_task_success(output={admin_decision: "MANUAL"})`
4. Returns an HTML confirmation page to the admin's browser

**Security note:** The task token itself serves as authentication — it is a one-time, cryptographically random token generated by Step Functions. Without the token, the endpoint cannot be called successfully. Tokens expire when the execution completes or times out.

---

### 6.11 Lambda: `security-auto-dashboard`

**Memory:** 256 MB | **Timeout:** 30 seconds

**What it does:** This is the most feature-rich Lambda in the system. It serves a complete single-page web application for security operations, handling all API routes from a single Lambda function.

**Features:**
- Live findings monitor with status, severity, and AI analysis display
- Pipeline control (enable/disable EventBridge rule)
- Simulation Lab with 5 realistic attack scenarios
- AI runbook generation — generates step-by-step remediation plans using AI
- Inline runbook execution — applies S3, IAM, and VPC fixes directly
- Runbook undo — reverses any runbook-applied change
- Batch remediation — AI-assisted remediation of all pending findings
- AI provider hot-swap — switch between Gemini and Claude at runtime without redeployment
- Settings management — toggle email notifications, auto-remediation, AI analysis
- One-click infrastructure terminate — destroys all resources from within the dashboard

**Why a single Lambda for the entire dashboard?** This is an intentional architectural choice to minimize deployment complexity and cost. A single Lambda with a `/{proxy+}` route handles all dashboard traffic. The Lambda reads the path and HTTP method to route internally. This avoids API Gateway-to-Lambda mapping complexity and keeps the deployment unit atomic.

---

### 6.12 Amazon DynamoDB — `security-automation-findings`

**Primary Key:** `finding_id` (String, Hash)  
**GSI:** `status-created-index` — Hash: `status`, Range: `created_at`  
**TTL:** `ttl_epoch` (30-day automatic expiry)

**What it stores:** Every security finding processed by the system, including:
- Resource details (type, ID, ARN, account, region)
- AI analysis result (risk level, false positive flag, recommended playbook)
- Current status in the remediation lifecycle
- Step Functions task token (for pending approvals)
- Generated runbook JSON, execution logs, and undo data
- Timestamps for audit trail

**Finding Status Lifecycle:**
```
PENDING_APPROVAL ──► APPROVED ──► RESOLVED
                 └──► REJECTED
                 └──► MANUAL_REVIEW
AUTO_REMEDIATED ──────────────► RESOLVED
FALSE_POSITIVE (terminal)
FAILED (terminal — remediation error)
```

**Why DynamoDB over RDS?** This workload is perfectly suited to DynamoDB:
- Variable schema (different resource types have different fields)
- Workload is bursty (many findings in a short period, then quiet)
- No complex JOINs required
- Pay-per-request billing fits the sporadic usage pattern
- TTL-based auto-expiry eliminates maintenance overhead
- On-demand scaling handles load spikes without provisioning

---

### 6.13 Amazon DynamoDB — `security-automation-settings`

**Primary Key:** `setting_key` (String, Hash)

**What it stores:** Runtime configuration key-value pairs:

| Key | Values | Purpose |
|---|---|---|
| `email_notifications` | `"true"` / `"false"` | Controls SNS email sending |
| `auto_remediation` | `"true"` / `"false"` | If false, ALL findings go to admin approval |
| `ai_analysis_enabled` | `"true"` / `"false"` | If false, uses keyword-based fallback |
| `ai_provider` | `"gemini"` / `"claude"` | Current active AI provider |
| `ai_model` | e.g. `"gemini-2.5-flash"` | Specific model in use |
| `batch_remediation_status` | `"idle"` / `"running"` | Tracks batch job state |

**Why a separate settings table?** The settings table serves as a runtime control plane. By storing configuration in DynamoDB rather than Lambda environment variables, settings can be changed in real time from the dashboard without redeploying any Lambda function. This is the key to hot-swapping AI providers and toggling behaviors dynamically.

---

### 6.14 Amazon SNS — `security-automation-admin-alerts`

**Type:** Standard Topic  
**Subscription:** Email (to admin address configured at deploy time)

**What it does:** Delivers the admin approval email containing the finding summary and three clickable action links. The email body includes:
- Finding title and severity
- AI risk assessment and analysis
- Resource type, ID, and region
- Recommended remediation action
- Three HTML-formatted action buttons linking to the API Gateway approval endpoints

---

### 6.15 Amazon API Gateway — `SecurityAutomationApprovalAPI`

**Type:** REST API  
**Stage:** `prod`  
**Integration type:** AWS_PROXY (Lambda proxy)

**Endpoints:**

| Path | Method | Lambda | Purpose |
|---|---|---|---|
| `/approve` | GET | approval-handler | Admin approves a finding |
| `/reject` | GET | approval-handler | Admin rejects a finding |
| `/manual` | GET | approval-handler | Admin marks as manual |
| `/dashboard` | GET | dashboard | Serves dashboard HTML |
| `/dashboard/{proxy+}` | ANY | dashboard | All dashboard API calls |

**Why REST API over HTTP API?** REST API supports:
- Resource policies for IP-based access control
- Usage plans for rate limiting
- More granular stage variable management
- Required for Lambda proxy integration with query string handling

---

### 6.16 AWS Secrets Manager — `security-automation/ai-api-key`

**Secret format:**
```json
{
  "api_key": "AIzaSy...",
  "provider": "gemini"
}
```

**What it does:** Stores the AI provider API key securely. The key is retrieved at Lambda invocation time — it is never embedded in code, environment variables, or deployment artifacts.

**Why Secrets Manager and not Parameter Store?**
- Secrets Manager supports automatic rotation (can be configured)
- The `put_secret_value` API allows runtime updates from the dashboard without redeployment
- KMS-encrypted at rest by default
- Fine-grained IAM access per-Lambda

---

### 6.17 Amazon CloudWatch Logs

**Log groups:**
- `/aws/states/SecurityRemediationStateMachine` (Level: ALL — every state transition logged)
- `/aws/lambda/security-auto-*` — one group per Lambda (8 total)
- **Retention:** 30 days for all groups

**Structured logging:** Each Lambda emits structured JSON log entries with fields:
- `event_type` (AI_ANALYSIS_START, AI_ANALYSIS_COMPLETE, ERROR, etc.)
- `finding_id`, `resource_type`, `resource_id`, `severity`
- `duration_ms` for performance tracking
- Contextual details relevant to the event type

---

## 7. Complete Data Flow — Step by Step

### Path A: Auto-Remediation (Happy Path)

```
1. AWS Security Hub generates a finding:
   → resource_type: AwsS3Bucket
   → severity: HIGH
   → title: "S3 Bucket Allows Public Read Access"
   → compliance: FAILED, workflow: NEW

2. EventBridge Rule (securityhub-finding-rule) matches the event
   → Rule state must be ENABLED
   → Calls sfn:StartExecution with finding JSON as input

3. Step Functions execution begins: SecurityRemediationStateMachine
   → State: ParseFinding (Pass state)
   → Extracts: finding_id, resource_type, resource_id, severity, title, description

4. State: AIAnalysis
   → Invokes security-auto-ai-analyzer Lambda
   → AI Analyzer:
       a. Reads DynamoDB settings for ai_provider, ai_model overrides
       b. Calls secretsmanager:GetSecretValue for API key
       c. Calls s3:GetBucketTagging, GetBucketPublicAccessBlock, GetBucketWebsite
       d. Constructs prompt with finding details + infrastructure context
       e. HTTPS POST to https://generativelanguage.googleapis.com/v1beta/models/
          gemini-2.5-flash:generateContent?key={api_key}
       f. Receives JSON: {risk_level: "HIGH", is_false_positive: false,
          safe_to_auto_remediate: true, recommended_playbook: "s3_remediation", ...}
       g. Applies hardcoded safety overrides (none triggered for this finding)
   → Returns ai_analysis object to Step Functions

5. State: IsFalsePositive?
   → is_false_positive = false → continue to IsSafeToAutoRemediate

6. State: IsSafeToAutoRemediate?
   → safe_to_auto_remediate = true → continue to DetermineResourceType

7. State: DetermineResourceType
   → resource_type contains "S3" → RemediateS3

8. State: RemediateS3
   → Invokes security-auto-s3-remediation Lambda
   → Lambda:
       a. Extracts bucket name from resource_id (e.g., "arn:aws:s3:::my-bucket")
       b. Calls s3:PutBucketPublicAccessBlock (all 4 flags = True)
       c. Calls s3:PutBucketAcl(ACL='private')
       d. Writes to DynamoDB: {finding_id, status: 'AUTO_REMEDIATED', ...}
   → Returns remediation_result to Step Functions

9. State: VerifyRemediation
   → Invokes security-auto-verification Lambda
   → Lambda:
       a. Calls s3:GetBucketPublicAccessBlock → confirms all 4 flags are True
       b. Calls securityhub:BatchUpdateFindings → sets WorkflowStatus=RESOLVED
       c. Calls dynamodb:UpdateItem → sets status=RESOLVED
   → Returns {verification_passed: true}

10. State: EndSuccess (Succeed)
    → Execution completes successfully
    → Total time: ~2–4 minutes
```

### Path B: Admin Approval Required

```
1–4. Same as Path A through AIAnalysis

5. State: IsFalsePositive? → false → continue

6. State: IsSafeToAutoRemediate?
   → Finding is a production-tagged security group (tag: Environment=Production)
   → ai_analysis.safe_to_auto_remediate = false (AI + guardrail both flag this)
   → Route to NotifyAdmin

7. State: NotifyAdmin (waitForTaskToken)
   → Invokes security-auto-notification Lambda with payload:
       { finding: {...}, ai_analysis: {...}, task_token: "AAAAKg..." }
   → Notification Lambda:
       a. Puts finding in DynamoDB: {status: 'PENDING_APPROVAL', task_token: 'AAAAKg...'}
       b. Reads settings: email_notifications = "true"
       c. Constructs email with approval links embedding URL-encoded task_token
       d. Calls sns:Publish → email delivered to admin
   → Step Functions PAUSES (heartbeat timeout: 3600s)

8. Admin receives email → Reviews finding and AI analysis
   → Clicks [Approve] button → browser sends:
     GET https://{api-id}.execute-api.us-east-1.amazonaws.com/prod/approve
         ?token={URL-encoded-task-token}&action=1

9. API Gateway routes to security-auto-approval-handler Lambda
   → Lambda:
       a. URL-decodes the token
       b. Calls sfn:SendTaskSuccess(
            taskToken="AAAAKg...",
            output={"admin_decision": "APPROVED", "approved_action": 1}
          )

10. Step Functions RESUMES with approval_result in state

11. State: RouteAdminDecision
    → admin_decision = "APPROVED" → ExecuteApprovedPlaybook

12. State: ExecuteApprovedPlaybook
    → resource_type contains "SecurityGroup" → ApprovedRemediateVPC

13. State: ApprovedRemediateVPC
    → Invokes security-auto-vpc-remediation Lambda
    → Lambda executes the approved action
    → Updates DynamoDB: {status: 'APPROVED'}

14. State: VerifyRemediation → VerifyRemediation Lambda → RESOLVED

15. State: EndSuccess
    → Total time: ~15–20 minutes (dominated by human response time)
```

### Path C: False Positive Suppression

```
1–4. Same as Path A through AIAnalysis

5. State: IsFalsePositive?
   → is_false_positive = true (AI detected intentional public bucket with PublicAccess=Intentional tag)
   → Route to SuppressFalsePositive

6. State: SuppressFalsePositive (Pass state)
   → Logs suppression

7. State: EndFalsePositive (Succeed)
   → Finding is acknowledged but not remediated
   → No DynamoDB write (or written as FALSE_POSITIVE via dashboard API)
```

---

## 8. Step Functions State Machine — All States

```
SecurityRemediationStateMachine
│
├── ParseFinding (Pass)
│   Purpose: Normalize EventBridge finding event to standard format
│   Output: finding_id, resource_type, resource_id, severity, title, description
│   Next: AIAnalysis
│
├── AIAnalysis (Task — Lambda)
│   Lambda: security-auto-ai-analyzer
│   Timeout: 90s | Retry: 2 attempts, 5s interval, 2x backoff
│   Catch: States.ALL → HandleError
│   Next: IsFalsePositive
│
├── IsFalsePositive (Choice)
│   IF ai_analysis.is_false_positive == true → SuppressFalsePositive
│   DEFAULT → IsSafeToAutoRemediate
│
├── SuppressFalsePositive (Pass) → EndFalsePositive (Succeed)
│
├── IsSafeToAutoRemediate (Choice)
│   IF ai_analysis.safe_to_auto_remediate == true → DetermineResourceType
│   DEFAULT → NotifyAdmin
│
├── DetermineResourceType (Choice)
│   IF resource_type contains "S3" → RemediateS3
│   IF resource_type contains "Iam" → RemediateIAM
│   IF resource_type contains "SecurityGroup" → RemediateVPC
│   DEFAULT → EndUnsupported (Succeed)
│
├── RemediateS3 (Task — Lambda)          ─┐
├── RemediateIAM (Task — Lambda)          ├── All: Timeout 90s, Retry 2x
├── RemediateVPC (Task — Lambda)         ─┘   Catch → HandleError
│   All Next: VerifyRemediation
│
├── NotifyAdmin (Task — Lambda, waitForTaskToken)
│   Heartbeat: 3600s | Timeout: 3660s
│   Catch: HeartbeatTimeout/Timeout → EndTimeout
│         States.ALL → HandleError
│   Next: RouteAdminDecision
│
├── RouteAdminDecision (Choice)
│   IF admin_decision == "APPROVED" → ExecuteApprovedPlaybook
│   IF admin_decision == "REJECTED" → EndRejected (Succeed)
│   IF admin_decision == "MANUAL" → EndManual (Succeed)
│   DEFAULT → HandleError
│
├── ExecuteApprovedPlaybook (Choice)
│   IF resource_type "S3" → ApprovedRemediateS3
│   IF resource_type "Iam" → ApprovedRemediateIAM
│   IF resource_type "SecurityGroup" → ApprovedRemediateVPC
│   DEFAULT → EndUnsupported
│
├── ApprovedRemediateS3 / IAM / VPC (Task — Lambda)
│   Same specs as auto path. Next: VerifyRemediation
│
├── VerifyRemediation (Task — Lambda)
│   Lambda: security-auto-verification
│   Timeout: 60s | Catch → HandleError
│   Next: EndSuccess
│
├── EndSuccess (Succeed)
├── EndRejected (Succeed)
├── EndManual (Succeed)
├── EndTimeout (Succeed)
├── EndFalsePositive (Succeed)
├── EndUnsupported (Succeed)
└── HandleError (Fail — error: "PipelineError")
```

---

## 9. AI Analysis Engine

### Architecture

The AI engine uses a **provider abstraction pattern** with a **model fallback chain**:

```
Request → get_provider(active_provider, api_key, active_model)
            ↓
         GeminiProvider or ClaudeProvider (both extend BaseAIProvider)
            ↓
         provider.analyze(prompt, max_tokens=600)
            ↓
         Fallback chain on 429/404:
         gemini-2.5-flash → gemini-2.0-flash → gemini-2.0-flash-lite
```

### The Prompt

The system prompt is carefully engineered for security analysis tasks:

```
AWS security analyst. Analyze finding and return JSON only.

CONTEXT: {infrastructure_context}   ← Live AWS resource state

FINDING: {finding_details}          ← Security Hub finding data

RULES (non-negotiable):
1. tag AutoRemediationExclude=true → safe_to_auto_remediate=false
2. tag Environment=Production → safe_to_auto_remediate=false
3. is_default_sg=true → safe_to_auto_remediate=false
4. tag ServiceAccount=true OR Role=CI-Pipeline → safe_to_auto_remediate=false
5. S3 website_hosting_enabled=true AND intentional_public_tag=true → is_false_positive=true
6. playbook must be one of: s3_remediation, iam_remediation, vpc_remediation, manual, none
7. No deletions. All actions reversible.

Return ONLY this JSON:
{"risk_level":"HIGH|MEDIUM|LOW","is_false_positive":bool,"analysis":"1-2 sentences",...}
```

### AI Response Schema

```json
{
  "risk_level": "HIGH",
  "is_false_positive": false,
  "false_positive_reason": null,
  "analysis": "SSH port 22 is exposed to the internet on a non-production security group, allowing brute-force attacks.",
  "safe_to_auto_remediate": true,
  "escalation_reason": null,
  "recommended_playbook": "vpc_remediation",
  "recommended_actions": [
    {
      "action_id": 1,
      "playbook": "vpc_remediation",
      "description": "Revoke inbound SSH rule allowing 0.0.0.0/0",
      "risk": "LOW",
      "reversible": true
    }
  ]
}
```

### Infrastructure Context Gathering

Before calling the AI, the Lambda gathers live resource state:

| Resource Type | AWS API Calls Made |
|---|---|
| S3 Bucket | `GetBucketTagging`, `GetBucketPublicAccessBlock`, `GetBucketWebsite`, `GetBucketPolicy` |
| IAM User | `ListUserTags`, `ListAccessKeys`, `GetAccessKeyLastUsed`, `ListAttachedUserPolicies` |
| Security Group | `DescribeSecurityGroups`, `DescribeNetworkInterfaces`, `DescribeInstances` |

**Why gather context before calling AI?** The AI can only make a good decision if it knows the current state. Without context, the AI might recommend auto-remediating a production resource or fail to identify an intentionally public S3 website. Live context transforms AI from pattern-matching to genuine situational awareness.

### Gemini API Configuration

```python
{
  "generationConfig": {
    "maxOutputTokens": 600,        # Enough for structured JSON response
    "temperature": 0.1,            # Near-deterministic — we want consistent analysis
    "topP": 0.8,
    "responseMimeType": "application/json",  # Forces JSON output
    "thinkingConfig": {"thinkingBudget": 0}  # Disables thinking tokens (gemini-2.5-flash)
  }
}
```

**Why `thinkingBudget: 0`?** Gemini 2.5 Flash is a reasoning model that uses internal "thinking tokens" before generating output. These thinking tokens count against `maxOutputTokens`. With a 600-token budget, the model would consume ~590 tokens on reasoning and only produce ~40 characters of actual JSON (too short — results in truncated, invalid JSON). Setting `thinkingBudget: 0` disables thinking and dedicates all 600 tokens to the JSON response.

---

## 10. Operations Dashboard

The dashboard is a complete single-page application served by the `security-auto-dashboard` Lambda. It provides:

### Key Features

**1. Live Findings Monitor**  
Real-time view of all security findings with status, severity badges, AI risk level, and timestamps. Click any finding to see full details including AI analysis, remediation actions, and runbook status.

**2. Pipeline Control**  
Toggle the EventBridge rule on/off. When OFF, Security Hub findings are not processed automatically (useful during deployments or maintenance).

**3. Simulation Lab (5 Scenarios)**

| Case | Scenario | Severity | Path |
|---|---|---|---|
| A1 | S3 Bucket — Public Access Open | HIGH | Auto-remediation |
| A2 | Security Group — SSH Open to World (port 22) | HIGH | Auto-remediation |
| A3 | Security Group — All Traffic Open | CRITICAL | Auto-remediation |
| B1 | IAM CI-Pipeline User — Active Access Keys | HIGH | Admin approval |
| B2 | Production Security Group — RDP Open (port 3389) | CRITICAL | Admin approval |

Each simulation creates a **real AWS resource** with the vulnerability, injects the finding directly into the pipeline (bypassing EventBridge), and demonstrates the full remediation flow.

**4. AI Runbook Generation & Apply**  
For any finding, generate a step-by-step AI remediation runbook. Preview the plan before executing. Apply inline (for S3/IAM/EC2) or get CLI commands for manual execution (for other resource types). Undo any applied runbook to restore the original state.

**5. Batch Remediation**  
Remediate all pending findings in one click. Uses AI to generate and apply runbooks with configurable retry logic. AI learns from failures — each retry feeds the failure logs back to the AI for improved accuracy.

**6. AI Provider Hot-Swap**  
Switch between Gemini and Claude at runtime without redeployment:
1. Open AI config modal
2. Paste a new API key
3. Validate — backend calls the provider's models list API
4. Select model
5. Save — new provider/model stored in DynamoDB and Secrets Manager
6. All subsequent AI calls use the new provider immediately

---

## 11. MTTR Reduction — Proof & Calculation

### What is MTTR?

**Mean Time to Remediate (MTTR)** = Average time from when a security finding is detected to when it is fully resolved and verified. It is a key security operations metric and a standard KPI used in SOC reporting and compliance frameworks (ISO 27001, SOC 2, NIST CSF).

### Baseline: Manual Process (Industry Average)

Based on published industry benchmarks (IBM Cost of a Data Breach 2024, Ponemon Institute):

| Step | Manual Time |
|---|---|
| Finding detected by Security Hub | 0 minutes (automatic) |
| Security engineer notified / sees alert | 30–60 minutes (typical on-call SLA) |
| Alert reviewed and triaged by engineer | 30–90 minutes |
| Remediation plan documented and approved | 60–120 minutes (change approval process) |
| Fix implemented by engineer | 15–60 minutes |
| Fix verified and ticket closed | 15–30 minutes |
| **Total MTTR (Manual)** | **~2.5 hours (optimistic) to 6 hours (typical)** |

For critical findings requiring change control: 8–24 hours.

### This System: Measured Execution Times

**Path A — Auto-Remediation:**

| Step | Time |
|---|---|
| EventBridge detects finding | < 5 seconds |
| Step Functions execution starts | < 1 second |
| AI analysis (Gemini API call) | 3–8 seconds |
| Remediation Lambda execution | 3–10 seconds |
| Verification Lambda execution | 2–5 seconds |
| Security Hub updated to RESOLVED | < 1 second |
| **Total MTTR (Auto Path)** | **~10–30 seconds** |

**Path B — Admin Approval (estimated, admin response dependent):**

| Step | Time |
|---|---|
| EventBridge to Step Functions | < 5 seconds |
| AI analysis | 3–8 seconds |
| Notification Lambda + SNS email | 5–15 seconds |
| Email delivered to admin inbox | 30–120 seconds |
| Admin reviews finding and AI analysis | 2–10 minutes |
| Admin clicks approval link | < 1 second |
| Approval Handler + Step Functions resume | 1–2 seconds |
| Approved remediation + verification | 5–15 seconds |
| **Total MTTR (Approval Path)** | **~5–15 minutes** |

### MTTR Reduction Summary

| Path | Manual MTTR | Automated MTTR | Reduction |
|---|---|---|---|
| Auto-remediation (Severity HIGH) | 4 hours | 30 seconds | **~99.8%** |
| Admin approval (Critical/Production) | 8 hours | 15 minutes | **~96.9%** |
| Weighted average (70% auto, 30% approval) | ~5 hours | ~5 minutes | **~98.3%** |

### Proof: Real Timing from Simulation

When running Simulation Case A2 (SSH Security Group open):

```
T+0:00  Simulation creates SG + calls sfn:StartExecution
T+0:02  Step Functions: ParseFinding → AIAnalysis state begins
T+0:07  Gemini API returns analysis (safe_to_auto_remediate: true)
T+0:08  DetermineResourceType → RemediateVPC state begins
T+0:10  VPC Lambda: describe_security_groups() → revoke_security_group_ingress()
T+0:12  VerifyRemediation Lambda: describe_security_groups() confirms rule removed
T+0:13  Security Hub: batch_update_findings() → RESOLVED
T+0:13  DynamoDB: status = RESOLVED

Total elapsed: 13 seconds
```

### Additional Security Benefits (Not Captured in MTTR)

- **Consistency:** Every S3 finding gets exactly the same remediation — no variation based on who is on call
- **24/7 Coverage:** System responds at 3AM without paging anyone
- **False Positive Detection:** AI prevents wasted effort on non-issues
- **Undo Capability:** Any mistake can be reversed instantly — unlike manual fixes
- **Audit Trail:** Every action logged with timestamps in DynamoDB and CloudWatch

---

## 12. How This Differs From Other Solutions

### vs. AWS Security Hub Native Remediation (AWS Config Auto-Remediation)

| Feature | AWS Config Auto-Remediation | This System |
|---|---|---|
| AI analysis | None | Full LLM analysis with context |
| False positive detection | None | AI + hardcoded guardrails |
| Production resource protection | Manual configuration per rule | Automatic tag-based guardrail |
| Admin approval workflow | None | waitForTaskToken pattern |
| Audit trail | CloudTrail only | DynamoDB + CloudWatch structured logs |
| Dashboard | AWS Console only | Custom web application |
| Runbook generation | None | AI-generated step-by-step |
| Multi-provider AI | N/A | Gemini + Claude hot-swappable |
| Cost | Config rules: ~$1/rule/month | ~$3–15/month total |

### vs. Commercial SOAR Platforms (Splunk SOAR, Pagerduty, Swimlane, Cortex XSOAR)

| Feature | Commercial SOAR | This System |
|---|---|---|
| Annual cost | $50,000–$500,000 | ~$50–180/year |
| Deployment | Vendor-managed SaaS or self-hosted server | Fully serverless, no servers |
| IaC support | Limited | 100% Terraform |
| AI integration | Plugin-based, additional cost | Native, built-in |
| AWS-native | Partial | 100% AWS-native |
| Setup time | Weeks to months | 1 hour (`quickdeploy.ps1`) |
| Customization | Limited by vendor | Full source code access |

### vs. Custom Lambda-Based Security Automation (Common DIY Approach)

| Feature | DIY Lambda Scripts | This System |
|---|---|---|
| Orchestration | None — scripts run independently | Step Functions state machine |
| Human approval | None | waitForTaskToken pattern |
| AI analysis | None | LLM-powered risk assessment |
| State management | None | DynamoDB with full lifecycle |
| Dashboard | None | Full web UI |
| Undo capability | None | Per-finding undo state |
| False positive handling | None | AI detection |
| IaC | Usually manual | 100% Terraform |

### Unique Differentiators

1. **AI-powered context awareness:** Not just pattern matching — the AI reads live resource state (tags, configurations, usage) before deciding
2. **Hot-swappable AI providers:** Switch Gemini ↔ Claude at runtime without any code deployment
3. **Hardcoded safety guardrails:** Even if the AI says "safe to auto-remediate," hardcoded rules block action on production-tagged and CI-pipeline resources
4. **Reversible actions only:** No deletions. Every remediation can be undone from the dashboard
5. **Simulation Lab:** Test the entire pipeline end-to-end with real AWS resources, safely

---

## 13. Security & Safety Guardrails

### Layered Defense Model

The system implements security at multiple layers to ensure no finding is incorrectly auto-remediated:

**Layer 1 — AI Analysis (Contextual)**
The AI reads live resource state and decides based on context. A security group in a production VPC is treated differently than one in a dev account.

**Layer 2 — Hardcoded Guardrails (Code-Level, Cannot Be Bypassed by AI)**

| Tag/Condition | Enforced Action |
|---|---|
| `AutoRemediationExclude=true` | Force `safe_to_auto_remediate=false` |
| `Environment=Production` | Force `safe_to_auto_remediate=false` |
| Default VPC Security Group (`is_default_sg=true`) | Force `safe_to_auto_remediate=false` |
| `ServiceAccount=true` or `Role=CI-Pipeline` | Force `safe_to_auto_remediate=false` |
| S3 with `website_hosting_enabled=true` AND `PublicAccess=Intentional` | Force `is_false_positive=true` |

These are applied in `response_validator.py` **after** the AI responds. The AI cannot override them — they are unconditional code-level checks.

**Layer 3 — Dashboard Toggles (Runtime Override)**

| Toggle | Effect |
|---|---|
| `auto_remediation=false` | ALL findings go to admin approval — AI recommendation ignored |
| `ai_analysis_enabled=false` | AI call skipped entirely — keyword-based routing only |

**Layer 4 — Reversibility**
Every remediation function preserves undo state in DynamoDB:
- S3: Original public access block configuration captured before modification
- VPC: Exact revoked SG rules stored as JSON
- IAM: Access key IDs that were deactivated stored for re-enablement

**Layer 5 — IAM Least Privilege**
Each Lambda has its own IAM role with only the permissions it needs. For example:
- `LambdaAIAnalyzerRole`: Can only READ resource context (GetBucketTagging, DescribeSecurityGroups, etc.) + read Secrets Manager — cannot modify anything
- `LambdaRemediationRole`: Can only modify the specific resources it remediates — cannot read Secrets Manager or invoke other Lambdas
- `LambdaApprovalRole`: Can only call `sfn:SendTaskSuccess/Failure` — cannot read findings or modify resources

---

## 14. Rough Architecture Diagram — For Whiteboard Interviews

### How to Draw This in 5 Minutes

Practice drawing the following in this sequence. Use boxes for services and arrows for flows.

```
STEP 1: Draw the main pipeline (left to right)

[Security Hub] --finding--> [EventBridge] --start_execution--> [Step Functions]


STEP 2: Expand Step Functions into decision flow (top to bottom inside the box)

[Step Functions]
  |
  |--> [AI Lambda] --> calls Gemini/Claude API (external cloud)
  |       |
  |    returns analysis
  |       |
  +-- False Positive? --(yes)--> END (suppress)
  |
  +-- Safe to Auto? --(no)---> [Notification Lambda] --> [SNS] --> Admin email
  |                                                                    |
  |                                                              clicks link
  |                                                                    |
  |                                                          [API Gateway]
  |                                                                    |
  |                                                         [Approval Lambda]
  |                                                                    |
  |                                                    sfn.send_task_success()
  |                                                                    |
  |                                                         <Step Functions resumes>
  |
  +-- Safe to Auto? --(yes)-> [S3 / IAM / VPC Lambda] --> [Verify Lambda] --> END

STEP 3: Add DynamoDB (persistent storage - draw below the main flow)

[DynamoDB: findings]   [DynamoDB: settings]

Draw arrows: Notification Lambda --write--> findings
             Remediation Lambdas --write--> findings
             Verification Lambda --update--> findings
             Dashboard Lambda --read/write--> both tables

STEP 4: Add the Dashboard (separate box at the bottom)

[Browser] --> [API Gateway] --> [Dashboard Lambda]
                                     |
                          +--> DynamoDB (read/write)
                          +--> Step Functions (start execution / send_task)
                          +--> EventBridge (enable/disable rule)
                          +--> Secrets Manager (AI key management)
                          +--> Gemini/Claude (direct AI calls)

STEP 5: Add Secrets Manager and CloudWatch (floating)

[Secrets Manager] <-- AI Analyzer Lambda reads API key
[CloudWatch Logs] <-- all Lambdas + Step Functions write logs
```

### Simplified Box Diagram (Suitable for Whiteboard)

```
┌──────────────────────────────────────────────────────────────────┐
│                    AWS Region: us-east-1                         │
│                                                                  │
│  [Security Hub] → [EventBridge] → [Step Functions]              │
│                                         │                        │
│                          ┌──────────────┤                        │
│                          ▼              ▼                        │
│                    [AI Analyzer]    FALSE POSITIVE?              │
│                     ↕ Gemini       YES → END (suppress)         │
│                     ↕ Claude             │                       │
│                          │          SAFE AUTO?                   │
│                          │         YES ↓    NO ↓                │
│                     ┌────┘    ┌──────────┐ ┌──────────────────┐ │
│                     │        │ Remediate │ │ Notification     │ │
│                     │        │  S3/IAM/  │ │  Lambda → SNS    │ │
│                     │        │   VPC     │ │  → Email → Admin │ │
│                     │        └──────┬────┘ └──────┬───────────┘ │
│                     │               │             │ (clicks link)│
│                     │        [Verify Lambda]  [API Gateway]      │
│                     │               │             │              │
│                     │          RESOLVED      [Approval Handler]  │
│                     │                             │              │
│                     │                     sfn.send_task_success()│
│                     │                    (Step Functions resumes) │
│                     │                                            │
│  ──────────────────────────────────────────────────────────────  │
│  [Browser] → [API GW] → [Dashboard Lambda]                       │
│                               ↕ DynamoDB (findings + settings)   │
│  ──────────────────────────────────────────────────────────────  │
│  Data: [DynamoDB ×2]  [Secrets Manager]  [CloudWatch Logs]      │
└──────────────────────────────────────────────────────────────────┘
                      ↕ External: [Gemini API] [Claude API]
```

---

## 15. Interview Preparation — Architecture Walkthrough

### How to Introduce This Project (30-Second Elevator Pitch)

> "I built a fully serverless, AI-powered security automation platform on AWS. It ingests security findings from AWS Security Hub, uses a large language model to assess risk and detect false positives, then either auto-remediates the issue or routes it to an admin for approval — reducing our mean time to remediate from hours to under a minute. The entire infrastructure is defined in Terraform and costs about $10 a month."

### How to Walk Through the Architecture (3-5 Minutes)

**Opening:**
> "The system has three main layers. At the top is the event-driven pipeline triggered by Security Hub. In the middle is the AI analysis and decision engine orchestrated by Step Functions. At the bottom is a web dashboard for human oversight and control."

**Layer 1 — Trigger:**
> "When AWS Security Hub flags a compliance failure — for example, a public S3 bucket or an SSH port open to the internet — EventBridge picks up the event and starts a Step Functions execution. I chose EventBridge because it has a native integration with Security Hub, it filters events server-side so we only process relevant findings, and it decouples the trigger from the processing logic."

**Layer 2 — Orchestration:**
> "Step Functions orchestrates the entire workflow as a state machine. I chose Step Functions over Lambda chains or SQS because it gives me visual execution history, built-in retry logic, conditional branching, and critically — the waitForTaskToken pattern which lets the workflow pause for up to an hour while waiting for a human to make a decision."

**Layer 3 — AI Analysis:**
> "The first thing Step Functions does is invoke the AI Analyzer Lambda. This Lambda gathers live infrastructure context from AWS — it reads the bucket's public access settings, the IAM user's tags, the security group rules — and passes all of this to Gemini, along with the finding. The AI returns a structured JSON response saying: what's the risk level, is this a false positive, is it safe to auto-remediate."

**Layer 4 — Decision Routing:**
> "Based on the AI response, the state machine takes one of three paths: suppress a false positive, auto-remediate using one of three remediation Lambdas, or escalate to a human admin via an approval workflow. Production-tagged resources and CI pipeline users are always escalated regardless of what the AI says — that's a hardcoded guardrail."

**Layer 5 — Notification & Approval:**
> "For the escalation path, the Notification Lambda stores the finding in DynamoDB with the Step Functions task token embedded in it, then sends an email via SNS with three clickable links: approve, reject, or mark manual. When the admin clicks a link, API Gateway routes to the Approval Handler Lambda which calls sfn.SendTaskSuccess with the admin's decision. Step Functions resumes and executes the approved remediation."

**Layer 6 — Verification:**
> "After any remediation — auto or approved — a Verification Lambda confirms the fix was actually applied by re-reading the resource state. It then writes RESOLVED to Security Hub and DynamoDB."

**Dashboard:**
> "Finally, the Operations Dashboard is a serverless web app served by a single Lambda function. It shows all findings in real time, lets you toggle settings, run simulations, generate AI runbooks, and even swap the AI provider from Gemini to Claude without touching any code."

---

## 16. Interview Q&A — All Questions & Answers

### Architecture & Design Questions

**Q: Why did you use Step Functions instead of Lambda chaining?**
> Lambda chaining — where Lambda A invokes Lambda B synchronously — creates tight coupling, makes error handling complex, and provides zero visibility into execution state. Step Functions gives me a visual state machine, built-in retry/backoff, conditional branching, durable execution history, and most importantly the waitForTaskToken pattern which is impossible to implement cleanly with Lambda chaining. If any Lambda fails, the execution history tells me exactly which state failed and what the input was.

**Q: Explain the waitForTaskToken pattern.**
> waitForTaskToken is a Step Functions pattern for human-in-the-loop workflows. When Step Functions invokes the Notification Lambda, it passes a special one-time token called a task token in the payload. The Lambda stores this token in DynamoDB and sends it (URL-encoded) in the admin email links. Step Functions then PAUSES — it doesn't timeout, doesn't retry, it literally waits. When the admin clicks a link, the Approval Handler Lambda extracts the token and calls sfn.SendTaskSuccess with the admin's decision. Step Functions immediately resumes from where it paused. This is elegant because the paused execution costs nothing — you only pay for active execution.

**Q: Why DynamoDB and not RDS/PostgreSQL?**
> This workload has three characteristics that make DynamoDB the right choice: First, the schema is variable — an S3 finding has different fields than an IAM finding, and DynamoDB's schemaless nature handles this naturally. Second, the access pattern is simple key-value lookups by finding_id with occasional GSI queries by status — no JOINs required. Third, the workload is bursty — you might get 100 findings in five minutes then nothing for hours — and DynamoDB on-demand billing means you only pay for actual reads and writes. RDS would require provisioning instance size for peak load and paying for it 24/7.

**Q: Why is the EventBridge rule disabled by default?**
> Safety. When you first deploy infrastructure with Terraform, the last thing you want is the system immediately starting to auto-remediate resources based on Security Hub findings that might be pre-existing false positives or known issues in your environment. Disabling the rule by default gives the operator time to validate the deployment, run simulations, and ensure the system is working as expected before turning on real-world automation. The operator explicitly enables it via the dashboard when they're ready.

**Q: How does the AI provider hot-swap work without redeployment?**
> The AI provider and model are stored in DynamoDB's settings table, not as Lambda environment variables. The AI Analyzer Lambda reads these settings from DynamoDB at the START of every invocation — not at cold start. This means any change to the DynamoDB settings takes effect on the very next Lambda invocation. The API key is stored in Secrets Manager and is also read at invocation time. So changing provider from Gemini to Claude takes effect within seconds of clicking Save on the dashboard, with no Lambda update or deployment required.

**Q: How do you handle the case where the Gemini API is down?**
> Three layers of fallback: First, the model fallback chain — if gemini-2.5-flash returns 429 or 404, it automatically tries gemini-2.0-flash, then gemini-2.0-flash-lite. Second, the provider fallback — the admin can switch to Claude via the dashboard. Third, the keyword-based fallback in ai_analyzer.py — if all AI calls fail, the Lambda inspects the finding title for known keywords (e.g., "CI-Pipeline" → escalate to admin, "S3 public" → auto-remediate) and makes a safe decision. The pipeline never stalls due to an AI outage.

**Q: What happens if a Lambda function times out mid-remediation?**
> Step Functions handles this through its retry and catch configuration. Each task state has a retry policy: Lambda.ServiceException and Lambda.TooManyRequestsException are retried up to 2 times with 5-second intervals and 2x exponential backoff. If all retries fail, the Catch block routes execution to the HandleError state (a Fail state). The DynamoDB finding record may be partially written, but since each Lambda writes to DynamoDB atomically at its start, the finding remains in PENDING_APPROVAL or AUTO_REMEDIATED until manually cleaned up. The execution history in Step Functions shows exactly what failed and why.

**Q: How do you prevent the system from breaking production?**
> Four layers: (1) Hardcoded guardrail — if a resource has `Environment=Production` tag, `safe_to_auto_remediate` is forced to false regardless of AI recommendation. (2) The AI is given the live resource tags as context and is instructed never to auto-remediate production resources. (3) The `auto_remediation` toggle in the dashboard can disable all auto-remediation globally. (4) Every remediation is reversible — the runbook system captures pre-remediation state and can undo any change with one click.

**Q: How does IAM least privilege work in this system?**
> Each Lambda has its own IAM role with only the exact permissions it needs. For example: the AI Analyzer Lambda can only READ resource state (get_bucket_tagging, describe_security_groups) and read from Secrets Manager. It cannot write to DynamoDB, cannot invoke other Lambdas, and cannot modify any resources. The Remediation Lambda can write to S3, IAM, and EC2 — but cannot read the AI API key or invoke the notification Lambda. The Approval Handler can only call sfn:SendTaskSuccess and sfn:SendTaskFailure. This way, even if one Lambda were compromised, the blast radius is limited to exactly what that function needs to do.

**Q: What are the security risks of sending task tokens in email links?**
> The task token is a cryptographically random, one-time-use identifier generated by Step Functions. It is opaque and unpredictable — there is no way to guess or enumerate valid tokens. The token is valid only for the duration of the Step Functions execution (up to 1 hour). If the execution times out, the token is invalid. The URL encoding prevents special characters from being mangled in email clients. The main risk is email interception — for higher security environments, this could be mitigated by requiring re-authentication before the approval endpoint accepts the request.

**Q: How would you scale this to handle 10,000 findings per day?**
> The architecture is already horizontally scalable: Lambda auto-scales to 1000 concurrent executions by default, Step Functions supports 1 million standard workflow executions per month, and DynamoDB on-demand scales to millions of requests. The only bottlenecks to address at scale: (1) Gemini/Claude API rate limits — mitigated by model fallback, SQS buffering, or batch processing; (2) Lambda concurrency limits — request a limit increase from AWS; (3) DynamoDB throughput — on-demand mode handles this automatically. No architectural changes are needed, just limit increases.

**Q: Walk me through the simulation flow.**
> When I click "Run Simulation — A2 (SSH SG)" in the dashboard: (1) The Dashboard Lambda calls ec2:CreateSecurityGroup in my AWS account; (2) It calls ec2:AuthorizeSecurityGroupIngress to add a rule allowing TCP:22 from 0.0.0.0/0; (3) It constructs a fake Security Hub finding JSON for this resource; (4) It calls sfn:StartExecution directly with this finding JSON — bypassing EventBridge entirely; (5) The full Step Functions pipeline runs: AI analyzes the real SG rules, determines it's safe to auto-remediate, VPC Lambda revokes the rule, Verification Lambda confirms it's gone. The entire flow takes about 15 seconds and uses real AWS resources to demonstrate the real remediation.

**Q: How do you handle concurrent findings for the same resource?**
> Currently, there is no deduplication at the EventBridge or Step Functions level — multiple executions could attempt to remediate the same resource simultaneously. In practice, this is benign because all remediation operations are idempotent (calling put_bucket_public_access_block twice has the same effect as calling it once). For future improvement, I would add a DynamoDB conditional write check at the start of each remediation Lambda — if the finding is already in AUTO_REMEDIATED or RESOLVED status, skip the remediation. This prevents duplicate DynamoDB writes and redundant AWS API calls.

**Q: Why store the Step Functions task token in DynamoDB?**
> Two reasons: (1) The Dashboard's manual action feature — an admin can approve/reject a finding directly from the dashboard UI without using the email link. The dashboard reads the task_token from DynamoDB and calls sfn:SendTaskSuccess on behalf of the admin. Without storing the token in DynamoDB, this workflow would be impossible. (2) Resilience — if the Notification Lambda crashes after sending the email but before the admin responds, the token is preserved in DynamoDB and the approval workflow can still complete.

**Q: How much does this system cost?**
> At typical load (100 findings/day): Lambda: ~$0.02/month. Step Functions: ~$1/month (standard workflow at $0.025 per 1,000 state transitions). DynamoDB on-demand: ~$0.50/month. API Gateway: ~$0.10/month. Secrets Manager: $0.40/month (1 secret). CloudWatch Logs: ~$0.50/month (ingest + storage). SNS: ~$0.00 (email notifications are free up to 1,000). Total: **~$3–5/month**. The Gemini API free tier (1,000 requests/day) covers typical usage at no additional cost.

**Q: What's the difference between the runbook feature and the Step Functions remediation?**
> The Step Functions path handles the automated pipeline (detection → AI analysis → remediation → verification). It uses pre-written remediation code (put_bucket_public_access_block, revoke_security_group_ingress, etc.) for the three supported resource types. The runbook feature is a dashboard-level feature for on-demand remediation of ANY finding, including unsupported resource types. The AI generates a step-by-step remediation plan based on the live resource state, then either executes it inline (for S3/IAM/EC2) or presents it as advisory CLI commands for the admin to run manually (for DynamoDB, RDS, etc.).

**Q: What testing have you done?**
> (1) Simulation Lab — runs end-to-end integration tests using real AWS resources and real API calls; (2) The five simulation scenarios cover all three resource types (S3, IAM, SG) and both execution paths (auto + approval); (3) Error path testing — simulating AI API failures to verify fallback behavior; (4) Manual state machine testing — using the dashboard to manually approve/reject findings and verify the Step Functions callback; (5) Terraform validate in CI/CD — GitHub Actions runs `terraform validate` on every pull request.

### Scenario-Based Questions

**Q: A finding comes in at 3AM for a critical S3 bucket with public access. Walk me through exactly what happens.**

> 1. Security Hub flags the finding (CRITICAL, FAILED, NEW).
> 2. EventBridge matches it and calls sfn:StartExecution — this happens within seconds, no human involved.
> 3. Step Functions starts. ParseFinding extracts the details.
> 4. AI Analyzer runs. It reads the bucket's tags — no Environment=Production, no AutoRemediationExclude. It reads the bucket's website hosting — not enabled. It calls Gemini: "This is a CRITICAL S3 bucket with public access and no protective tags. Risk: HIGH. Safe to auto-remediate: YES."
> 5. IsFalsePositive: NO. IsSafeToAutoRemediate: YES. DetermineResourceType: S3. → RemediateS3.
> 6. S3 Remediation Lambda: calls put_bucket_public_access_block (all 4 flags True) + put_bucket_acl (private). DynamoDB: AUTO_REMEDIATED.
> 7. Verification Lambda confirms all four flags are True. Security Hub updated to RESOLVED. DynamoDB: RESOLVED.
> 8. Total elapsed: ~30 seconds. No human was paged. No one woke up.

**Q: What if that bucket is actually hosting a public website intentionally?**

> This is exactly the false positive scenario. If the bucket has both `website_hosting_enabled=true` AND a tag `PublicAccess=Intentional`, the AI Analyzer will detect this from the infrastructure context. In the system prompt, rule #5 states: "S3 website hosting enabled AND intentional_public_tag=true → is_false_positive=true." The AI returns is_false_positive=true. Step Functions routes to SuppressFalsePositive → EndFalsePositive. The bucket is not touched. Additionally, the hardcoded override in response_validator.py enforces this regardless of any other AI response.

**Q: The admin receives an approval email but the link doesn't work — what could be wrong?**

> Most likely causes: (1) The Step Functions execution already timed out (heartbeat timeout: 1 hour) — the task token expired and sfn:SendTaskSuccess returns ResourceNotFound; (2) The admin already acted on a previous email for the same finding; (3) URL encoding issue in the email client mangling the token parameter. The Approval Handler Lambda returns a clear HTML error page in each case. The admin can use the Dashboard as a fallback — the Dashboard reads the task_token from DynamoDB and can send the callback from the UI.

---

## 17. Dependencies & Failure Mitigation

### Dependency Map & Failure Scenarios

| Dependency | Failure Impact | Mitigation |
|---|---|---|
| **EventBridge** | No new findings trigger pipeline | EventBridge has 99.99% SLA. Fallback: Dashboard simulate endpoint can manually inject findings into Step Functions bypassing EventBridge |
| **Step Functions** | No orchestration | 99.95% SLA. Manual remediation via Dashboard runbook feature. Findings can still be stored and reviewed |
| **Gemini API (primary)** | No AI analysis | Three-tier mitigation: (1) Model fallback chain: gemini-2.5-flash → gemini-2.0-flash → gemini-2.0-flash-lite; (2) Switch to Claude via Dashboard hot-swap; (3) Keyword-based fallback in code — pipeline never stalls |
| **Claude API (alternate)** | AI analysis via Gemini only | Gemini takes over; no code change needed |
| **Secrets Manager** | AI API key unavailable | Secrets Manager has 99.99% SLA. Mitigation: Lambda retries on ClientError. Findings fall back to keyword routing |
| **DynamoDB** | Findings not persisted | DynamoDB SLA 99.99% with multi-AZ replication. Mitigation: CloudWatch Logs capture all finding details independently |
| **SNS Email delivery** | Admin not notified | Retry policy on SNS (3 retries over 20 min). Mitigation: Dashboard shows all PENDING_APPROVAL findings — admin can act from dashboard without email |
| **API Gateway** | Approval links + dashboard inaccessible | 99.95% SLA. Mitigation: Dashboard fallback via direct Lambda invocation if needed |
| **Lambda cold start** | First invocation has ~200ms extra latency | Negligible impact for async pipelines. Mitigation: Provisioned concurrency for dashboard Lambda if sub-100ms response required |
| **Internet connectivity from Lambda** | Gemini/Claude unreachable | Lambda runs in AWS public subnet with internet access by default. Mitigation: Keyword-based fallback. For VPC deployment: NAT Gateway required |
| **AWS Security Hub** | No findings generated | Upstream source dependency. Mitigation: Simulation Lab allows pipeline testing independent of Security Hub |

### Circuit Breaker Pattern

The system implements a software circuit breaker in the AI Analyzer Lambda:

```
Call Gemini → Success? → Return result
           → Failure (429/404)? → Try next model in chain
           → All models fail? → Try Claude (if configured)
           → Claude fails? → Keyword-based routing (never fails)
```

This ensures the pipeline always produces an output, even under complete AI provider outage.

### Data Durability

- **DynamoDB:** Multi-AZ by default, point-in-time recovery available, 30-day TTL
- **CloudWatch Logs:** Independent of DynamoDB — all finding details logged even if DynamoDB write fails
- **Secrets Manager:** Multi-AZ, 99.99% SLA
- **Findings at risk:** Between EventBridge trigger and DynamoDB write (~10 seconds window), a finding could be lost if Step Functions fails catastrophically. This is acceptable for security monitoring — the finding will re-appear in Security Hub on the next evaluation cycle

---

## 18. Monitoring & Observability

### CloudWatch Log Structure

Every Lambda emits structured JSON:

```json
{
  "event_type": "AI_ANALYSIS_COMPLETE",
  "timestamp": "2025-06-14T10:30:45Z",
  "finding_id": "sim-a2-12345",
  "resource_type": "AwsEc2SecurityGroup",
  "resource_id": "sg-0abc123",
  "severity": "HIGH",
  "ai_risk_level": "HIGH",
  "ai_safe_to_auto": true,
  "duration_ms": 4230,
  "model_used": "gemini-2.5-flash",
  "provider_used": "gemini"
}
```

### What to Monitor (Operational Runbook)

| Metric | Alert Threshold | Action |
|---|---|---|
| AI Lambda error rate | > 5% in 5 min | Check Gemini API status; verify Secrets Manager |
| Step Functions execution failures | > 0 in 1 hour | Check HandleError state in execution history |
| Remediation Lambda failures | > 0 | Check IAM permissions; verify resource accessibility |
| DynamoDB throttling | > 0 | Switch to provisioned capacity mode |
| PENDING_APPROVAL findings older than 2 hours | Any | Admin may not have received email — check SNS |
| Gemini fallback model used | High frequency | Primary model quota exhausted; rotate API key |

### Step Functions Execution Dashboard

Step Functions provides a built-in visual execution dashboard:
- Every execution shows which state it's in
- Full input/output for each state
- Execution history searchable by date, status
- Direct link to CloudWatch logs for failed states

---

## 19. Cost Analysis

### Monthly Cost Estimate (100 Findings/Day)

| Service | Usage | Cost |
|---|---|---|
| Lambda | 100 findings × 8 Lambda invocations × 1 second avg × $0.0000166667/GB-second × 128MB | ~$0.02 |
| Step Functions | 100 × 30 state transitions/execution × $0.025/1000 | ~$0.075 |
| DynamoDB | 100 writes/day × 30 days = 3,000 × $0.00000025/write | ~$0.001 |
| API Gateway | 100 dashboard hits/day × $3.50/million | ~$0.01 |
| Secrets Manager | 1 secret × $0.40/month | $0.40 |
| CloudWatch Logs | ~100 MB/day ingestion × $0.50/GB | ~$1.50 |
| SNS | Email notifications (free tier) | $0.00 |
| Gemini API | Free tier: 1,000 requests/day | $0.00 |
| EventBridge | 100 events × $1.00/million | ~$0.01 |
| **Total** | | **~$2–5/month** |

### Cost Optimization Tips

- CloudWatch Log retention set to 30 days (vs. default indefinite) saves ~80% on log storage
- DynamoDB TTL auto-deletes old findings — no manual cleanup cost
- Gemini free tier covers ~1,000 AI calls/day — switch to Claude only if exceeding free limits
- Lambda right-sizing: AI Analyzer uses 256 MB (needs memory for boto3); Remediation Lambdas use 128 MB (simple single-operation functions)

---

## 20. Future Scope & Improvements

### Short-Term Improvements (1–3 Months)

**1. Finding Deduplication**  
Add a DynamoDB conditional write at Step Functions start to check if a finding_id is already being processed. Prevents duplicate remediations for the same resource when Security Hub emits repeat findings.

**2. Slack/Teams Integration**  
Replace or supplement SNS email notifications with Slack message to a security channel. Slash commands (`/approve <finding_id>`) for in-Slack approval. Much faster admin response time.

**3. SQS Buffer for High-Volume Scenarios**  
Add an SQS queue between EventBridge and Step Functions with a Lambda consumer. This allows rate-limiting Step Functions executions (e.g., max 10 concurrent) to stay within Gemini API rate limits during large-scale finding spikes.

**4. Multi-Account Support**  
Current system operates in a single AWS account. Extend to cross-account remediation using IAM role assumption — the remediation Lambdas assume a role in the target account to perform fixes. Requires updating EventBridge to receive findings from AWS Organizations Security Hub aggregator.

**5. Security Hub Custom Action Integration**  
Add a Security Hub Custom Action that triggers the pipeline on-demand for any finding — allowing security engineers to push specific findings through the AI analysis pipeline manually from the Security Hub console.

### Medium-Term Improvements (3–6 Months)

**6. Response Schema with AI**  
Add `responseSchema` to the Gemini API request alongside `responseMimeType: "application/json"` for stricter JSON structure enforcement, reducing response validation failures.

**7. More Resource Types**  
Extend remediation to cover:
- RDS instances with public access
- Lambda functions with overly permissive resource policies
- CloudTrail disabled findings
- KMS key rotation disabled findings
- MFA not enabled on root account

**8. Metrics Dashboard in CloudWatch**  
Auto-provision a CloudWatch dashboard with graphs for:
- MTTR by severity level (tracked over time)
- Auto-remediation vs. approval rate
- False positive rate by resource type
- Gemini vs. Claude API latency

**9. Scheduled Compliance Sweep**  
Add an EventBridge scheduled rule (daily at midnight) that queries Security Hub for all FAILED findings older than 24 hours and re-runs them through the pipeline. This catches findings that were missed or failed processing.

**10. Runbook Library**  
Build a library of pre-approved runbooks for common finding types. Instead of calling the AI every time, retrieve the pre-approved runbook for known findings (S3 public access → always block access). Use AI only for novel or unusual findings.

### Long-Term Vision (6–12 Months)

**11. Multi-Cloud Extension**  
Extend to Azure Security Center and GCP Security Command Center using the same pipeline design. The AI analysis layer is cloud-agnostic; only the remediation Lambdas need cloud-specific implementations.

**12. Threat Intelligence Integration**  
Feed threat intelligence feeds (IP reputation, known malicious patterns) into the AI context. An IAM key that's been used from a known-malicious IP should be treated as CRITICAL and automatically deactivated even if the finding would normally be LOW risk.

**13. Remediation Verification via AWS Config**  
After remediation, subscribe to AWS Config change events to independently verify that the configuration drift was corrected. This provides a second, independent verification path beyond the current Lambda-based check.

**14. ML-Based False Positive Learning**  
Log all AI analysis decisions and human override decisions to a training dataset. Periodically fine-tune the AI model on your organization's specific resources and tagging conventions to improve false positive detection accuracy over time.

---

## 21. Appendix — Reference Tables

### A. Lambda Function Specifications

| Function Name | Memory | Timeout | Role |
|---|---|---|---|
| security-auto-ai-analyzer | 256 MB | 60s | LambdaAIAnalyzerRole |
| security-auto-dashboard | 256 MB | 30s | LambdaDashboardRole |
| security-auto-s3-remediation | 128 MB | 60s | LambdaRemediationRole |
| security-auto-iam-remediation | 128 MB | 60s | LambdaRemediationRole |
| security-auto-vpc-remediation | 128 MB | 60s | LambdaRemediationRole |
| security-auto-verification | 128 MB | 60s | LambdaVerificationRole |
| security-auto-notification | 128 MB | 30s | LambdaNotificationRole |
| security-auto-approval-handler | 128 MB | 10s | LambdaApprovalRole |

### B. IAM Role Summary

| Role | Assigned To | Key Permissions |
|---|---|---|
| StepFunctionsRole | Step Functions | lambda:InvokeFunction on security-auto-* |
| LambdaAIAnalyzerRole | ai-analyzer | GetBucketTagging, DescribeSecurityGroups, GetSecretValue (read-only) |
| LambdaRemediationRole | s3/iam/vpc Lambda (×3) | PutBucketPublicAccessBlock, UpdateAccessKey, RevokeSecurityGroupIngress, DynamoDB PutItem |
| LambdaVerificationRole | verification | GetBucketPublicAccessBlock, ListAccessKeys, DescribeSecurityGroups, BatchUpdateFindings, DynamoDB UpdateItem |
| LambdaNotificationRole | notification | SNS Publish, DynamoDB GetItem/PutItem/UpdateItem |
| LambdaDashboardRole | dashboard | DynamoDB CRUD, SFN StartExecution/SendTask, EventBridge Enable/Disable, SecretsManager Get/Put, S3/IAM/EC2 (simulation + runbook) |
| LambdaApprovalRole | approval-handler | SFN SendTaskSuccess/Failure |
| EventBridgeRole | EventBridge rule | SFN StartExecution |

### C. DynamoDB Schema — Findings Table

| Attribute | Type | Description |
|---|---|---|
| finding_id | String (PK) | Unique finding identifier |
| resource_type | String | e.g., AwsS3Bucket, AwsEc2SecurityGroup |
| resource_id | String | ARN or ID of affected resource |
| severity | String | CRITICAL, HIGH, MEDIUM, LOW |
| title | String | Human-readable finding title |
| description | String | Detailed finding description |
| ai_analysis | String (JSON) | Full AI analysis object |
| recommended_actions | String (JSON) | Array of recommended actions |
| risk_level | String | AI-assigned risk level |
| status | String | Current finding status |
| task_token | String | Step Functions callback token |
| created_at | String | ISO 8601 timestamp |
| updated_at | String | ISO 8601 timestamp |
| ttl_epoch | Number | Unix epoch for DynamoDB TTL (30 days) |
| runbook | String (JSON) | Generated remediation runbook |
| runbook_status | String | READY, APPLIED, ADVISORY, UNDONE |
| runbook_logs | String (JSON) | Execution log entries |
| undo_data | String (JSON) | Pre-remediation state for undo |
| environment | String | Environment tag from resource |
| action_taken | String | Description of action performed |

### D. Dashboard API Routes

| Method | Path | Purpose |
|---|---|---|
| GET | /dashboard | Serve HTML dashboard UI |
| GET | /dashboard/api/findings | List all findings |
| DELETE | /dashboard/api/findings | Clear all findings |
| GET | /dashboard/api/settings | Get toggle settings |
| PUT | /dashboard/api/settings | Update toggle settings |
| GET | /dashboard/api/control | Get pipeline status |
| POST | /dashboard/api/control | Enable/disable/terminate pipeline |
| POST | /dashboard/api/action | Approve/reject finding from dashboard |
| POST | /dashboard/api/email | Resend notification email |
| GET | /dashboard/api/ai-config | Get current AI provider/model |
| PUT | /dashboard/api/ai-config | Update AI provider/model/key |
| POST | /dashboard/api/ai-models | Validate API key + list models |
| POST | /dashboard/api/simulate | Create simulation + start pipeline |
| DELETE | /dashboard/api/simulate | Delete simulation resource |
| POST | /dashboard/api/ai-runbook | Generate AI remediation runbook |
| POST | /dashboard/api/apply-runbook | Execute inline runbook |
| POST | /dashboard/api/undo-runbook | Reverse inline runbook |
| GET | /dashboard/api/remediate-all | Get batch remediation status |
| POST | /dashboard/api/remediate-all | Start batch remediation |

### E. Simulation Cases Reference

| Case | Resource Created | Vulnerability | Severity | Routing |
|---|---|---|---|---|
| A1 | S3 bucket | Block public access disabled | HIGH | Auto-remediation |
| A2 | Security Group | TCP:22 (SSH) from 0.0.0.0/0 | HIGH | Auto-remediation |
| A3 | Security Group | All traffic (-1) from 0.0.0.0/0 | CRITICAL | Auto-remediation |
| B1 | IAM User (tag: Role=CI-Pipeline) | Active access keys on CI user | HIGH | Admin approval |
| B2 | Security Group (tag: Environment=Production) | TCP:3389 (RDP) from 0.0.0.0/0 | CRITICAL | Admin approval |

### F. Finding Status Reference

| Status | Meaning | Set By |
|---|---|---|
| PENDING_APPROVAL | Waiting for admin decision | notification Lambda |
| AUTO_REMEDIATED | Auto-fix applied, pending verification | remediation Lambda |
| APPROVED | Admin approved, fix executing | approval-handler Lambda |
| REJECTED | Admin rejected, no action taken | approval-handler Lambda |
| RESOLVED | Verified fixed | verification Lambda |
| MANUAL_REVIEW | Admin marked for manual handling | approval-handler Lambda |
| FALSE_POSITIVE | AI determined non-issue | ai-analyzer Lambda (via fallback) |
| FAILED | Remediation encountered an error | remediation Lambda |

---

*Documentation last updated: May 2026*  
*Architecture diagram version: v2 (ChatGPT-generated, verified accurate)*  
*GitHub: https://github.com/CynicPoet/aws-security-automation*
