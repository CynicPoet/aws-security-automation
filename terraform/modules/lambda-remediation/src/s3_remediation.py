"""
s3_remediation.py — S3 misconfiguration remediation Lambda.

Playbook: Block all four S3 Block Public Access settings and set bucket ACL to private.

Follows the 6-step playbook pattern:
  1. VALIDATE   — extract bucket name, check exclusion tags
  2. SAFETY CHECK — website hosting → flag for false positive, don't auto-fix
  3. LOG        — remediation starting
  4. EXECUTE    — apply block public access + private ACL (idempotent)
  5. VERIFY     — confirm settings applied
  6. LOG        — outcome

Input event (from Step Functions):
  {
    "finding": { finding_id, resource_type, resource_id, severity, ... },
    "ai_analysis": { risk_level, recommended_playbook, safe_to_auto_remediate, ... }
  }

Returns:
  { "status": "SUCCESS"|"FAILED"|"SKIPPED", "resource_id": "...", "action_taken": "...", ... }
"""

import os
import boto3
from botocore.exceptions import ClientError
from utils import StructuredLogger, update_finding_workflow, extract_bucket_name, get_finding_fields

REGION = os.environ.get("AWS_REGION", "us-east-1")

s3 = boto3.client("s3")


def lambda_handler(event: dict, context) -> dict:
    """Entry point — orchestrates the S3 remediation playbook."""
    log = StructuredLogger("security-auto-s3-remediation", context)
    finding = get_finding_fields(event)
    bucket_name = extract_bucket_name(finding["resource_id"])

    log.info(
        "REMEDIATION_START",
        f"S3 remediation triggered for bucket '{bucket_name}'",
        finding_id=finding["finding_id"],
        resource_type=finding["resource_type"],
        resource_id=bucket_name,
        severity=finding["severity"],
    )

    # ── 1. VALIDATE ──────────────────────────────────────────────────────────
    try:
        tags = _get_bucket_tags(bucket_name)
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "NoSuchBucket":
            log.warning("REMEDIATION_SKIPPED", f"Bucket '{bucket_name}' no longer exists — skipping", resource_id=bucket_name)
            return _result("SKIPPED", bucket_name, "bucket_not_found")
        raise

    if tags.get("AutoRemediationExclude", "").lower() == "true":
        log.info("REMEDIATION_SKIPPED", f"Bucket '{bucket_name}' tagged AutoRemediationExclude=true — skipping", resource_id=bucket_name)
        return _result("SKIPPED", bucket_name, "excluded_by_tag")

    # ── 2. SAFETY CHECK ───────────────────────────────────────────────────────
    # If website hosting is enabled and bucket is intentionally public, treat as false positive
    if tags.get("PublicAccess", "").lower() == "intentional":
        log.info("REMEDIATION_SKIPPED", f"Bucket '{bucket_name}' tagged PublicAccess=Intentional — false positive, skipping", resource_id=bucket_name)
        return _result("SKIPPED", bucket_name, "intentional_public_false_positive")

    website_enabled = _has_website_hosting(bucket_name)
    if website_enabled and tags.get("Environment", "").lower() == "production":
        log.warning(
            "REMEDIATION_SKIPPED",
            f"Bucket '{bucket_name}' has website hosting enabled in Production — escalation required",
            resource_id=bucket_name,
        )
        return _result("SKIPPED", bucket_name, "production_website_requires_approval")

    # ── 3. LOG ────────────────────────────────────────────────────────────────
    log.info("REMEDIATION_START", f"Applying Block Public Access to bucket '{bucket_name}'", resource_id=bucket_name)

    # ── 4. EXECUTE ────────────────────────────────────────────────────────────
    try:
        # Block all four public access settings (idempotent)
        s3.put_bucket_public_access_block(
            Bucket=bucket_name,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            },
        )

        # Set ACL to private (idempotent)
        try:
            s3.put_bucket_acl(Bucket=bucket_name, ACL="private")
        except ClientError as exc:
            # Object ownership settings may prevent ACL changes — not fatal
            if "AccessControlListNotSupported" in exc.response["Error"]["Code"]:
                log.warning("REMEDIATION_START", f"ACL change skipped for '{bucket_name}' — object ownership disables ACLs", resource_id=bucket_name)
            else:
                raise

    except ClientError as exc:
        log.error(
            "REMEDIATION_FAILED",
            f"Failed to block public access on '{bucket_name}': {exc.response['Error']['Message']}",
            resource_id=bucket_name,
            outcome="FAILED",
        )
        return _result("FAILED", bucket_name, "block_public_access", error=str(exc))

    # ── 5. VERIFY ─────────────────────────────────────────────────────────────
    verified = _verify_blocked(bucket_name)
    if not verified:
        log.error("REMEDIATION_FAILED", f"Verification failed — public access block not confirmed on '{bucket_name}'", resource_id=bucket_name, outcome="FAILED")
        return _result("FAILED", bucket_name, "block_public_access", error="post-apply verification failed")

    # ── 6. LOG ────────────────────────────────────────────────────────────────
    log.info(
        "REMEDIATION_SUCCESS",
        f"S3 public access blocked and ACL set to private for '{bucket_name}'",
        resource_id=bucket_name,
        action_taken="s3_block_public_access",
        outcome="SUCCESS",
    )

    # Update Security Hub finding
    if finding["finding_id"] != "unknown" and finding["product_arn"]:
        try:
            update_finding_workflow(
                finding["finding_id"],
                finding["product_arn"],
                "RESOLVED",
                "Auto-remediated by SecurityAutomation pipeline — s3_remediation playbook",
                region=REGION,
            )
        except ClientError:
            pass  # Non-fatal — pipeline continues

    return _result("SUCCESS", bucket_name, "s3_block_public_access")


# ── HELPERS ───────────────────────────────────────────────────────────────────

def _get_bucket_tags(bucket_name: str) -> dict:
    """Return bucket tags as a flat dict. Returns {} if no tags exist."""
    try:
        response = s3.get_bucket_tagging(Bucket=bucket_name)
        return {t["Key"]: t["Value"] for t in response.get("TagSet", [])}
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "NoSuchTagSet":
            return {}
        raise


def _has_website_hosting(bucket_name: str) -> bool:
    """Return True if the bucket has static website hosting enabled."""
    try:
        s3.get_bucket_website(Bucket=bucket_name)
        return True
    except ClientError:
        return False


def _verify_blocked(bucket_name: str) -> bool:
    """Verify that all four Block Public Access settings are enabled."""
    try:
        resp = s3.get_bucket_public_access_block(Bucket=bucket_name)
        cfg = resp["PublicAccessBlockConfiguration"]
        return all([
            cfg.get("BlockPublicAcls"),
            cfg.get("IgnorePublicAcls"),
            cfg.get("BlockPublicPolicy"),
            cfg.get("RestrictPublicBuckets"),
        ])
    except ClientError:
        return False


def _result(status: str, resource_id: str, action: str, error: str = None) -> dict:
    return {
        "status": status,
        "resource_id": resource_id,
        "resource_type": "AwsS3Bucket",
        "action_taken": action,
        "error": error,
    }
