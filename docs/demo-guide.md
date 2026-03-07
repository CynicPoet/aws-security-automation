# Demo Guide

## Prerequisites

- Stack deployed via `.\scripts\quickdeploy.ps1`
- SNS subscription confirmed (check admin email inbox, click "Confirm subscription")
- Dashboard open in browser (URL printed at end of quickdeploy)

---

## Deploying

```powershell
# Copy and fill in your credentials
copy scripts\config.ps1.example scripts\config.ps1
# Edit config.ps1: add AWS keys, region, admin email, Gemini/Claude API key

.\scripts\quickdeploy.ps1
```

The script runs 6 steps and prints the dashboard URL at the end. It also prompts:

```
Auto-terminate after how many hours? [0 = manual only, recommended: 4]
```

Enter a number (e.g. `4`) to set an automatic self-destruct timer — infrastructure deletes
itself after N hours. Prevents post-demo billing if you forget to tear down.

---

## Running the Demo

Everything is controlled from the **dashboard**. No AWS Console needed for normal operation.

### Step 1: Open the dashboard

URL is printed by quickdeploy:
`https://{api-gateway-id}.execute-api.us-east-1.amazonaws.com/prod/dashboard`

### Step 2: Confirm SNS subscription

Check admin email for "AWS Notification - Subscription Confirmation" and click the link.
Without this, approval emails won't be delivered.

### Step 3: Open Simulation Lab

Click **Simulation Lab** in the dashboard header. Five scenarios available:

| ID | Scenario | Expected Result |
|----|----------|-----------------|
| A1 | S3 Bucket — Public Access Open | Auto-remediated ~20s |
| A2 | Security Group — SSH Open to World | Auto-remediated ~20s |
| A3 | Security Group — All Traffic Open | Auto-remediated ~20s |
| B1 | IAM User — Role=CI-Pipeline | Admin approval email sent |
| B2 | Production SG — RDP Open | Admin approval email sent |

### Step 4: Run Category A (auto-remediation demo)

1. Click **Run** next to A1, A2, or A3
2. Dashboard creates a real misconfigured AWS resource and injects a finding
3. Finding appears in the table — status changes to `AUTO_REMEDIATED` within ~20 seconds
4. Click the finding row to open the detail modal:
   - Resource ARN, account ID, region, timestamps
   - AI analysis: risk level, safe_to_auto_remediate decision, justification
   - Remediation steps taken

### Step 5: Run Category B (admin approval demo)

1. Click **Run** next to B1 or B2
2. Finding appears with status `PENDING_APPROVAL`
3. Check admin email — rich HTML email arrives with:
   - AI analysis summary and risk assessment
   - Escalation reason (why AI flagged for approval)
   - **Approve** / **Reject** / **Manual Review** 1-click links
4. Click **Approve** — confirmation page opens, Step Functions resumes
5. Status: `APPROVED` → remediation runs → `RESOLVED`

### Step 6: AI Runbook (optional)

1. Click any finding row to open the detail modal
2. Click **Generate Runbook** — AI fetches live resource state and creates a step-by-step plan
3. Click **Apply Runbook** — inline boto3 remediation runs
4. Click **Undo** — restores pre-remediation state

### Step 7: Batch Remediation (optional)

1. Run B1 and B2 without approving (they stay as `PENDING_APPROVAL`)
2. Click **Remediate All** in the header
3. Set options: Runbook Priority, Retry on Failure, Max Attempts (1–5)
4. Start — live progress bar tracks Resolved / Advisory / Failed in real time

### Step 8: Reset

Click **Delete** next to each simulation in the Simulation Lab panel to clean up AWS resources.
Use **Clear All** to wipe the findings table for a fresh demo.

---

## Dashboard Controls Reference

| Control | Description |
|---------|-------------|
| Pipeline ON/OFF | Enables/disables EventBridge rule for real Security Hub findings |
| AI toggle | Enables/disables AI API calls; OFF uses keyword-based fallback (saves free tier quota) |
| AI button | Hot-swap provider/model (Gemini or Claude) with API key validation — no redeploy |
| Remediate All | Batch force-remediation of all PENDING_APPROVAL findings with retry |
| Simulation Lab | Create/delete the 5 demo scenarios on demand |
| Refresh | Reload findings from DynamoDB |
| Terminate | Type "terminate" to confirm — async self-destruct of all infrastructure |

---

## Viewing Step Functions Execution Graph (optional)

1. AWS Console → Step Functions → `SecurityRemediationStateMachine` → Executions
2. Click any execution to see the visual state flow
3. Expand any state to inspect input/output JSON

---

## Tearing Down

```powershell
.\scripts\quickdestroy.ps1
```

Or click **Terminate** in the dashboard — async self-destruct deletes all infrastructure
from within Lambda (SFN, DynamoDB, Lambda functions, SNS, EventBridge, CW logs, Secrets, API GW).

`quickdestroy.ps1` shows a discovery scan before confirming, then runs 6 steps:
SFN executions → Config → Security Hub standards → simulation resources → Terraform destroy → post-cleanup.
