# Demo Guide

## Prerequisites

- Terraform stack deployed (`.\scripts\deploy.ps1`)
- SNS subscription confirmed (check email inbox)
- AI API key set in Secrets Manager (see deploy script output)

---

## Running the Demo

### Step 1: Deploy simulation resources

```powershell
.\scripts\demo.ps1
```

This creates 6 intentionally misconfigured resources in ~30 seconds.

### Step 2: Watch the automation (AWS Console)

1. Open **Step Functions** → `SecurityRemediationStateMachine` → **Executions**
   - You'll see new executions appear within 5–30 seconds per finding
   - Click any execution to see the visual state machine flow

2. Open **CloudWatch** → **Log Insights** → select `/aws/security-automation`
   - Run: `fields @timestamp, event_type, resource_id, action_taken, outcome | sort @timestamp desc | limit 50`

3. Open **Security Hub** → **Findings**
   - Filter: `Workflow status = RESOLVED` to see auto-remediated findings

### Step 3: Approve a Category B action

- Check your admin email for an approval request
- Email contains: AI analysis, risk assessment, recommended action, and clickable approve/reject links
- Click **Approve (Recommended Action)** → browser opens → confirmation page → Step Functions resumes

### Step 4: Verify results

| Resource | Expected outcome |
|----------|-----------------|
| S3 `secauto-test-public-*` | Public access blocked, finding RESOLVED |
| SG `secauto-test-open-ssh` | Port 22 rule revoked, finding RESOLVED |
| SG `secauto-test-open-all` | All open-world rules revoked, finding RESOLVED |
| IAM `secauto-test-risky-user` | Access key deactivated (after admin approval) |
| SG `secauto-test-open-rdp` | Port 3389 rule revoked (after admin approval) |
| S3 `secauto-test-fp-website-*` | **No action taken** — false positive suppressed |

### Step 5: Reset demo

```powershell
.\scripts\demo.ps1 -Destroy   # remove simulation resources
.\scripts\demo.ps1            # recreate fresh misconfigurations
```

---

## Key Console Locations

| What to see | Console path |
|-------------|-------------|
| State machine executions | Step Functions → SecurityRemediationStateMachine |
| Structured logs | CloudWatch → Log Insights → /aws/security-automation |
| Live dashboard | CloudWatch → Dashboards → SecurityAutomation-LiveMonitor |
| Security findings | Security Hub → Findings |
| Approval emails | Your inbox (admin_email) |
| API approval links | API Gateway → SecurityAutomationApprovalAPI → Stages → prod |

---

## Pausing Between Demo Sessions

To avoid ongoing Security Hub charges during development breaks:

```powershell
.\scripts\pause-project.ps1   # disables EventBridge rule, ~$0.60/mo cost
.\scripts\resume-project.ps1  # re-enables before next demo
```
