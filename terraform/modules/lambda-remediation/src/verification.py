"""
verification.py — Post-remediation verification Lambda.

Re-checks the resource after remediation to confirm the fix was applied correctly.
Routes to the appropriate check function based on resource_type.

Input event:
  {
    "finding": { finding_id, resource_type, resource_id, ... },
    "remediation_result": { status, resource_id, resource_type, action_taken, ... }
  }

Returns:
  {
    "verification_passed": true | false,
    "resource_id": "...",
    "resource_type": "...",
    "check_performed": "...",
    "details": "..."
  }
"""

import os
import boto3
from botocore.exceptions import ClientError
from utils import StructuredLogger, update_finding_workflow, extract_bucket_name, extract_iam_username, extract_sg_id, get_finding_fields

REGION = os.environ.get("AWS_REGION", "us-east-1")
DENY_ALL_POLICY_NAME = "SecurityAutomation-EmergencyDenyAll"
OPEN_CIDRS = {"0.0.0.0/0", "::/0"}

s3 = boto3.client("s3")
iam = boto3.client("iam")
ec2 = boto3.client("ec2", region_name=REGION)


def lambda_handler(event: dict, context) -> dict:
    """Entry point — routes to the appropriate resource-type check."""
    log = StructuredLogger("security-auto-verification", context)
    finding = get_finding_fields(event)
    remediation = event.get("remediation_result", {})

    resource_type = finding["resource_type"]
    resource_id = remediation.get("resource_id", finding["resource_id"])

    log.info(
        "VERIFICATION_START",
        f"Verifying remediation for {resource_type} '{resource_id}'",
        finding_id=finding["finding_id"],
        resource_type=resource_type,
        resource_id=resource_id,
    )

    # If the remediation was skipped (e.g. exclusion tag), mark as passed with note
    if remediation.get("status") == "SKIPPED":
        log.info("VERIFICATION_PASS", f"Remediation was skipped — no verification needed", resource_id=resource_id)
        return _result(True, resource_id, resource_type, "skipped_no_check", "Remediation was intentionally skipped")

    try:
        if "S3" in resource_type or "s3" in resource_id.lower():
            return _verify_s3(log, finding, resource_id)
        elif "Iam" in resource_type or "iam" in resource_type.lower():
            return _verify_iam(log, finding, resource_id)
        elif "SecurityGroup" in resource_type or resource_id.startswith("sg-"):
            return _verify_vpc(log, finding, resource_id)
        else:
            log.warning("VERIFICATION_PASS", f"Unknown resource type '{resource_type}' — marking as passed", resource_id=resource_id)
            return _result(True, resource_id, resource_type, "unknown_type_pass", f"No verifier for type {resource_type}")
    except Exception as exc:
        log.error("VERIFICATION_FAIL", f"Verification check threw exception: {exc}", resource_id=resource_id)
        return _result(False, resource_id, resource_type, "exception", str(exc))


# ── S3 VERIFICATION ───────────────────────────────────────────────────────────

def _verify_s3(log, finding: dict, resource_id: str) -> dict:
    """Verify all four S3 Block Public Access settings are enabled."""
    bucket_name = extract_bucket_name(resource_id)
    try:
        resp = s3.get_bucket_public_access_block(Bucket=bucket_name)
        cfg = resp["PublicAccessBlockConfiguration"]
        all_blocked = all([
            cfg.get("BlockPublicAcls"),
            cfg.get("IgnorePublicAcls"),
            cfg.get("BlockPublicPolicy"),
            cfg.get("RestrictPublicBuckets"),
        ])
        if all_blocked:
            log.info("VERIFICATION_PASS", f"S3 bucket '{bucket_name}' — all Block Public Access settings confirmed", resource_id=bucket_name, outcome="SUCCESS")
            _resolve_finding(finding, "Auto-remediated — s3_block_public_access verified")
            return _result(True, bucket_name, "AwsS3Bucket", "s3_public_access_block_check", "All four Block Public Access settings enabled")
        else:
            log.error("VERIFICATION_FAIL", f"S3 bucket '{bucket_name}' — Block Public Access NOT fully enabled", resource_id=bucket_name, outcome="FAILED")
            return _result(False, bucket_name, "AwsS3Bucket", "s3_public_access_block_check", f"Settings: {cfg}")
    except ClientError as exc:
        if "NoSuchPublicAccessBlockConfiguration" in exc.response["Error"]["Code"]:
            log.error("VERIFICATION_FAIL", f"S3 bucket '{bucket_name}' — no Block Public Access config found", resource_id=bucket_name)
            return _result(False, bucket_name, "AwsS3Bucket", "s3_public_access_block_check", "No BlockPublicAccess configuration found")
        raise


# ── IAM VERIFICATION ──────────────────────────────────────────────────────────

def _verify_iam(log, finding: dict, resource_id: str) -> dict:
    """Verify no active access keys and deny policy is attached."""
    username = extract_iam_username(resource_id)
    try:
        keys = iam.list_access_keys(UserName=username).get("AccessKeyMetadata", [])
        active_keys = [k for k in keys if k["Status"] == "Active"]
        policies = iam.list_user_policies(UserName=username).get("PolicyNames", [])
        deny_attached = DENY_ALL_POLICY_NAME in policies

        if len(active_keys) == 0 and deny_attached:
            log.info("VERIFICATION_PASS", f"IAM user '{username}' — no active keys and deny policy confirmed", resource_id=username, outcome="SUCCESS")
            _resolve_finding(finding, "Admin-approved remediation — iam_remediation verified")
            return _result(True, username, "AwsIamUser", "iam_keys_deactivated_check", "All keys inactive, deny policy attached")
        else:
            details = f"active_keys={len(active_keys)}, deny_policy={deny_attached}"
            log.error("VERIFICATION_FAIL", f"IAM user '{username}' — verification failed: {details}", resource_id=username, outcome="FAILED")
            return _result(False, username, "AwsIamUser", "iam_keys_deactivated_check", details)
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "NoSuchEntity":
            log.warning("VERIFICATION_PASS", f"IAM user '{username}' no longer exists — treating as pass", resource_id=username)
            return _result(True, username, "AwsIamUser", "iam_user_deleted", "User no longer exists")
        raise


# ── VPC VERIFICATION ──────────────────────────────────────────────────────────

def _verify_vpc(log, finding: dict, resource_id: str) -> dict:
    """Verify no 0.0.0.0/0 or ::/0 ingress rules remain."""
    sg_id = extract_sg_id(resource_id)
    try:
        response = ec2.describe_security_groups(GroupIds=[sg_id])
        sg = response["SecurityGroups"][0]
        open_rules = [
            p for p in sg["IpPermissions"]
            if any(r.get("CidrIp") in OPEN_CIDRS for r in p.get("IpRanges", []))
            or any(r.get("CidrIpv6") in OPEN_CIDRS for r in p.get("Ipv6Ranges", []))
        ]
        if not open_rules:
            log.info("VERIFICATION_PASS", f"Security group '{sg_id}' — no open-world rules confirmed", resource_id=sg_id, outcome="SUCCESS")
            _resolve_finding(finding, "Auto-remediated — vpc_remediation verified")
            return _result(True, sg_id, "AwsEc2SecurityGroup", "vpc_open_world_rules_check", "No open-world ingress rules found")
        else:
            log.error("VERIFICATION_FAIL", f"Security group '{sg_id}' — {len(open_rules)} open rules still present", resource_id=sg_id, outcome="FAILED")
            return _result(False, sg_id, "AwsEc2SecurityGroup", "vpc_open_world_rules_check", f"{len(open_rules)} open-world rules still present")
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "InvalidGroup.NotFound":
            log.warning("VERIFICATION_PASS", f"Security group '{sg_id}' no longer exists — treating as pass", resource_id=sg_id)
            return _result(True, sg_id, "AwsEc2SecurityGroup", "sg_deleted", "SG no longer exists")
        raise


# ── HELPERS ───────────────────────────────────────────────────────────────────

def _resolve_finding(finding: dict, note: str) -> None:
    """Update Security Hub finding to RESOLVED. Non-fatal if it fails."""
    if finding["finding_id"] != "unknown" and finding.get("product_arn"):
        try:
            update_finding_workflow(finding["finding_id"], finding["product_arn"], "RESOLVED", note, region=REGION)
        except ClientError:
            pass


def _result(passed: bool, resource_id: str, resource_type: str, check: str, details: str) -> dict:
    return {
        "verification_passed": passed,
        "resource_id": resource_id,
        "resource_type": resource_type,
        "check_performed": check,
        "details": details,
        "outcome": "SUCCESS" if passed else "FAILED",
    }
