"""
send_notification.py — Admin notification Lambda.

Builds a rich plain-text + HTML email with the AI analysis and clickable
approve/reject links, then publishes it to the SNS admin alerts topic.

The task_token (Step Functions callback token) is URL-encoded into the
approval links so the admin's click routes back to the approval Lambda.

Environment variables:
  SNS_TOPIC_ARN        — ARN of security-automation-admin-alerts SNS topic
  API_GATEWAY_BASE_URL — Base URL of the approval API Gateway (e.g. https://xxx.execute-api...)
  AWS_REGION           — AWS region

Input event:
  {
    "finding":     { finding_id, resource_type, resource_id, severity, title, description, ... },
    "ai_analysis": { risk_level, analysis, recommended_actions, escalation_reason, ... },
    "task_token":  "step-functions-callback-token-base64..."
  }

Returns:
  { "status": "SENT", "message_id": "...", "recipient_topic": "..." }
"""

import json
import logging
import os
import urllib.parse
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "")
API_GATEWAY_BASE_URL = os.environ.get("API_GATEWAY_BASE_URL", "").rstrip("/")
REGION = os.environ.get("AWS_REGION", "us-east-1")

sns = boto3.client("sns", region_name=REGION)

SEVERITY_EMOJI = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}


def lambda_handler(event: dict, context) -> dict:
    """Entry point — build and send the admin notification email."""
    finding = event.get("finding", {})
    ai_analysis = event.get("ai_analysis", {})
    task_token = event.get("task_token", "")

    resource_type = finding.get("resource_type", "Unknown")
    resource_id = finding.get("resource_id", "unknown")
    finding_id = finding.get("finding_id", "unknown")
    severity = finding.get("severity", "HIGH")
    title = finding.get("title", "Security Finding Detected")
    description = finding.get("description", "")

    risk_level = ai_analysis.get("risk_level", severity)
    analysis_text = ai_analysis.get("analysis", "No AI analysis available.")
    escalation_reason = ai_analysis.get("escalation_reason", "")
    recommended_actions = ai_analysis.get("recommended_actions", [])

    emoji = SEVERITY_EMOJI.get(severity, "⚠️")

    _log("ADMIN_NOTIFIED", finding_id, resource_type, resource_id, severity,
         f"Building admin notification for '{resource_id}'")

    # ── BUILD APPROVAL LINKS ──────────────────────────────────────────────────
    encoded_token = urllib.parse.quote(task_token, safe="")
    approve_links = []
    for action in recommended_actions:
        action_id = action.get("action_id", 1)
        desc = action.get("description", f"Action {action_id}")
        link = f"{API_GATEWAY_BASE_URL}/approve?token={encoded_token}&action={action_id}"
        approve_links.append({"action_id": action_id, "description": desc, "link": link})

    reject_link = f"{API_GATEWAY_BASE_URL}/reject?token={encoded_token}"
    manual_link = f"{API_GATEWAY_BASE_URL}/manual?token={encoded_token}"

    # ── BUILD EMAIL SUBJECT ───────────────────────────────────────────────────
    subject = f"{emoji} [{severity}] Security Finding — Action Required: {_short_resource(resource_id)}"
    # SNS subject limit = 100 chars
    subject = subject[:100]

    # ── BUILD EMAIL BODY ──────────────────────────────────────────────────────
    body = _build_email_body(
        emoji=emoji,
        severity=severity,
        risk_level=risk_level,
        title=title,
        description=description,
        resource_type=resource_type,
        resource_id=resource_id,
        finding_id=finding_id,
        analysis_text=analysis_text,
        escalation_reason=escalation_reason,
        approve_links=approve_links,
        reject_link=reject_link,
        manual_link=manual_link,
    )

    # ── PUBLISH TO SNS ────────────────────────────────────────────────────────
    try:
        response = sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=subject,
            Message=body,
        )
        message_id = response.get("MessageId", "unknown")
    except ClientError as exc:
        _log("ERROR", finding_id, resource_type, resource_id, severity,
             f"Failed to publish SNS notification: {exc.response['Error']['Message']}")
        raise

    _log("ADMIN_NOTIFIED", finding_id, resource_type, resource_id, severity,
         f"Admin notification sent — MessageId={message_id}")

    return {
        "status": "SENT",
        "message_id": message_id,
        "recipient_topic": SNS_TOPIC_ARN,
    }


# ── EMAIL BUILDER ─────────────────────────────────────────────────────────────

def _build_email_body(
    emoji, severity, risk_level, title, description, resource_type, resource_id,
    finding_id, analysis_text, escalation_reason, approve_links, reject_link, manual_link,
) -> str:
    """Build the plain-text email body for admin review."""
    lines = [
        f"{'='*70}",
        f"  {emoji} SECURITY ALERT — ACTION REQUIRED",
        f"{'='*70}",
        "",
        f"FINDING:   {title}",
        f"RESOURCE:  {resource_type} — {resource_id}",
        f"SEVERITY:  {severity}  |  AI RISK LEVEL: {risk_level}",
        f"FINDING ID: {finding_id}",
        "",
        f"{'─'*70}",
        "  DESCRIPTION",
        f"{'─'*70}",
        description or "(no description)",
        "",
        f"{'─'*70}",
        "  AI ANALYSIS",
        f"{'─'*70}",
        analysis_text,
    ]

    if escalation_reason:
        lines += ["", f"WHY ESCALATED: {escalation_reason}"]

    lines += [
        "",
        f"{'─'*70}",
        "  RECOMMENDED ACTIONS",
        f"{'─'*70}",
    ]

    if approve_links:
        for item in approve_links:
            lines.append(f"  [{item['action_id']}] {item['description']}")
            lines.append(f"      APPROVE → {item['link']}")
            lines.append("")
    else:
        lines.append("  No specific actions available — manual review recommended.")
        lines.append("")

    lines += [
        f"  [M] I will handle this manually:",
        f"      MANUAL  → {manual_link}",
        "",
        f"  [R] This is a false positive / reject:",
        f"      REJECT  → {reject_link}",
        "",
        f"{'─'*70}",
        "  ⏰ Auto-skip in 60 minutes if no response.",
        f"{'─'*70}",
        "",
        "This notification was generated by the AWS Security Automation Pipeline.",
    ]

    return "\n".join(lines)


# ── HELPERS ───────────────────────────────────────────────────────────────────

def _short_resource(resource_id: str) -> str:
    """Return last segment of ARN or full ID if not an ARN."""
    return resource_id.split("/")[-1].split(":")[-1][:40]


def _log(event_type, finding_id, resource_type, resource_id, severity, message):
    logger.info(json.dumps({
        "event_type": event_type,
        "finding_id": finding_id,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "severity": severity,
        "message": message,
    }))
