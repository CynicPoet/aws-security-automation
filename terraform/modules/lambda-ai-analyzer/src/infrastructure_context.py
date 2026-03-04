"""
infrastructure_context.py — Build infrastructure context for AI analysis.

Gathers resource details, tags, and dependencies so the AI can make
context-aware decisions (e.g., detect false positives, assess blast radius).
"""

import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timezone


def build_infrastructure_context(finding: dict, region: str = "us-east-1") -> dict:
    """
    Gather context about the affected resource before calling the AI.

    Args:
        finding: Normalized finding dict with resource_type and resource_id.
        region:  AWS region.

    Returns:
        context dict with resource_tags, resource_details, and type-specific sub-context.
    """
    resource_type = finding.get("resource_type", "")
    resource_id = finding.get("resource_id", "")

    context = {
        "account_info": {
            "region": region,
            "environment": "Development/Testing",
            "note": "Demo environment for security automation capstone project",
        },
        "resource_type": resource_type,
        "resource_id": resource_id,
        "resource_tags": {},
        "resource_details": {},
    }

    try:
        if "S3" in resource_type:
            context.update(_build_s3_context(resource_id))
        elif "Iam" in resource_type:
            context.update(_build_iam_context(resource_id))
        elif "SecurityGroup" in resource_type:
            context.update(_build_vpc_context(resource_id, region))
    except Exception as exc:
        # Context gathering must never block the AI call
        context["context_error"] = str(exc)

    return context


# ── S3 CONTEXT ────────────────────────────────────────────────────────────────

def _build_s3_context(resource_id: str) -> dict:
    """Gather S3 bucket context."""
    bucket_name = resource_id.split(":::")[-1] if ":::" in resource_id else resource_id
    s3 = boto3.client("s3")
    ctx = {"resource_details": {"bucket_name": bucket_name}}

    # Tags
    try:
        resp = s3.get_bucket_tagging(Bucket=bucket_name)
        ctx["resource_tags"] = {t["Key"]: t["Value"] for t in resp.get("TagSet", [])}
    except ClientError:
        ctx["resource_tags"] = {}

    # Website hosting
    website_enabled = False
    try:
        s3.get_bucket_website(Bucket=bucket_name)
        website_enabled = True
    except ClientError:
        pass

    # Bucket policy exists?
    policy_exists = False
    try:
        s3.get_bucket_policy(Bucket=bucket_name)
        policy_exists = True
    except ClientError:
        pass

    ctx["s3_context"] = {
        "bucket_name": bucket_name,
        "website_hosting_enabled": website_enabled,
        "bucket_policy_exists": policy_exists,
        "has_cloudfront_origin": False,  # Simplified for demo scope
        "intentional_public_tag": ctx["resource_tags"].get("PublicAccess", "").lower() == "intentional",
    }
    return ctx


# ── IAM CONTEXT ───────────────────────────────────────────────────────────────

def _build_iam_context(resource_id: str) -> dict:
    """Gather IAM user context."""
    username = resource_id.split("user/")[-1] if "user/" in resource_id else resource_id
    iam = boto3.client("iam")
    ctx = {"resource_details": {"username": username}}

    # Tags
    try:
        resp = iam.list_user_tags(UserName=username)
        ctx["resource_tags"] = {t["Key"]: t["Value"] for t in resp.get("Tags", [])}
    except ClientError:
        ctx["resource_tags"] = {}

    # Access keys
    key_info = []
    try:
        keys = iam.list_access_keys(UserName=username).get("AccessKeyMetadata", [])
        for key in keys:
            key_detail = {
                "key_id": key["AccessKeyId"],
                "status": key["Status"],
                "created": key["CreateDate"].isoformat() if hasattr(key["CreateDate"], "isoformat") else str(key["CreateDate"]),
                "age_days": (datetime.now(timezone.utc) - key["CreateDate"]).days,
            }
            try:
                lu = iam.get_access_key_last_used(AccessKeyId=key["AccessKeyId"])
                last_used = lu.get("AccessKeyLastUsed", {})
                key_detail["last_used_date"] = str(last_used.get("LastUsedDate", "never"))
                key_detail["last_used_service"] = last_used.get("ServiceName", "N/A")
            except ClientError:
                pass
            key_info.append(key_detail)
    except ClientError:
        pass

    # Attached policies
    attached_policies = []
    try:
        resp = iam.list_attached_user_policies(UserName=username)
        attached_policies = [p["PolicyName"] for p in resp.get("AttachedPolicies", [])]
    except ClientError:
        pass

    tags = ctx["resource_tags"]
    ctx["iam_context"] = {
        "username": username,
        "access_keys": key_info,
        "attached_policies": attached_policies,
        "is_service_account": tags.get("ServiceAccount", "").lower() == "true",
        "is_ci_pipeline": tags.get("Role", "").lower() == "ci-pipeline",
        "environment": tags.get("Environment", "unknown"),
        "has_admin_access": "AdministratorAccess" in attached_policies,
    }
    return ctx


# ── VPC CONTEXT ───────────────────────────────────────────────────────────────

def _build_vpc_context(resource_id: str, region: str) -> dict:
    """Gather Security Group context."""
    sg_id = resource_id.split("security-group/")[-1] if "security-group/" in resource_id else resource_id.split(":")[-1]
    ec2 = boto3.client("ec2", region_name=region)
    ctx = {"resource_details": {"sg_id": sg_id}}

    try:
        resp = ec2.describe_security_groups(GroupIds=[sg_id])
        sg = resp["SecurityGroups"][0]
        ctx["resource_tags"] = {t["Key"]: t["Value"] for t in sg.get("Tags", [])}

        # Attached instances
        instances_resp = ec2.describe_instances(
            Filters=[{"Name": "instance.group-id", "Values": [sg_id]}]
        )
        instance_count = sum(
            len(r["Instances"]) for r in instances_resp.get("Reservations", [])
        )

        # Attached ENIs
        eni_resp = ec2.describe_network_interfaces(
            Filters=[{"Name": "group-id", "Values": [sg_id]}]
        )
        eni_count = len(eni_resp.get("NetworkInterfaces", []))

        tags = ctx["resource_tags"]
        ctx["vpc_context"] = {
            "sg_id": sg_id,
            "sg_name": sg.get("GroupName", sg_id),
            "vpc_id": sg.get("VpcId", "unknown"),
            "is_default_sg": sg.get("GroupName") == "default",
            "attached_instance_count": instance_count,
            "attached_eni_count": eni_count,
            "environment": tags.get("Environment", "unknown"),
            "service": tags.get("Service", "unknown"),
            "is_production": tags.get("Environment", "").lower() == "production",
        }
    except ClientError:
        ctx["resource_tags"] = {}
        ctx["vpc_context"] = {"sg_id": sg_id, "error": "could not fetch SG details"}

    return ctx
