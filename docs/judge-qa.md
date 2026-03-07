# Judge / Interviewer Q&A

Common questions from evaluators and suggested answers.

---

## Architecture & Design

**Q: Why use Step Functions instead of a single Lambda orchestrator?**

Step Functions provides: visual execution graph (great for demos), built-in retry/catch per state,
`waitForTaskToken` for human-in-the-loop without polling, CloudWatch integration, and a complete
audit trail of every state transition. A single Lambda would require custom state management and
lose all those benefits. Step Functions STANDARD type stores full execution history — each
remediation event is permanently logged and queryable.

---

**Q: Why AI? Couldn't you just use rule-based routing?**

Rule-based routing handles simple cases (severity=HIGH → escalate), but AI adds:
1. **False positive detection** — recognizes context like `PublicAccess=Intentional` or
   `Purpose=StaticWebsite` tags without hardcoding every combination
2. **Risk contextualization** — considers resource type, environment, tags, and severity together
3. **Natural language justification** — explains *why* it made a decision in the approval email
4. **Extensibility** — new finding types don't require code changes, just prompt tuning

The AI does NOT write remediation code at runtime. Pre-written playbooks execute — AI only routes.

---

**Q: What prevents the AI from doing something dangerous?**

Multiple layers of hardcoded safety overrides that the AI cannot bypass:

- `AutoRemediationExclude=true` tag → never auto-remediate, regardless of AI output
- `Environment=Production` → always require human approval
- Default security groups → never modify
- `ServiceAccount=true` / `Role=CI-Pipeline` → IAM remediation always escalates
- `recommended_playbook` not in approved list → force to `manual`
- AI failure / malformed JSON → default to HIGH risk, escalate (fail-safe, not fail-open)
- AI API unreachable → keyword-based fallback routing, never blocks the pipeline

The principle: AI advises, safety rules govern, humans approve high-risk actions.

---

**Q: How is this different from AWS Config + automatic remediation?**

AWS Config auto-remediation runs SSM documents with limited context and no human-in-the-loop.
This system adds: AI-powered false positive detection, contextual risk analysis, structured
admin approval workflow with email links, full audit logs, verification after remediation,
a real-time web dashboard, AI runbook generation, and batch remediation with retry feedback.

---

**Q: The README says the demo uses simulated findings — is the Security Hub integration real?**

Yes, the full integration is implemented:
- Security Hub account is activated
- EventBridge rule (`securityhub-finding-rule`) is deployed and wired to Step Functions
- All IAM permissions for Security Hub → EventBridge → SFN are in place
- The pipeline accepts real Security Hub findings when the EventBridge rule is enabled

For the demo environment, I removed AWS Config and Security Hub standards subscriptions because
Config's `all_supported = true` recording generated $4.90 in charges in a single development
period (1,633 recorded items × $0.003). The demo uses simulated findings injected directly into
Step Functions — the remediation pipeline is identical in both paths.

In a production deployment, you'd re-enable Config with a restricted recording group (5 resource
types instead of all), dropping Config cost from ~$5/month to ~$0.06/month.

---

**Q: Why did you remove Config entirely rather than just restricting the recording group?**

For a simulation-based demo, Config provides no value — findings come from the Simulation Lab,
not from real resource state evaluation. Adding Config back with a restricted recording group
would add cost and operational complexity (recorder, delivery channel, S3 bucket, IAM role)
for zero benefit in the demo context. The architecture document explains both configurations
and what would be needed for a production deployment.

---

## Security

**Q: Is this production-ready?**

The architecture is production-grade: IAM least-privilege (8 roles, each scoped to minimum
required actions), no hardcoded credentials, Secrets Manager for API keys, structured audit
logging via CloudWatch, idempotent remediation playbooks, and fail-safe AI routing.

For a real production deployment you'd add: VPC placement for Lambdas, KMS encryption for
DynamoDB/SNS/CloudWatch, SCPs to prevent IAM permission escalation, WAF on API Gateway,
and Config + Security Hub standards with a restricted recording group.

---

**Q: What if the approval email link expires?**

Step Functions `waitForTaskToken` has `HeartbeatSeconds=3600` (1-hour timeout). If the admin
doesn't respond within 1 hour, the timeout path fires: logs the event, sends a secondary
notification, and ends in a `Succeed` state (not `Fail`) to prevent false alarms. The finding
remains visible in the dashboard for manual follow-up.

---

**Q: How do you prevent replay attacks on the approval URL?**

The task token is a cryptographically random string generated by Step Functions — functionally
a one-time token. Once used (success or failure sent), subsequent calls with the same token
return `InvalidToken`. The Lambda handles this with a "link expired" HTML response. The token
is execution-specific, so there's no cross-execution reuse.

---

## Cost & Scalability

**Q: What does this cost per month?**

~$0.02/month in demo mode (Config removed). Breakdown:
- API Gateway: ~$0.01 (REST API flat fee)
- Secrets Manager: ~$0.01 (while deployed; deleted on terminate)
- Lambda / Step Functions / SNS / DynamoDB / EventBridge: ~$0.00 (pay-per-use, negligible at demo scale)

A hard budget guard ($5 limit via AWS Budgets Action) auto-attaches a deny-all IAM policy to the
deployer user if spend exceeds $5, preventing runaway charges.

In production with Config (restricted recording group, 5 resource types): ~$0.10–0.20/month.

---

**Q: Can this handle multiple AWS accounts?**

The current deployment is single-account. Multi-account would add:
- Security Hub aggregator (designate a security account)
- EventBridge cross-account event bus rules
- Lambda assuming cross-account IAM roles for remediation
- The Step Functions + AI + dashboard layer remains unchanged

---

## Implementation

**Q: Why Gemini instead of Claude/GPT-4 as the default?**

Gemini 2.0 Flash has a generous free tier — zero API cost for demo/development. The system
is fully provider-agnostic: the dashboard has a hot-swap UI to switch between Gemini and Claude
(any model) with no redeploy. Both providers are validated with a live test call before saving.
The fallback chain (2.0 Flash → 2.0 Flash Lite → 1.5 Flash) ensures the pipeline never blocks
even if a specific model is unavailable.

---

**Q: Why Python stdlib + boto3 only? No Lambda Layers?**

Lambda Layers add operational complexity (version management, layer ARNs, region copying).
By calling Gemini/Claude REST APIs directly via `urllib.request`, the system has zero external
dependencies beyond boto3 (included in every Lambda runtime). The Lambda zip contains only
`.py` files — deploys in seconds, no pip install, no layer management. The code is fully
readable without a build step.

---

**Q: How did you handle the AI provider hot-swap without redeploying Lambda?**

Provider and model settings are stored in DynamoDB (`security-automation-settings` table).
The AI Analyzer Lambda reads DynamoDB at invocation time (not at cold start), so updating
a setting in DynamoDB takes effect on the next finding with zero infrastructure changes.
The API key is stored in Secrets Manager, also read at invocation time. The dashboard calls
`PUT /api/ai-config` which writes to both DynamoDB and Secrets Manager — hot-swap is fully
self-contained.

---

**Q: What is the batch remediation feature?**

"Remediate All" processes all `PENDING_APPROVAL` findings sequentially. For each finding:
1. Optionally uses an existing READY runbook first (if Runbook Priority is on)
2. Falls back to live AI runbook generation
3. Applies inline remediation (S3/SG/IAM) or marks advisory for unsupported resource types
4. On failure: feeds full failure logs to AI for the next retry attempt (accuracy improves each retry)

Progress is tracked in DynamoDB and polled by the dashboard every 3 seconds with a live
progress bar showing Resolved/Advisory/Failed counts.

---

**Q: How long did this take to build?**

Built incrementally across multiple stages, each validated and committed before moving to the
next. The project includes ~12 Terraform modules, ~15 Python source files, a full web dashboard
(single-file HTML/JS/CSS), and supporting scripts.
