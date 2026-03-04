"""
approval_handler.py — Admin approval handler Lambda (API Gateway backend).

Called when the admin clicks an approve/reject/manual link from the notification email.
Sends the task result back to Step Functions via the callback task token.

API Gateway routes (all GET with query parameters):
  GET /approve?token={task_token}&action={action_id}  → approve with action N
  GET /reject?token={task_token}                       → reject (false positive)
  GET /manual?token={task_token}                       → admin will fix manually

Environment variables:
  AWS_REGION — AWS region

Input event (API Gateway proxy integration):
  {
    "path": "/approve" | "/reject" | "/manual",
    "queryStringParameters": { "token": "...", "action": "1" }
  }

Returns:
  API Gateway response with HTML confirmation page (statusCode 200).
"""

import json
import logging
import os
import urllib.parse
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = os.environ.get("AWS_REGION", "us-east-1")

sfn = boto3.client("stepfunctions", region_name=REGION)


def lambda_handler(event: dict, context) -> dict:
    """Entry point — handle the admin's approval/rejection click."""
    path = event.get("path", event.get("rawPath", "/unknown"))
    params = event.get("queryStringParameters") or {}

    raw_token = params.get("token", "")
    action_str = params.get("action", "1")

    if not raw_token:
        return _html_response(400, "Error", "Missing task token — link may have expired.")

    # URL-decode the token (it was encoded when building the approval link)
    task_token = urllib.parse.unquote(raw_token)

    logger.info(json.dumps({
        "event_type": "ADMIN_ACTION",
        "path": path,
        "action": action_str,
        "message": f"Admin clicked {path} with action={action_str}",
    }))

    try:
        action_id = int(action_str) if action_str.isdigit() else 1
    except (ValueError, AttributeError):
        action_id = 1

    # ── ROUTE BY PATH ─────────────────────────────────────────────────────────
    if "/approve" in path:
        return _handle_approve(task_token, action_id)
    elif "/reject" in path:
        return _handle_reject(task_token)
    elif "/manual" in path:
        return _handle_manual(task_token)
    else:
        return _html_response(404, "Not Found", "Unknown approval action.")


# ── ACTION HANDLERS ───────────────────────────────────────────────────────────

def _handle_approve(task_token: str, action_id: int) -> dict:
    """Send task success — admin approved a specific remediation action."""
    task_output = json.dumps({
        "admin_decision": "APPROVED",
        "approved_action": action_id,
    })
    try:
        sfn.send_task_success(taskToken=task_token, output=task_output)
        logger.info(json.dumps({"event_type": "ADMIN_APPROVED", "action": action_id, "message": f"Admin approved action {action_id}"}))
        return _html_response(
            200,
            "✅ Action Approved",
            f"Action {action_id} has been approved. The security automation pipeline will execute the remediation now.",
        )
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        if code in ("TaskTimedOut", "InvalidToken"):
            return _html_response(410, "Link Expired", "This approval link has expired or was already used. The pipeline may have already timed out.")
        return _html_response(500, "Error", f"Failed to process approval: {exc.response['Error']['Message']}")


def _handle_reject(task_token: str) -> dict:
    """Send task success with REJECTED decision — suppress finding as false positive."""
    task_output = json.dumps({
        "admin_decision": "REJECTED",
        "approved_action": None,
    })
    try:
        sfn.send_task_success(taskToken=task_token, output=task_output)
        logger.info(json.dumps({"event_type": "ADMIN_REJECTED", "message": "Admin rejected finding as false positive"}))
        return _html_response(
            200,
            "✅ Finding Rejected",
            "The finding has been marked as a false positive and will be suppressed in Security Hub. No remediation action will be taken.",
        )
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        if code in ("TaskTimedOut", "InvalidToken"):
            return _html_response(410, "Link Expired", "This rejection link has expired or was already used.")
        return _html_response(500, "Error", f"Failed to process rejection: {exc.response['Error']['Message']}")


def _handle_manual(task_token: str) -> dict:
    """Send task success with MANUAL decision — admin will fix it themselves."""
    task_output = json.dumps({
        "admin_decision": "MANUAL",
        "approved_action": None,
    })
    try:
        sfn.send_task_success(taskToken=task_token, output=task_output)
        logger.info(json.dumps({"event_type": "ADMIN_MANUAL", "message": "Admin chose to handle remediation manually"}))
        return _html_response(
            200,
            "✅ Manual Review Confirmed",
            "You have chosen to handle this finding manually. The pipeline has been notified. "
            "Please investigate and remediate the finding within your agreed SLA.",
        )
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        if code in ("TaskTimedOut", "InvalidToken"):
            return _html_response(410, "Link Expired", "This link has expired or was already used.")
        return _html_response(500, "Error", f"Failed to confirm manual decision: {exc.response['Error']['Message']}")


# ── HTML RESPONSE BUILDER ─────────────────────────────────────────────────────

def _html_response(status_code: int, heading: str, message: str) -> dict:
    """Build an API Gateway Lambda proxy response with a simple HTML page."""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Security Automation — {heading}</title>
  <style>
    body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 80px auto; padding: 0 20px; color: #333; }}
    h1 {{ font-size: 1.5rem; }}
    .box {{ background: #f4f4f4; border-left: 4px solid #0073bb; padding: 16px; border-radius: 4px; }}
    .footer {{ margin-top: 40px; font-size: 0.8rem; color: #888; }}
  </style>
</head>
<body>
  <h1>{heading}</h1>
  <div class="box"><p>{message}</p></div>
  <div class="footer">AWS Security Automation Pipeline — automated response system</div>
</body>
</html>"""
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "text/html; charset=utf-8"},
        "body": html,
    }
