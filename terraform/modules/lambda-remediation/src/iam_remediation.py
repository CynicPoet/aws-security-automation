"""
iam_remediation.py — IAM misconfiguration remediation Lambda.

Playbook: Deactivate all active access keys for an IAM user and attach
          a deny-all inline policy to prevent further API calls.

Follows the 6-step playbook pattern:
  1. VALIDATE   — extract username, check exclusion / service-account tags
  2. SAFETY CHECK — CI-Pipeline / ServiceAccount tags → must not auto-remediate
  3. LOG        — remediation starting
  4. EXECUTE    — deactivate keys + attach deny-all policy (idempotent)
  5. VERIFY     — confirm all keys inactive
  6. LOG        — outcome

Input event:
  {
    "finding": { finding_id, resource_type, resource_id, severity, ... },
    "ai_analysis": { ... },
    "approved_action": 1 | 2   # 1=deactivate+deny, 2=deny only (from admin approval flow)
  }
"""

import json
import os
import boto3
from botocore.exceptions import ClientError
from utils import StructuredLogger, update_finding_workflow, extract_iam_username, get_finding_fields, write_finding_status

REGION         = os.environ.get("AWS_REGION", "us-east-1")
FINDINGS_TABLE = os.environ.get("FINDINGS_TABLE", "")
DENY_ALL_POLICY_NAME = "SecurityAutomation-EmergencyDenyAll"

# Inline policy that denies all API actions — applied as a circuit-breaker
DENY_ALL_POLICY = json.dumps({
    "Version": "2012-10-17",
    "Statement": [{
        "Sid": "SecurityAutomationEmergencyDeny",
        "Effect": "Deny",
        "Action": "*",
        "Resource": "*",
    }]
})

iam = boto3.client("iam")


def lambda_handler(event: dict, context) -> dict:
    """Entry point — orchestrates the IAM remediation playbook."""
    log = StructuredLogger("security-auto-iam-remediation", context)
    finding = get_finding_fields(event)
    username = extract_iam_username(finding["resource_id"])
    approved_action = event.get("approved_action", 1)  # default: deactivate + deny

    log.info(
        "REMEDIATION_START",
        f"IAM remediation triggered for user '{username}' (action={approved_action})",
        finding_id=finding["finding_id"],
        resource_type=finding["resource_type"],
        resource_id=username,
        severity=finding["severity"],
    )

    # Write to DynamoDB so auto-remediated findings appear in dashboard
    write_finding_status(FINDINGS_TABLE, finding, event.get("ai_analysis", {}), "AUTO_REMEDIATED")

    # ── 1. VALIDATE ──────────────────────────────────────────────────────────
    try:
        user_tags = _get_user_tags(username)
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "NoSuchEntity":
            log.warning("REMEDIATION_SKIPPED", f"IAM user '{username}' not found — skipping", resource_id=username)
            return _result("SKIPPED", username, "user_not_found")
        raise

    if user_tags.get("AutoRemediationExclude", "").lower() == "true":
        log.info("REMEDIATION_SKIPPED", f"User '{username}' tagged AutoRemediationExclude=true — skipping", resource_id=username)
        return _result("SKIPPED", username, "excluded_by_tag")

    # ── 2. SAFETY CHECK ───────────────────────────────────────────────────────
    # Service accounts and CI pipelines must always require admin approval
    is_service_account = user_tags.get("ServiceAccount", "").lower() == "true"
    is_ci_pipeline = user_tags.get("Role", "").lower() == "ci-pipeline"
    if is_service_account or is_ci_pipeline:
        log.warning(
            "REMEDIATION_SKIPPED",
            f"User '{username}' is a service/CI account — admin approval required (not auto-remediating)",
            resource_id=username,
        )
        return _result("SKIPPED", username, "service_account_requires_approval")

    # ── 3. LOG ────────────────────────────────────────────────────────────────
    log.info("REMEDIATION_START", f"Applying IAM key deactivation + deny policy to user '{username}'", resource_id=username)

    deactivated_keys = []
    # ── 4. EXECUTE ────────────────────────────────────────────────────────────
    try:
        # Step A: Deactivate all active access keys (unless action=2 means deny-only)
        if approved_action != 2:
            keys = iam.list_access_keys(UserName=username).get("AccessKeyMetadata", [])
            for key in keys:
                if key["Status"] == "Active":
                    iam.update_access_key(
                        UserName=username,
                        AccessKeyId=key["AccessKeyId"],
                        Status="Inactive",
                    )
                    deactivated_keys.append(key["AccessKeyId"])
                    log.info("REMEDIATION_START", f"Deactivated access key {key['AccessKeyId']} for user '{username}'", resource_id=username)

        # Step B: Attach deny-all inline policy (idempotent — put_user_policy is safe to repeat)
        iam.put_user_policy(
            UserName=username,
            PolicyName=DENY_ALL_POLICY_NAME,
            PolicyDocument=DENY_ALL_POLICY,
        )

    except ClientError as exc:
        log.error(
            "REMEDIATION_FAILED",
            f"IAM remediation failed for '{username}': {exc.response['Error']['Message']}",
            resource_id=username,
            outcome="FAILED",
        )
        return _result("FAILED", username, "iam_key_deactivate_deny_policy", error=str(exc))

    # ── 5. VERIFY ─────────────────────────────────────────────────────────────
    verified = _verify_no_active_keys(username) if approved_action != 2 else _verify_deny_policy(username)
    if not verified:
        log.error("REMEDIATION_FAILED", f"Verification failed for user '{username}'", resource_id=username, outcome="FAILED")
        return _result("FAILED", username, "iam_key_deactivate_deny_policy", error="post-apply verification failed")

    # ── 6. LOG ────────────────────────────────────────────────────────────────
    action_desc = "iam_deactivate_keys_deny_policy" if approved_action != 2 else "iam_deny_policy_only"
    log.info(
        "REMEDIATION_SUCCESS",
        f"IAM remediation complete for '{username}': {len(deactivated_keys)} keys deactivated, deny policy applied",
        resource_id=username,
        action_taken=action_desc,
        outcome="SUCCESS",
    )

    if finding["finding_id"] != "unknown" and finding["product_arn"]:
        try:
            action_label = f"action {approved_action}" if approved_action else "auto"
            update_finding_workflow(
                finding["finding_id"],
                finding["product_arn"],
                "RESOLVED",
                f"Admin-approved remediation — {action_label} — {action_desc}",
                region=REGION,
            )
        except ClientError:
            pass

    return _result("SUCCESS", username, action_desc, deactivated_keys=deactivated_keys)


# ── HELPERS ───────────────────────────────────────────────────────────────────

def _get_user_tags(username: str) -> dict:
    """Return IAM user tags as a flat dict."""
    try:
        response = iam.list_user_tags(UserName=username)
        return {t["Key"]: t["Value"] for t in response.get("Tags", [])}
    except ClientError:
        return {}


def _verify_no_active_keys(username: str) -> bool:
    """Return True if the user has no active access keys."""
    keys = iam.list_access_keys(UserName=username).get("AccessKeyMetadata", [])
    return all(k["Status"] != "Active" for k in keys)


def _verify_deny_policy(username: str) -> bool:
    """Return True if the deny-all inline policy exists on the user."""
    policies = iam.list_user_policies(UserName=username).get("PolicyNames", [])
    return DENY_ALL_POLICY_NAME in policies


def _result(status: str, resource_id: str, action: str, error: str = None, deactivated_keys: list = None) -> dict:
    return {
        "status": status,
        "resource_id": resource_id,
        "resource_type": "AwsIamUser",
        "action_taken": action,
        "deactivated_keys": deactivated_keys or [],
        "error": error,
    }
