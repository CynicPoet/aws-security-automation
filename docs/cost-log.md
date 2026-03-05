# Cost Log

Tracking monthly AWS cost estimates for this project.

---

## Target Budget

**$1.00/month** (hard limit enforced via AWS Budgets alert at 80% and 100%)

---

## Estimated Monthly Cost Breakdown (at rest, no traffic)

| Service | Resource | Est. Monthly Cost |
|---------|----------|-------------------|
| Secrets Manager | `security-automation/ai-api-key` (1 secret) | $0.40 |
| Security Hub | FSBP + CIS standards, us-east-1 | $0.05–0.10 |
| CloudWatch Logs | `/aws/security-automation` 90-day retention | $0.05–0.10 |
| CloudWatch Alarms | 2 alarms | $0.20 |
| Lambda | 7 functions, invocations only | ~$0.00 |
| Step Functions | STANDARD, invocations only | ~$0.00 |
| API Gateway | REST API, invocations only | ~$0.00 |
| SNS | Email subscriptions, messages only | ~$0.01 |
| IAM | Roles and policies | $0.00 |
| EventBridge | Rule (invocations only) | ~$0.00 |
| AWS Config | Recorder (resource tracking) | $0.03/resource recorded |
| S3 | Config delivery bucket (minimal) | ~$0.01 |
| **Total** | | **~$0.61–0.90/mo** |

---

## Notes

- **Secrets Manager** is the single largest cost item — $0.40/secret/month is fixed
- **CloudWatch Alarms**: $0.10/alarm/month × 2 = $0.20/month
- **Security Hub**: Free for first 30 days, then charges per check. FSBP + CIS = ~$0.05–0.10/mo for a small account
- **Lambda/Step Functions/API GW**: Generous free tiers (1M Lambda requests free, 4000 state transitions free). Effectively $0 for demo usage
- **AI API (Gemini)**: $0.00 — using free tier (10 RPM, 250 RPD). Would be ~$0.00–0.10/mo even on paid tier at demo volume

---

## Budget Alert Configuration

Configured in `terraform/modules/budget/main.tf`:
- Alert at **80% actual** of $1.00/mo → email to `admin_email`
- Alert at **100% forecasted** of $1.00/mo → email to `admin_email`

---

## Cost Reduction Options

| Option | Savings |
|--------|---------|
| Remove CloudWatch Alarms | -$0.20/mo |
| Use `pause-project.ps1` between sessions | Stops Lambda/Step Functions invocations (already $0) |
| Reduce Config recorder to specific resource types | -$0.01–0.05/mo |
| Reduce log retention from 90 to 14 days | -$0.03–0.05/mo |
