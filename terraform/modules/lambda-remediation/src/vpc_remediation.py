"""
vpc_remediation.py — VPC security group misconfiguration remediation Lambda.

Playbook: Revoke all inbound rules that allow unrestricted access (0.0.0.0/0 or ::/0)
          on the specified security group.

Follows the 6-step playbook pattern:
  1. VALIDATE   — extract SG ID, check exclusion tags, never modify default SG
  2. SAFETY CHECK — Production-tagged SG → require admin approval
  3. LOG        — remediation starting
  4. EXECUTE    — revoke all 0.0.0.0/0 and ::/0 ingress rules (idempotent)
  5. VERIFY     — confirm no open-world rules remain
  6. LOG        — outcome

Input event:
  {
    "finding": { finding_id, resource_type, resource_id, severity, ... },
    "ai_analysis": { ... },
    "approved_action": 1 | 2   # 1=revoke all, 2=restrict to CIDR (from admin approval)
  }
"""

import os
import boto3
from botocore.exceptions import ClientError
from utils import StructuredLogger, update_finding_workflow, extract_sg_id, get_finding_fields, write_finding_status

REGION         = os.environ.get("AWS_REGION", "us-east-1")
FINDINGS_TABLE = os.environ.get("FINDINGS_TABLE", "")
OPEN_CIDRS = {"0.0.0.0/0", "::/0"}

ec2 = boto3.client("ec2", region_name=REGION)


def lambda_handler(event: dict, context) -> dict:
    """Entry point — orchestrates the VPC security group remediation playbook."""
    log = StructuredLogger("security-auto-vpc-remediation", context)
    finding = get_finding_fields(event)
    sg_id = extract_sg_id(finding["resource_id"])

    log.info(
        "REMEDIATION_START",
        f"VPC remediation triggered for security group '{sg_id}'",
        finding_id=finding["finding_id"],
        resource_type=finding["resource_type"],
        resource_id=sg_id,
        severity=finding["severity"],
    )

    # Write to DynamoDB so auto-remediated findings appear in dashboard
    write_finding_status(FINDINGS_TABLE, finding, event.get("ai_analysis", {}), "AUTO_REMEDIATED")

    # ── 1. VALIDATE ──────────────────────────────────────────────────────────
    try:
        sg = _get_security_group(sg_id)
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "InvalidGroup.NotFound":
            log.warning("REMEDIATION_SKIPPED", f"Security group '{sg_id}' not found — skipping", resource_id=sg_id)
            return _result("SKIPPED", sg_id, "sg_not_found")
        raise

    sg_tags = {t["Key"]: t["Value"] for t in sg.get("Tags", [])}
    sg_name = sg.get("GroupName", sg_id)

    if sg_tags.get("AutoRemediationExclude", "").lower() == "true":
        log.info("REMEDIATION_SKIPPED", f"SG '{sg_id}' tagged AutoRemediationExclude=true — skipping", resource_id=sg_id)
        return _result("SKIPPED", sg_id, "excluded_by_tag")

    # Never modify the default security group blindly
    if sg_name == "default":
        log.warning("REMEDIATION_SKIPPED", f"SG '{sg_id}' is the default security group — skipping (safety rule)", resource_id=sg_id)
        return _result("SKIPPED", sg_id, "default_sg_protected")

    # ── 2. SAFETY CHECK ───────────────────────────────────────────────────────
    if sg_tags.get("Environment", "").lower() == "production":
        log.warning(
            "REMEDIATION_SKIPPED",
            f"SG '{sg_id}' is tagged Environment=Production — admin approval required",
            resource_id=sg_id,
        )
        return _result("SKIPPED", sg_id, "production_requires_approval")

    # ── 3. LOG ────────────────────────────────────────────────────────────────
    open_rules = _find_open_rules(sg["IpPermissions"])
    log.info(
        "REMEDIATION_START",
        f"Found {len(open_rules)} open-world ingress rules on '{sg_id}' — revoking",
        resource_id=sg_id,
    )

    if not open_rules:
        log.info("REMEDIATION_SKIPPED", f"No open-world rules found on '{sg_id}' — already compliant", resource_id=sg_id)
        return _result("SKIPPED", sg_id, "already_compliant")

    # ── 4. EXECUTE ────────────────────────────────────────────────────────────
    try:
        ec2.revoke_security_group_ingress(
            GroupId=sg_id,
            IpPermissions=open_rules,
        )
    except ClientError as exc:
        # InvalidPermission.NotFound means rule was already removed — idempotent
        if exc.response["Error"]["Code"] == "InvalidPermission.NotFound":
            log.info("REMEDIATION_START", f"Rules on '{sg_id}' already removed — idempotent", resource_id=sg_id)
        else:
            log.error(
                "REMEDIATION_FAILED",
                f"Failed to revoke rules on '{sg_id}': {exc.response['Error']['Message']}",
                resource_id=sg_id,
                outcome="FAILED",
            )
            return _result("FAILED", sg_id, "revoke_open_world_rules", error=str(exc))

    # ── 5. VERIFY ─────────────────────────────────────────────────────────────
    verified = _verify_no_open_rules(sg_id)
    if not verified:
        log.error("REMEDIATION_FAILED", f"Verification failed — open rules still present on '{sg_id}'", resource_id=sg_id, outcome="FAILED")
        return _result("FAILED", sg_id, "revoke_open_world_rules", error="post-apply verification failed")

    # ── 6. LOG ────────────────────────────────────────────────────────────────
    log.info(
        "REMEDIATION_SUCCESS",
        f"Revoked {len(open_rules)} open-world ingress rules from security group '{sg_id}'",
        resource_id=sg_id,
        action_taken="vpc_revoke_open_world_ingress",
        outcome="SUCCESS",
    )

    if finding["finding_id"] != "unknown" and finding["product_arn"]:
        try:
            update_finding_workflow(
                finding["finding_id"],
                finding["product_arn"],
                "RESOLVED",
                "Auto-remediated by SecurityAutomation pipeline — vpc_remediation playbook",
                region=REGION,
            )
        except ClientError:
            pass

    return _result("SUCCESS", sg_id, "vpc_revoke_open_world_ingress", revoked_count=len(open_rules))


# ── HELPERS ───────────────────────────────────────────────────────────────────

def _get_security_group(sg_id: str) -> dict:
    """Return the security group dict from EC2."""
    response = ec2.describe_security_groups(GroupIds=[sg_id])
    return response["SecurityGroups"][0]


def _find_open_rules(ip_permissions: list) -> list:
    """
    Return ingress rules that contain 0.0.0.0/0 or ::/0 ranges.
    Returns the exact permission objects needed for revoke_security_group_ingress.
    """
    open_rules = []
    for perm in ip_permissions:
        # Filter IPv4 ranges to only open-world CIDRs
        ipv4_ranges = [r for r in perm.get("IpRanges", []) if r.get("CidrIp") in OPEN_CIDRS]
        ipv6_ranges = [r for r in perm.get("Ipv6Ranges", []) if r.get("CidrIpv6") in OPEN_CIDRS]

        if ipv4_ranges or ipv6_ranges:
            # Build a targeted revoke permission for only the open-world ranges
            filtered = dict(perm)
            if ipv4_ranges:
                filtered["IpRanges"] = ipv4_ranges
            else:
                filtered.pop("IpRanges", None)
            if ipv6_ranges:
                filtered["Ipv6Ranges"] = ipv6_ranges
            else:
                filtered.pop("Ipv6Ranges", None)
            # Remove empty UserIdGroupPairs if present
            filtered.pop("UserIdGroupPairs", None)
            filtered.pop("PrefixListIds", None)
            open_rules.append(filtered)

    return open_rules


def _verify_no_open_rules(sg_id: str) -> bool:
    """Return True if the SG has no open-world ingress rules remaining."""
    sg = _get_security_group(sg_id)
    return len(_find_open_rules(sg["IpPermissions"])) == 0


def _result(status: str, resource_id: str, action: str, error: str = None, revoked_count: int = 0) -> dict:
    return {
        "status": status,
        "resource_id": resource_id,
        "resource_type": "AwsEc2SecurityGroup",
        "action_taken": action,
        "revoked_rules_count": revoked_count,
        "error": error,
    }
