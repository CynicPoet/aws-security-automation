"""
utils.py — Shared utilities for all Security Automation Lambda functions.

Provides:
- StructuredLogger: JSON-formatted CloudWatch logging matching the project log schema
- update_finding_workflow: Update Security Hub finding workflow status
- extract_resource_id: Parse simple resource ID from AWS ARN
"""

import json
import logging
import os
import time
import boto3
from datetime import datetime, timezone

# ──────────────────────────────────────────────────────────────────────────────
# STRUCTURED LOGGER
# ──────────────────────────────────────────────────────────────────────────────

_root_logger = logging.getLogger()
_root_logger.setLevel(logging.INFO)


class StructuredLogger:
    """
    Emits JSON log entries matching the project's CloudWatch log schema.

    Every log call writes a structured JSON object with fields:
    timestamp, event_type, finding_id, resource_type, resource_id,
    severity, action_taken, outcome, execution_id, duration_ms, message
    """

    def __init__(self, function_name: str, context=None):
        self.function_name = function_name
        self.execution_id = getattr(context, "invoked_function_arn", "local") if context else "local"
        self._start_ms = int(time.time() * 1000)

    def _emit(self, level: str, event_type: str, message: str, **kwargs):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "event_type": event_type,
            "function_name": self.function_name,
            "execution_id": self.execution_id,
            "duration_ms": int(time.time() * 1000) - self._start_ms,
            "message": message,
        }
        entry.update({k: v for k, v in kwargs.items() if v is not None})
        _root_logger.info(json.dumps(entry))

    def info(self, event_type: str, message: str, **kwargs):
        self._emit("INFO", event_type, message, **kwargs)

    def error(self, event_type: str, message: str, **kwargs):
        self._emit("ERROR", event_type, message, **kwargs)

    def warning(self, event_type: str, message: str, **kwargs):
        self._emit("WARNING", event_type, message, **kwargs)


# ──────────────────────────────────────────────────────────────────────────────
# SECURITY HUB HELPER
# ──────────────────────────────────────────────────────────────────────────────

def update_finding_workflow(
    finding_id: str,
    product_arn: str,
    workflow_status: str,
    note: str,
    region: str = "us-east-1",
) -> None:
    """
    Update the workflow status of a Security Hub finding.

    Args:
        finding_id:     Full ARN of the Security Hub finding.
        product_arn:    ProductArn from the finding (identifies the source).
        workflow_status: 'NEW' | 'NOTIFIED' | 'RESOLVED' | 'SUPPRESSED'
        note:           Human-readable note explaining the status change.
        region:         AWS region.
    """
    client = boto3.client("securityhub", region_name=region)
    client.batch_update_findings(
        FindingIdentifiers=[{"Id": finding_id, "ProductArn": product_arn}],
        Workflow={"Status": workflow_status},
        Note={"Text": note[:512], "UpdatedBy": "SecurityAutomation"},
    )


# ──────────────────────────────────────────────────────────────────────────────
# ARN PARSING HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def extract_bucket_name(resource_id: str) -> str:
    """
    Extract S3 bucket name from ARN or plain name.

    Examples:
        'arn:aws:s3:::my-bucket' → 'my-bucket'
        'my-bucket'              → 'my-bucket'
    """
    if resource_id.startswith("arn:aws:s3:::"):
        return resource_id.split(":::")[1]
    return resource_id


def extract_iam_username(resource_id: str) -> str:
    """
    Extract IAM username from ARN or plain name.

    Examples:
        'arn:aws:iam::123456789012:user/my-user' → 'my-user'
        'my-user' → 'my-user'
    """
    if "user/" in resource_id:
        return resource_id.split("user/")[-1]
    return resource_id


def extract_sg_id(resource_id: str) -> str:
    """
    Extract EC2 security group ID from ARN or plain ID.

    Examples:
        'arn:aws:ec2:us-east-1:123:security-group/sg-0abc' → 'sg-0abc'
        'sg-0abc' → 'sg-0abc'
    """
    if "security-group/" in resource_id:
        return resource_id.split("security-group/")[-1]
    # resource_id may be 'sg-xxx' directly
    parts = resource_id.split(":")
    for part in parts:
        if part.startswith("sg-"):
            return part
    return resource_id


def write_finding_status(
    table_name: str,
    finding: dict,
    ai_analysis: dict,
    status: str,
) -> None:
    """
    Write a finding record to the DynamoDB findings table (best-effort, non-fatal).
    Used by remediation Lambdas to make auto-remediated findings visible in the dashboard.
    """
    if not table_name:
        return
    try:
        region = os.environ.get("AWS_REGION", "us-east-1")
        table  = boto3.resource("dynamodb", region_name=region).Table(table_name)
        table.put_item(
            Item={
                "finding_id":          finding.get("finding_id", "unknown"),
                "resource_type":       finding.get("resource_type", ""),
                "resource_id":         finding.get("resource_id", ""),
                "severity":            finding.get("severity", "MEDIUM"),
                "title":               finding.get("title", finding.get("description", "")),
                "description":         finding.get("description", ""),
                "ai_analysis":         json.dumps(ai_analysis) if ai_analysis else "{}",
                "recommended_actions": json.dumps(ai_analysis.get("recommended_actions", [])) if ai_analysis else "[]",
                "risk_level":          (ai_analysis or {}).get("risk_level", "MEDIUM"),
                "status":              status,
                "created_at":          datetime.now(timezone.utc).isoformat(),
                "updated_at":          datetime.now(timezone.utc).isoformat(),
                "ttl_epoch":           int(time.time()) + 30 * 24 * 3600,
                "environment":         finding.get("environment", ""),
                "action_taken":        "",
            },
            ConditionExpression="attribute_not_exists(finding_id)",  # don't overwrite existing records
        )
    except Exception:
        pass  # Non-fatal — dashboard visibility is best-effort


def get_finding_fields(event: dict) -> dict:
    """
    Normalise the finding dict from an incoming Lambda event.

    The state machine always passes the finding under key 'finding'.
    Returns a flat dict with safe defaults for missing fields.
    """
    finding = event.get("finding", event)  # fallback to whole event
    return {
        "finding_id": finding.get("finding_id", finding.get("Id", "unknown")),
        "product_arn": finding.get("product_arn", finding.get("ProductArn", "")),
        "resource_type": finding.get("resource_type", finding.get("ResourceType", "Unknown")),
        "resource_id": finding.get("resource_id", finding.get("ResourceId", "unknown")),
        "resource_arn": finding.get("resource_arn", finding.get("ResourceId", "")),
        "severity": finding.get("severity", finding.get("Severity", {}).get("Label", "UNKNOWN")),
        "title": finding.get("title", finding.get("Title", "")),
        "description": finding.get("description", finding.get("Description", "")),
        "region": finding.get("region", "us-east-1"),
    }
