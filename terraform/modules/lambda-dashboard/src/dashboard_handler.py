"""
Dashboard Lambda — serves the web UI and handles API calls.

Routes (all via API Gateway proxy):
  GET  /dashboard              → HTML dashboard page
  GET  /dashboard/api/findings → list all findings
  GET  /dashboard/api/findings/{id} → single finding
  POST /dashboard/api/findings/{id}/action → approve/reject/manual
  GET  /dashboard/api/settings → get settings
  PUT  /dashboard/api/settings → update settings
"""
import json
import os
import time
import boto3
from datetime import datetime, timezone
from boto3.dynamodb.conditions import Key

FINDINGS_TABLE = os.environ["FINDINGS_TABLE"]
SETTINGS_TABLE = os.environ["SETTINGS_TABLE"]
AWS_REGION_NAME = os.environ.get("AWS_REGION", "us-east-1")

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION_NAME)
sfn = boto3.client("stepfunctions", region_name=AWS_REGION_NAME)

findings_table = dynamodb.Table(FINDINGS_TABLE)
settings_table = dynamodb.Table(SETTINGS_TABLE)


# ── HELPERS ────────────────────────────────────────────────────────────────────

def respond(status_code, body, content_type="application/json"):
    headers = {
        "Content-Type": content_type,
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "GET,POST,PUT,OPTIONS",
    }
    if content_type == "application/json":
        body = json.dumps(body, default=str)
    return {"statusCode": status_code, "headers": headers, "body": body}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def ttl_30_days():
    return int(time.time()) + 30 * 24 * 3600


# ── ROUTE HANDLERS ─────────────────────────────────────────────────────────────

def get_dashboard_html():
    """Return the embedded HTML dashboard page."""
    from dashboard_html import DASHBOARD_HTML
    return respond(200, DASHBOARD_HTML, content_type="text/html")


def list_findings():
    result = findings_table.scan()
    items = result.get("Items", [])
    # sort newest first
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return respond(200, {"findings": items})


def get_finding(finding_id):
    result = findings_table.get_item(Key={"finding_id": finding_id})
    item = result.get("Item")
    if not item:
        return respond(404, {"error": "Finding not found"})
    return respond(200, item)


def take_action(finding_id, body_str):
    try:
        body = json.loads(body_str or "{}")
    except json.JSONDecodeError:
        return respond(400, {"error": "Invalid JSON body"})

    action = body.get("action", "").lower()   # approve | reject | manual
    action_id = body.get("action_id")         # int, for approve

    if action not in ("approve", "reject", "manual"):
        return respond(400, {"error": "action must be approve, reject, or manual"})

    # Read finding to get task_token
    result = findings_table.get_item(Key={"finding_id": finding_id})
    item = result.get("Item")
    if not item:
        return respond(404, {"error": "Finding not found"})

    task_token = item.get("task_token")
    if not task_token:
        return respond(400, {"error": "No pending approval token for this finding"})

    if item.get("status") != "PENDING_APPROVAL":
        return respond(400, {"error": f"Finding is not pending approval (status={item.get('status')})"})

    # Send decision to Step Functions
    if action == "approve":
        task_output = json.dumps({
            "admin_decision": "APPROVED",
            "approved_action": int(action_id) if action_id is not None else 1,
        })
    elif action == "reject":
        task_output = json.dumps({"admin_decision": "REJECTED"})
    else:
        task_output = json.dumps({"admin_decision": "MANUAL"})

    try:
        sfn.send_task_success(taskToken=task_token, output=task_output)
    except sfn.exceptions.TaskTimedOut:
        return respond(410, {"error": "Approval window has expired (1-hour timeout exceeded)"})
    except sfn.exceptions.InvalidToken:
        return respond(410, {"error": "Invalid or already-used approval token"})
    except Exception as e:
        return respond(500, {"error": str(e)})

    # Update finding status in DynamoDB
    new_status = "APPROVED" if action == "approve" else ("REJECTED" if action == "reject" else "MANUAL_REVIEW")
    findings_table.update_item(
        Key={"finding_id": finding_id},
        UpdateExpression="SET #s = :s, action_taken = :a, updated_at = :u REMOVE task_token",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":s": new_status,
            ":a": action,
            ":u": now_iso(),
        },
    )

    return respond(200, {"status": "ok", "action": action, "finding_id": finding_id})


def get_settings():
    result = settings_table.get_item(Key={"setting_key": "email_notifications"})
    item = result.get("Item", {"setting_key": "email_notifications", "value": "false"})
    return respond(200, item)


def update_settings(body_str):
    try:
        body = json.loads(body_str or "{}")
    except json.JSONDecodeError:
        return respond(400, {"error": "Invalid JSON body"})

    value = "true" if body.get("email_notifications") else "false"
    settings_table.put_item(Item={
        "setting_key": "email_notifications",
        "value": value,
        "updated_at": now_iso(),
    })
    return respond(200, {"setting_key": "email_notifications", "value": value})


# ── MAIN HANDLER ───────────────────────────────────────────────────────────────

def lambda_handler(event, context):
    method = event.get("httpMethod", "GET")
    path = event.get("path", "/dashboard")
    body = event.get("body") or ""

    # OPTIONS pre-flight
    if method == "OPTIONS":
        return respond(200, "")

    # Normalize path
    path = path.rstrip("/") or "/dashboard"

    # Route: serve HTML dashboard
    if method == "GET" and path in ("/dashboard", "/prod/dashboard"):
        return get_dashboard_html()

    # Route: list findings
    if method == "GET" and path.endswith("/api/findings") and not path.endswith("/action"):
        # Check if there's a finding_id in path
        parts = path.split("/")
        api_idx = next((i for i, p in enumerate(parts) if p == "api"), -1)
        if api_idx >= 0 and len(parts) > api_idx + 2:
            finding_id = parts[api_idx + 2]
            return get_finding(finding_id)
        return list_findings()

    # Route: single finding
    if method == "GET" and "/api/findings/" in path and not path.endswith("action"):
        finding_id = path.split("/api/findings/")[-1].split("/")[0]
        return get_finding(finding_id)

    # Route: take action on finding
    if method == "POST" and "/api/findings/" in path and path.endswith("/action"):
        finding_id = path.split("/api/findings/")[-1].replace("/action", "")
        return take_action(finding_id, body)

    # Route: settings GET
    if method == "GET" and path.endswith("/api/settings"):
        return get_settings()

    # Route: settings PUT
    if method == "PUT" and path.endswith("/api/settings"):
        return update_settings(body)

    return respond(404, {"error": f"Unknown route: {method} {path}"})
