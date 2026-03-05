"""
send_notification.py — stores findings to DynamoDB and optionally sends SNS email.

Called by Step Functions NotifyAdmin state (waitForTaskToken).
Email is only sent when the 'email_notifications' setting is 'true' in DynamoDB.

Input event:
  {
    "finding":     { finding_id, resource_type, resource_id, severity, title, description, ... },
    "ai_analysis": { risk_level, analysis, recommended_actions, escalation_reason, ... },
    "task_token":  "step-functions-callback-token..."   (may be absent for auto-remediations)
  }
"""

import json
import logging
import os
import time
import urllib.parse
import boto3
from datetime import datetime, timezone
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

SNS_TOPIC_ARN        = os.environ.get("SNS_TOPIC_ARN", "")
API_GATEWAY_BASE_URL = os.environ.get("API_GATEWAY_BASE_URL", "").rstrip("/")
FINDINGS_TABLE       = os.environ.get("FINDINGS_TABLE", "")
SETTINGS_TABLE       = os.environ.get("SETTINGS_TABLE", "")
AWS_REGION_NAME      = os.environ.get("AWS_REGION", "us-east-1")

sns      = boto3.client("sns", region_name=AWS_REGION_NAME)
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION_NAME)

SEVERITY_EMOJI = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}


# ── HELPERS ────────────────────────────────────────────────────────────────────

def now_iso():
    return datetime.now(timezone.utc).isoformat()


def ttl_30_days():
    return int(time.time()) + 30 * 24 * 3600


def is_email_enabled():
    if not SETTINGS_TABLE:
        return False
    try:
        table = dynamodb.Table(SETTINGS_TABLE)
        result = table.get_item(Key={"setting_key": "email_notifications"})
        return result.get("Item", {}).get("value", "false") == "true"
    except Exception:
        return False


def store_finding(finding, ai_analysis, task_token, status):
    if not FINDINGS_TABLE:
        return
    table = dynamodb.Table(FINDINGS_TABLE)

    rec_actions = ai_analysis.get("recommended_actions", [])
    if isinstance(rec_actions, str):
        try:
            rec_actions = json.loads(rec_actions)
        except Exception:
            rec_actions = []

    item = {
        "finding_id":          finding.get("finding_id", "unknown"),
        "resource_type":       finding.get("resource_type", ""),
        "resource_id":         finding.get("resource_id", ""),
        "severity":            finding.get("severity", "MEDIUM"),
        "title":               finding.get("title", finding.get("description", finding.get("finding_id", ""))),
        "description":         finding.get("description", ""),
        "ai_analysis":         json.dumps(ai_analysis),
        "recommended_actions": json.dumps(rec_actions),
        "risk_level":          ai_analysis.get("risk_level", ""),
        "status":              status,
        "created_at":          now_iso(),
        "updated_at":          now_iso(),
        "ttl_epoch":           ttl_30_days(),
        "environment":         finding.get("environment", ""),
        "action_taken":        "",
    }
    if task_token:
        item["task_token"] = task_token

    table.put_item(Item=item)
    _log("FINDING_STORED", item["finding_id"], item["resource_type"],
         item["resource_id"], item["severity"], f"Stored to DynamoDB, status={status}")


def _build_email_body(finding, ai_analysis, task_token):
    finding_id        = finding.get("finding_id", "unknown")
    resource_type     = finding.get("resource_type", "Unknown")
    resource_id       = finding.get("resource_id", "N/A")
    severity          = finding.get("severity", "HIGH")
    title             = finding.get("title", "Security Finding")
    description       = finding.get("description", "")
    analysis_text     = ai_analysis.get("analysis", "No AI analysis available.")
    escalation_reason = ai_analysis.get("escalation_reason", "")
    risk_level        = ai_analysis.get("risk_level", severity)
    emoji             = SEVERITY_EMOJI.get(severity.upper(), "⚠️")

    rec_actions = ai_analysis.get("recommended_actions", [])
    if isinstance(rec_actions, str):
        try:
            rec_actions = json.loads(rec_actions)
        except Exception:
            rec_actions = []

    encoded_token  = urllib.parse.quote(task_token, safe="")
    dashboard_url  = f"{API_GATEWAY_BASE_URL}/dashboard"
    reject_link    = f"{API_GATEWAY_BASE_URL}/reject?token={encoded_token}"
    manual_link    = f"{API_GATEWAY_BASE_URL}/manual?token={encoded_token}"

    lines = [
        "=" * 70,
        f"  {emoji} SECURITY ALERT — ACTION REQUIRED",
        "=" * 70,
        "",
        f"FINDING   : {title}",
        f"RESOURCE  : {resource_type} — {resource_id}",
        f"SEVERITY  : {severity}  |  AI RISK: {risk_level}",
        f"FINDING ID: {finding_id}",
        "",
        "─" * 70,
        "  DESCRIPTION",
        "─" * 70,
        description or "(no description)",
        "",
        "─" * 70,
        "  AI ANALYSIS",
        "─" * 70,
        analysis_text,
    ]
    if escalation_reason:
        lines += ["", f"WHY ESCALATED: {escalation_reason}"]
    lines += ["", "─" * 70, "  RECOMMENDED ACTIONS (click to approve)", "─" * 70]
    for action in rec_actions:
        action_id   = action.get("action_id", 1)
        action_desc = action.get("description", f"Action {action_id}")
        approve_url = f"{API_GATEWAY_BASE_URL}/approve?token={encoded_token}&action={action_id}"
        lines += [f"  [{action_id}] {action_desc}", f"      APPROVE -> {approve_url}", ""]
    lines += [
        f"  [M] I will handle this manually:",
        f"      MANUAL  -> {manual_link}",
        "",
        f"  [R] This is a false positive:",
        f"      REJECT  -> {reject_link}",
        "",
        "─" * 70,
        "  OR USE THE DASHBOARD (recommended):",
        f"  {dashboard_url}",
        "─" * 70,
        "",
        "  Approval links expire in 60 minutes.",
        "=" * 70,
    ]
    return "\n".join(lines)


# ── MAIN HANDLER ───────────────────────────────────────────────────────────────

def lambda_handler(event, context):
    finding     = event.get("finding", {})
    ai_analysis = event.get("ai_analysis", {})
    task_token  = event.get("task_token", "")
    status_hint = event.get("status_hint", "PENDING_APPROVAL")

    finding_id    = finding.get("finding_id", "unknown")
    resource_type = finding.get("resource_type", "Unknown")
    resource_id   = finding.get("resource_id", "N/A")
    severity      = finding.get("severity", "HIGH")

    status = "PENDING_APPROVAL" if task_token else status_hint

    # 1. Always store to DynamoDB (regardless of email toggle)
    try:
        store_finding(finding, ai_analysis, task_token, status)
    except Exception as exc:
        logger.warning(f"DynamoDB write failed: {exc}")

    result = {"status": "STORED", "finding_id": finding_id}

    # 2. Send email only if toggle is ON and this is a pending-approval item
    if task_token and is_email_enabled() and SNS_TOPIC_ARN:
        try:
            emoji   = SEVERITY_EMOJI.get(severity.upper(), "⚠️")
            subject = (f"{emoji} [{severity}] Action Required: "
                       f"{resource_id.split('/')[-1].split(':')[-1][:40]}")[:100]
            body    = _build_email_body(finding, ai_analysis, task_token)
            resp    = sns.publish(TopicArn=SNS_TOPIC_ARN, Subject=subject, Message=body)
            _log("EMAIL_SENT", finding_id, resource_type, resource_id, severity,
                 f"SNS email sent MessageId={resp['MessageId']}")
            result["email_sent"]  = True
            result["message_id"]  = resp["MessageId"]
        except ClientError as exc:
            logger.warning(f"SNS publish failed: {exc}")
            result["email_sent"] = False
    else:
        result["email_sent"] = False
        reason = "email_disabled" if not is_email_enabled() else ("no_task_token" if not task_token else "no_topic")
        _log("EMAIL_SKIPPED", finding_id, resource_type, resource_id, severity, reason)

    return result


def _log(event_type, finding_id, resource_type, resource_id, severity, message):
    logger.info(json.dumps({
        "event_type": event_type, "finding_id": finding_id,
        "resource_type": resource_type, "resource_id": resource_id,
        "severity": severity, "message": message,
    }))
