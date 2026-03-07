# Cost Log

Tracking AWS costs and engineering decisions for this project.

---

## Current Monthly Cost (demo mode, Config removed)

| Service | Resource | Est. Monthly Cost |
|---------|----------|-------------------|
| API Gateway | REST API flat fee (prorated) | ~$0.01 |
| Secrets Manager | `security-automation/ai-api-key` | ~$0.01 (while deployed) |
| Lambda | 8 functions, invocations only | ~$0.00 |
| Step Functions | STANDARD, invocations only | ~$0.00 |
| SNS | Email topic + messages | ~$0.00 |
| EventBridge | Rule invocations | ~$0.00 |
| CloudWatch Logs | Lambda log groups | ~$0.00 |
| DynamoDB | findings + settings tables, on-demand | ~$0.00 |
| Security Hub | Account activation only (no standards) | $0.00 |
| AWS Config | Removed — see below | $0.00 |
| **Total** | | **~$0.02/month** |

---

## Config Billing Incident — March 2026

### What happened

`security-hub/main.tf` was initially deployed with:

```hcl
resource "aws_config_configuration_recorder" "this" {
  recording_group {
    all_supported                 = true
    include_global_resource_types = true
  }
}
```

`all_supported = true` records every AWS resource change across the entire account at $0.003/item.
With normal development activity (Lambda deploys, security group changes, S3 bucket operations),
this generated:

- **Period 1:** 1,283 items → $3.85
- **Period 2 (12h later):** 1,633 items → $4.90 (items queued before deletion still billed)
- **Total charged:** ~$5.80 including tax

### What was fixed

1. Stopped the Config recorder immediately via boto3
2. Deleted recorder, delivery channel, S3 delivery bucket, and IAM role manually
3. Removed all Config resources and Security Hub standards subscriptions from Terraform
4. Disabled Security Hub standards (CIS v1.2, v1.4, FSBP) — they require Config to function

### Why removing standards was acceptable for demo

Security Hub standards subscriptions are only needed to *generate* real findings from resource
compliance checks. The demo uses simulated findings injected directly into Step Functions.
The remediation pipeline, AI analysis, approval workflow, and dashboard are all fully functional
regardless of finding source.

In a production deployment, Config + standards would be re-enabled with a restricted
recording group (only the 5 resource types actually monitored), dropping Config cost to ~$0.06/month.

### Billing lag note

AWS bills Config items that were already queued at the time of deletion. Deleting the recorder
does not cancel charges for items recorded before deletion. The $4.90 charge appeared on the
bill ~12 hours after the recorder was stopped — this is normal AWS billing behavior, not a bug.

---

## Budget Protection

Configured in `terraform/modules/budget/main.tf`:

| Threshold | Action |
|-----------|--------|
| $0.01 actual | Email alert |
| $1.00 actual | Email alert |
| $3.00 actual | Email alert |
| $5.00 actual | **Attach `BudgetExceededDenyAll` IAM policy to `terraform-deployer`** |

The $5 action attaches a deny-all IAM policy to the deployer user, blocking all AWS API calls
from Terraform and scripts. This fires once per billing period. To re-enable after triggering:
go to IAM Console → Users → terraform-deployer → Permissions → Detach the policy.

Note: Budget Actions fire once per threshold per billing period. If the spend already exceeds
the threshold at action creation time, it fires immediately.

---

## Auto-TTL

`quickdeploy.ps1` prompts for an auto-terminate timer at deploy time. Entering N hours creates
an EventBridge cron rule (`security-auto-ttl`) that invokes `_do_terminate` on the dashboard
Lambda after N hours. This deletes all infrastructure automatically — prevents post-demo billing
even if the manual destroy step is forgotten.

---

## Original Estimated Cost (before Config removal)

For historical reference — the original estimate that was significantly off:

| Service | Original Estimate | Actual (with all_supported=true) |
|---------|-------------------|----------------------------------|
| AWS Config | $0.03/resource | **$4.90 per development period** |
| Secrets Manager | $0.40/month | $0.40/month |
| Security Hub (standards) | $0.05–0.10/month | $0.05–0.10/month |
| Everything else | ~$0.00 | ~$0.02/month |
| **Total** | **~$0.70/month** | **~$5.80/month** |

The original estimate was based on a small number of tracked resources. `all_supported = true`
records every resource in the account, not just the ones your project monitors — Lambda deploys,
SG rule changes, S3 bucket operations all generate Config items.
