"""
Dashboard Lambda — web UI + all API calls.

Routes:
  GET    /dashboard                → HTML page
  GET    /dashboard/api/findings   → list all findings (JSON)
  DELETE /dashboard/api/findings   → clear all findings (demo reset)
  GET    /dashboard/api/settings   → get email setting
  PUT    /dashboard/api/settings   → update email setting
  GET    /dashboard/api/control    → pipeline status (ENABLED/DISABLED)
  POST   /dashboard/api/control    → shutdown / start / terminate pipeline
  POST   /dashboard/api/action     → approve/reject/manual  (finding_id in body)
  POST   /dashboard/api/email      → resend email for a finding
  POST   /dashboard/api/simulate   → create simulation case + start Step Functions
  DELETE /dashboard/api/simulate   → clean up simulation resource
"""

import json
import os
import time
import traceback
import urllib.request
import urllib.error
import boto3
from datetime import datetime, timezone
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr

FINDINGS_TABLE    = os.environ["FINDINGS_TABLE"]
SETTINGS_TABLE    = os.environ["SETTINGS_TABLE"]
STATE_MACHINE_ARN = os.environ.get("STATE_MACHINE_ARN", "")
EB_RULE_NAME      = os.environ.get("EB_RULE_NAME", "securityhub-finding-rule")
SNS_TOPIC_ARN     = os.environ.get("SNS_TOPIC_ARN", "")
ACCOUNT_ID        = os.environ.get("ACCOUNT_ID", "")
REGION            = os.environ.get("AWS_REGION", "us-east-1")
AI_SECRET_NAME    = "security-automation/ai-api-key"

# Claude models available (hardcoded — no public listing endpoint without paid access)
CLAUDE_MODELS = [
    {"id": "claude-haiku-4-5-20251001",  "name": "Claude Haiku 4.5  (fastest, most cost-efficient)"},
    {"id": "claude-sonnet-4-6",          "name": "Claude Sonnet 4.6 (balanced)"},
    {"id": "claude-opus-4-6",            "name": "Claude Opus 4.6   (most capable, highest cost)"},
]

dynamodb = boto3.resource("dynamodb", region_name=REGION)
sfn      = boto3.client("stepfunctions", region_name=REGION)
events   = boto3.client("events", region_name=REGION)
sns      = boto3.client("sns", region_name=REGION)
ec2      = boto3.client("ec2", region_name=REGION)
s3       = boto3.client("s3", region_name=REGION)
iam      = boto3.client("iam", region_name=REGION)
lam      = boto3.client("lambda", region_name=REGION)

findings_table = dynamodb.Table(FINDINGS_TABLE)
settings_table = dynamodb.Table(SETTINGS_TABLE)

# ── SIMULATION CASE CATALOGUE ─────────────────────────────────────────────────

SIMULATION_CASES = {
    "A1": {
        "label": "S3 Bucket — Public Access Open",
        "title": "S3 Bucket Allows Public Read Access",
        "description": "S3 bucket has Block Public Access disabled, exposing data to unauthenticated access.",
        "severity": "HIGH",
        "resource_type": "AwsS3Bucket",
        "category": "A",
    },
    "A2": {
        "label": "Security Group — SSH Open to World",
        "title": "Security Group Allows Unrestricted SSH Access (Port 22)",
        "description": "Security group allows inbound SSH (port 22) from 0.0.0.0/0, exposing instances to brute-force attacks.",
        "severity": "HIGH",
        "resource_type": "AwsEc2SecurityGroup",
        "category": "A",
    },
    "A3": {
        "label": "Security Group — All Traffic Open",
        "title": "Security Group Allows All Inbound Traffic from Internet",
        "description": "Security group allows all inbound traffic from 0.0.0.0/0 on all ports — complete exposure.",
        "severity": "CRITICAL",
        "resource_type": "AwsEc2SecurityGroup",
        "category": "A",
    },
    "B1": {
        "label": "IAM CI-Pipeline User — Active Keys",
        "title": "IAM CI-Pipeline User Has Active Access Keys — Admin Review Required",
        "description": "CI/CD pipeline IAM user has active access keys. Role=CI-Pipeline tag requires admin approval.",
        "severity": "HIGH",
        "resource_type": "AwsIamUser",
        "category": "B",
    },
    "B2": {
        "label": "Production SG — RDP Open to World",
        "title": "Production Security Group Allows RDP from Internet — Admin Approval Required",
        "description": "Production-tagged security group allows inbound RDP (port 3389) from 0.0.0.0/0.",
        "severity": "CRITICAL",
        "resource_type": "AwsEc2SecurityGroup",
        "category": "B",
    },
}


# ── HELPERS ───────────────────────────────────────────────────────────────────

def respond(status_code, body, content_type="application/json"):
    headers = {
        "Content-Type": content_type,
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
    }
    if content_type == "application/json":
        body = json.dumps(body, default=str)
    return {"statusCode": status_code, "headers": headers, "body": body}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def parse_body(body_str):
    try:
        return json.loads(body_str or "{}")
    except json.JSONDecodeError:
        return None


# ── ROUTE HANDLERS ────────────────────────────────────────────────────────────

def list_findings():
    result = findings_table.scan()
    items = result.get("Items", [])
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return respond(200, {
        "findings": items,
        "meta": {"account_id": ACCOUNT_ID, "region": REGION},
    })


def clear_findings():
    """Delete all findings from DynamoDB — for demo reset."""
    result = findings_table.scan(ProjectionExpression="finding_id")
    items = result.get("Items", [])
    if not items:
        return respond(200, {"status": "ok", "deleted": 0})
    deleted = 0
    for item in items:
        try:
            findings_table.delete_item(Key={"finding_id": item["finding_id"]})
            deleted += 1
        except Exception:
            pass
    return respond(200, {"status": "ok", "deleted": deleted})


def _get_setting(key, default="false"):
    result = settings_table.get_item(Key={"setting_key": key})
    item = result.get("Item")
    return item.get("value", default) if item else default


def get_settings():
    email = _get_setting("email_notifications", "false")
    auto_rem = _get_setting("auto_remediation", "true")
    ai_analysis = _get_setting("ai_analysis_enabled", "true")
    return respond(200, {
        "email_notifications": email,
        "auto_remediation": auto_rem,
        "ai_analysis_enabled": ai_analysis,
    })


def update_settings(body_str):
    body = parse_body(body_str)
    if body is None:
        return respond(400, {"error": "Invalid JSON"})
    updated = {}
    if "email_notifications" in body:
        val = "true" if body["email_notifications"] else "false"
        settings_table.put_item(Item={"setting_key": "email_notifications", "value": val, "updated_at": now_iso()})
        updated["email_notifications"] = val
    if "auto_remediation" in body:
        val = "true" if body["auto_remediation"] else "false"
        settings_table.put_item(Item={"setting_key": "auto_remediation", "value": val, "updated_at": now_iso()})
        updated["auto_remediation"] = val
    if "ai_analysis_enabled" in body:
        val = "true" if body["ai_analysis_enabled"] else "false"
        settings_table.put_item(Item={"setting_key": "ai_analysis_enabled", "value": val, "updated_at": now_iso()})
        updated["ai_analysis_enabled"] = val
    return respond(200, {"status": "ok", "updated": updated})


def get_ai_config():
    """Return current AI provider, model, and whether an API key is stored."""
    provider = _get_setting("ai_provider", "gemini")
    model    = _get_setting("ai_model", "gemini-2.0-flash")
    # Check whether a non-placeholder key exists in Secrets Manager
    has_key = False
    try:
        sm = boto3.client("secretsmanager", region_name=REGION)
        resp = sm.get_secret_value(SecretId=AI_SECRET_NAME)
        secret = json.loads(resp["SecretString"])
        key_val = secret.get("api_key", "")
        has_key = bool(key_val) and "REPLACE_WITH" not in key_val
    except Exception:
        pass
    return respond(200, {"provider": provider, "model": model, "has_api_key": has_key})


def update_ai_config(body_str):
    """
    Update AI provider/model in DynamoDB and optionally store new API key in Secrets Manager.
    Body: { provider, model, api_key (optional) }
    """
    body = parse_body(body_str)
    if body is None:
        return respond(400, {"error": "Invalid JSON"})

    updated = {}
    if "provider" in body:
        val = body["provider"].lower()
        if val not in ("gemini", "claude"):
            return respond(400, {"error": "provider must be 'gemini' or 'claude'"})
        settings_table.put_item(Item={"setting_key": "ai_provider", "value": val, "updated_at": now_iso()})
        updated["provider"] = val

    if "model" in body:
        settings_table.put_item(Item={"setting_key": "ai_model", "value": body["model"], "updated_at": now_iso()})
        updated["model"] = body["model"]

    if "api_key" in body and body["api_key"]:
        provider = body.get("provider") or _get_setting("ai_provider", "gemini")
        try:
            sm = boto3.client("secretsmanager", region_name=REGION)
            sm.put_secret_value(
                SecretId=AI_SECRET_NAME,
                SecretString=json.dumps({"api_key": body["api_key"], "provider": provider}),
            )
            updated["api_key"] = "stored"
        except Exception as exc:
            return respond(500, {"error": f"Failed to store API key: {exc}"})

    return respond(200, {"status": "ok", "updated": updated})


def fetch_ai_models(body_str):
    """
    Validate an API key against the chosen provider and return the list of usable models.
    Body: { provider, api_key? }  — api_key optional: uses stored Secrets Manager key if omitted.
    """
    body = parse_body(body_str)
    if body is None:
        return respond(400, {"error": "Invalid JSON"})

    provider = body.get("provider", "gemini").lower()
    api_key  = body.get("api_key", "").strip()

    # If no key provided, try to load from Secrets Manager
    if not api_key:
        api_key = _get_ai_api_key() or ""

    if not api_key:
        return respond(400, {"error": "No API key provided and no stored key found"})

    if provider == "gemini":
        return _fetch_gemini_models(api_key)
    elif provider == "claude":
        return _validate_claude_key(api_key)
    return respond(400, {"error": "provider must be 'gemini' or 'claude'"})


def _fetch_gemini_models(api_key: str):
    """Call Gemini models API, return models that support generateContent."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}&pageSize=50"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        err = exc.read().decode("utf-8")
        if exc.code == 400 or exc.code == 403:
            return respond(401, {"error": "Invalid Gemini API key"})
        return respond(502, {"error": f"Gemini API error {exc.code}: {err[:200]}"})
    except urllib.error.URLError as exc:
        return respond(502, {"error": f"Network error: {exc.reason}"})

    raw = data.get("models", [])
    # Filter to models that support generateContent and are flash/pro variants
    models = []
    for m in raw:
        name = m.get("name", "")  # e.g. "models/gemini-2.0-flash"
        model_id = name.replace("models/", "")
        supported = m.get("supportedGenerationMethods", [])
        display   = m.get("displayName", model_id)
        if "generateContent" not in supported:
            continue
        # Skip noisy embedding / vision-only / aqa models
        skip_keywords = ["embedding", "aqa", "vision", "learnlm", "exp", "preview", "latest"]
        if any(kw in model_id.lower() for kw in skip_keywords):
            continue
        models.append({"id": model_id, "name": display})

    # Sort: flash models first, then others
    models.sort(key=lambda x: (0 if "flash" in x["id"] else 1, x["id"]))
    if not models:
        return respond(200, {"valid": True, "models": [
            {"id": "gemini-2.0-flash",      "name": "Gemini 2.0 Flash"},
            {"id": "gemini-2.0-flash-lite",  "name": "Gemini 2.0 Flash Lite"},
            {"id": "gemini-1.5-flash",       "name": "Gemini 1.5 Flash"},
        ]})
    return respond(200, {"valid": True, "models": models})


def _validate_claude_key(api_key: str):
    """Validate Claude API key by making a minimal test call."""
    payload = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 5,
        "messages": [{"role": "user", "content": "Hi"}],
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
        return respond(200, {"valid": True, "models": CLAUDE_MODELS})
    except urllib.error.HTTPError as exc:
        err = exc.read().decode("utf-8")
        if exc.code in (401, 403):
            return respond(401, {"error": "Invalid Claude API key"})
        # 400 with valid key means model accepted but bad request — key is valid
        return respond(200, {"valid": True, "models": CLAUDE_MODELS})
    except urllib.error.URLError as exc:
        return respond(502, {"error": f"Network error: {exc.reason}"})


# ── AI DIRECT CALL HELPERS ─────────────────────────────────────────────────────

def _get_ai_api_key():
    """Retrieve AI API key from Secrets Manager. Returns None if not configured."""
    try:
        sm = boto3.client("secretsmanager", region_name=REGION)
        resp = sm.get_secret_value(SecretId=AI_SECRET_NAME)
        secret = json.loads(resp["SecretString"])
        key = secret.get("api_key", "")
        return key if key and "REPLACE_WITH" not in key else None
    except Exception:
        return None


def _call_ai_direct(prompt: str, max_tokens: int = 900):
    """Call configured AI provider directly. Returns (text, error_str)."""
    provider = _get_setting("ai_provider", "gemini")
    model    = _get_setting("ai_model", "gemini-2.0-flash")
    api_key  = _get_ai_api_key()
    if not api_key:
        return None, "AI API key not configured in Secrets Manager"
    if provider == "claude":
        return _call_claude_raw(api_key, model, prompt, max_tokens)
    return _call_gemini_raw(api_key, model, prompt, max_tokens)


def _call_gemini_raw(api_key, model, prompt, max_tokens):
    """Call Gemini API with automatic model fallback on 429. Returns (text, error)."""
    chain = [model] + [m for m in ("gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-flash") if m != model]
    for m in chain:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
        payload = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0, "responseMimeType": "application/json"},
            "safetySettings": [{"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}],
        }).encode()
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                body = json.loads(r.read().decode())
            return body["candidates"][0]["content"]["parts"][0]["text"].strip(), None
        except urllib.error.HTTPError as exc:
            err = exc.read().decode()[:200]
            if exc.code == 429 or exc.code == 404 or "RESOURCE_EXHAUSTED" in err:
                continue
            return None, f"Gemini HTTP {exc.code}: {err}"
        except Exception as exc:
            return None, f"Gemini error: {exc}"
    return None, "All Gemini models exhausted"


def _call_claude_raw(api_key, model, prompt, max_tokens):
    """Call Claude API directly. Returns (text, error)."""
    payload = json.dumps({
        "model": model, "max_tokens": max_tokens, "temperature": 0,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=payload,
        headers={"Content-Type": "application/json", "x-api-key": api_key, "anthropic-version": "2023-06-01"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = json.loads(r.read().decode())
        return body["content"][0]["text"].strip(), None
    except urllib.error.HTTPError as exc:
        return None, f"Claude HTTP {exc.code}: {exc.read().decode()[:200]}"
    except Exception as exc:
        return None, f"Claude error: {exc}"


# ── RUNBOOK ─────────────────────────────────────────────────────────────────────

_RUNBOOK_PROMPT = """AWS security remediation expert. Return ONLY valid JSON — no markdown, no preamble.

SECURITY FINDING:
{finding_json}

CURRENT AWS RESOURCE STATE:
{state_json}

REMEDIATION APPROACH:
{available_ops}

Generate a precise remediation runbook. Return this JSON exactly:
{{"summary":"one sentence what will be changed","risk_level":"LOW","estimated_impact":"effect on live services","execution_mode":"{execution_mode}","steps":[{{"n":1,"title":"step title","action":"what will be done","api_call":"exact boto3 or CLI command","expected":"what changes"}}],"rollback":[{{"n":1,"title":"undo title","action":"how to undo","api_call":"exact command to undo"}}],"warnings":["edge cases or cautions"]}}"""

_AVAILABLE_OPS = {
    "S3":      "s3.put_public_access_block(Bucket='NAME', PublicAccessBlockConfiguration={'BlockPublicAcls':True,'IgnorePublicAcls':True,'BlockPublicPolicy':True,'RestrictPublicBuckets':True})",
    "EC2":     "ec2.revoke_security_group_ingress(GroupId='SG_ID', IpPermissions=[<each_open_rule_from_current_state>])",
    "IAM":     "iam.update_access_key(UserName='USER', AccessKeyId='KEY_ID', Status='Inactive') — once per Active key",
    "GENERIC": "This resource type has no inline executor. Generate detailed AWS CLI / boto3 commands for manual admin execution. Be specific with exact resource IDs, parameter values, and prerequisite checks.",
}

_EXECUTION_MODES = {
    "S3":      "inline",
    "EC2":     "inline",
    "IAM":     "inline",
    "GENERIC": "advisory",
}


def _get_resource_state_for_runbook(resource_type: str, resource_id: str) -> dict:
    """Fetch minimal current resource state for AI runbook context."""
    state = {"resource_type": resource_type, "resource_id": resource_id}
    try:
        if "S3" in resource_type:
            bucket = resource_id.split(":::")[-1].split("/")[0]
            state["bucket_name"] = bucket
            try:
                r = s3.get_public_access_block(Bucket=bucket)
                state["current_public_access_block"] = r.get("PublicAccessBlockConfiguration", {})
            except ClientError as e:
                state["current_public_access_block"] = {"note": e.response["Error"]["Code"]}

        elif "SecurityGroup" in resource_type or "Ec2" in resource_type:
            sg_id = resource_id.split("/")[-1]
            state["sg_id"] = sg_id
            try:
                r = ec2.describe_security_groups(GroupIds=[sg_id])
                sg = r["SecurityGroups"][0]
                state["sg_name"] = sg.get("GroupName", "")
                state["tags"] = {t["Key"]: t["Value"] for t in sg.get("Tags", [])}
                open_rules = []
                for perm in sg.get("IpPermissions", []):
                    for rng in perm.get("IpRanges", []) + perm.get("Ipv6Ranges", []):
                        cidr = rng.get("CidrIp") or rng.get("CidrIpv6", "")
                        if cidr in ("0.0.0.0/0", "::/0"):
                            open_rules.append({
                                "protocol": perm.get("IpProtocol", "-1"),
                                "from_port": perm.get("FromPort", 0),
                                "to_port": perm.get("ToPort", 65535),
                                "cidr": cidr,
                            })
                state["open_ingress_rules"] = open_rules
            except ClientError as e:
                state["error"] = e.response["Error"]["Code"]

        elif "Iam" in resource_type or "iam" in resource_type.lower():
            username = resource_id.split("/")[-1]
            state["username"] = username
            try:
                keys = iam.list_access_keys(UserName=username)
                state["access_keys"] = [
                    {"id": k["AccessKeyId"][:8] + "...", "status": k["Status"]}
                    for k in keys.get("AccessKeyMetadata", [])
                ]
                tags = iam.list_user_tags(UserName=username)
                state["tags"] = {t["Key"]: t["Value"] for t in tags.get("Tags", [])}
            except ClientError as e:
                state["error"] = e.response["Error"]["Code"]
        else:
            # Generic resource: extract identifiers for advisory runbook
            state["note"] = (
                f"No live state fetcher for {resource_type}. "
                "Provide step-by-step CLI/Console remediation instructions."
            )
            # Try to extract a human-readable resource name from the ARN/ID
            parts = resource_id.split(":")
            state["resource_name"] = parts[-1] if parts else resource_id
    except Exception as e:
        state["fetch_error"] = str(e)
    return state


def _get_ops_key(resource_type: str) -> str:
    """Map AWS resource type string to remediation ops key (S3/EC2/IAM/GENERIC)."""
    rt = resource_type.lower()
    if "securitygroup" in rt or "ec2" in rt:
        return "EC2"
    if "iam" in rt:
        return "IAM"
    if "s3" in rt:
        return "S3"
    # DynamoDB, RDS, KMS, Lambda, ECS, etc. → advisory runbook (AI-generated manual steps)
    return "GENERIC"


def _apply_inline_for_finding(resource_type: str, resource_id: str, logs: list):
    """
    Attempt inline boto3 remediation for supported resource types.
    Returns (success, undo_data, logs, inline_supported).
    inline_supported=False means this resource type has no inline executor —
    the caller should treat the runbook as advisory only.
    """
    ops_key = _get_ops_key(resource_type)
    if ops_key == "S3":
        success, undo_data, logs = _apply_s3_block(resource_id, logs)
        return success, undo_data, logs, True
    elif ops_key == "EC2":
        success, undo_data, logs = _apply_sg_revoke(resource_id, logs)
        return success, undo_data, logs, True
    elif ops_key == "IAM":
        success, undo_data, logs = _apply_iam_disable(resource_id, logs)
        return success, undo_data, logs, True
    else:
        logs.append(f"[Advisory] No inline executor for: {resource_type}")
        logs.append("[Advisory] This runbook is for manual execution via AWS Console or CLI.")
        logs.append("[Advisory] Review each step and apply using the provided API calls.")
        return False, {}, logs, False


def _generate_runbook_with_context(item: dict, failure_history: list):
    """
    Generate AI runbook, optionally including prior failure context.
    Returns (runbook_dict, error_str). On success error_str is None.
    """
    resource_type = item.get("resource_type", "")
    resource_id   = item.get("resource_id", "")
    ops_key       = _get_ops_key(resource_type)
    current_state = _get_resource_state_for_runbook(resource_type, resource_id)

    finding_summary = {
        "resource_type": resource_type,
        "resource_id": resource_id,
        "severity": item.get("severity", ""),
        "title": item.get("title", ""),
        "description": item.get("description", ""),
        "ai_analysis": item.get("ai_analysis", ""),
    }

    prompt = _RUNBOOK_PROMPT.format(
        finding_json=json.dumps(finding_summary, default=str),
        state_json=json.dumps(current_state, default=str),
        available_ops=_AVAILABLE_OPS[ops_key],
        execution_mode=_EXECUTION_MODES[ops_key],
    )

    if failure_history:
        fail_ctx = f"\n\nPREVIOUS ATTEMPTS FAILED ({len(failure_history)}):\n"
        for fh in failure_history:
            tail = " | ".join(str(l) for l in fh.get("logs", [])[-5:])
            fail_ctx += f"  Attempt {fh.get('attempt','?')} [{fh.get('source','?')}]: {tail}\n"
        fail_ctx += "Revise your approach to avoid repeating the same failures.\n"
        prompt += fail_ctx

    text, err = _call_ai_direct(prompt, max_tokens=950)
    if err:
        return None, err

    try:
        return json.loads(text), None
    except json.JSONDecodeError:
        try:
            return json.loads(text[text.index("{"):text.rindex("}") + 1]), None
        except Exception:
            return None, f"Invalid JSON from AI: {text[:300]}"


def _update_finding_batch_result(finding_id: str, success: bool, logs: list,
                                  undo_data: dict, item: dict, failed: bool = False,
                                  advisory: bool = False):
    """Persist batch remediation outcome to DynamoDB."""
    if advisory:
        new_status = "MANUAL_REVIEW"
        rb_status  = "ADVISORY"
    elif success:
        new_status = "RESOLVED"
        rb_status  = "BATCH_APPLIED"
    elif failed:
        new_status = "FAILED"
        rb_status  = "BATCH_FAILED"
    else:
        new_status = item.get("status", "PENDING_APPROVAL")
        rb_status  = "BATCH_FAILED"

    try:
        findings_table.update_item(
            Key={"finding_id": finding_id},
            UpdateExpression=(
                "SET runbook_status = :rs, runbook_logs = :l, undo_data = :u, "
                "runbook_applied_at = :t, #st = :fs"
            ),
            ExpressionAttributeNames={"#st": "status"},
            ExpressionAttributeValues={
                ":rs": rb_status,
                ":l": json.dumps(logs, default=str),
                ":u": json.dumps(undo_data, default=str),
                ":t": now_iso(),
                ":fs": new_status,
            },
        )
    except Exception:
        pass  # best-effort — don't let DynamoDB errors abort the batch


def generate_runbook(body_str):
    body = parse_body(body_str)
    if body is None:
        return respond(400, {"error": "Invalid JSON"})
    finding_id = body.get("finding_id", "")
    if not finding_id:
        return respond(400, {"error": "finding_id required"})

    result = findings_table.get_item(Key={"finding_id": finding_id})
    item = result.get("Item")
    if not item:
        return respond(404, {"error": "Finding not found"})

    resource_type = item.get("resource_type", "")
    resource_id   = item.get("resource_id", "")

    ops_key = _get_ops_key(resource_type)
    current_state = _get_resource_state_for_runbook(resource_type, resource_id)

    finding_summary = {
        "resource_type": resource_type,
        "resource_id": resource_id,
        "severity": item.get("severity", ""),
        "title": item.get("title", ""),
        "description": item.get("description", ""),
        "ai_analysis": item.get("ai_analysis", ""),
    }

    prompt = _RUNBOOK_PROMPT.format(
        finding_json=json.dumps(finding_summary, default=str),
        state_json=json.dumps(current_state, default=str),
        available_ops=_AVAILABLE_OPS[ops_key],
        execution_mode=_EXECUTION_MODES[ops_key],
    )

    text, err = _call_ai_direct(prompt, max_tokens=900)
    if err:
        return respond(500, {"error": f"AI call failed: {err}"})

    try:
        runbook = json.loads(text)
    except json.JSONDecodeError:
        try:
            runbook = json.loads(text[text.index("{"):text.rindex("}") + 1])
        except Exception:
            return respond(500, {"error": f"AI returned invalid JSON: {text[:300]}"})

    runbook_status = "ADVISORY" if ops_key == "GENERIC" else "READY"
    try:
        findings_table.update_item(
            Key={"finding_id": finding_id},
            UpdateExpression="SET runbook = :r, runbook_status = :s, runbook_generated_at = :t",
            ExpressionAttributeValues={
                ":r": json.dumps(runbook, default=str),
                ":s": runbook_status,
                ":t": now_iso(),
            },
        )
    except Exception as e:
        return respond(500, {"error": f"Failed to store runbook: {e}"})

    provider = _get_setting("ai_provider", "gemini")
    model    = _get_setting("ai_model", "gemini-2.0-flash")
    return respond(200, {
        "runbook": runbook,
        "provider": provider,
        "model": model,
        "execution_mode": _EXECUTION_MODES[ops_key],
    })


def apply_runbook(body_str):
    body = parse_body(body_str)
    if body is None:
        return respond(400, {"error": "Invalid JSON"})
    finding_id = body.get("finding_id", "")
    if not finding_id:
        return respond(400, {"error": "finding_id required"})

    result = findings_table.get_item(Key={"finding_id": finding_id})
    item = result.get("Item")
    if not item:
        return respond(404, {"error": "Finding not found"})
    if not item.get("runbook"):
        return respond(400, {"error": "No runbook generated yet — generate runbook first"})

    resource_type = item.get("resource_type", "")
    resource_id   = item.get("resource_id", "")
    logs = []
    success = False
    undo_data = {}
    inline_supported = True

    try:
        success, undo_data, logs, inline_supported = _apply_inline_for_finding(resource_type, resource_id, logs)
    except Exception as e:
        logs.append(f"EXCEPTION: {e}")
        logs.append(f"TRACE: {traceback.format_exc().splitlines()[-3:]}")

    if not inline_supported:
        # Advisory mode — runbook generated for manual execution, not auto-applied
        findings_table.update_item(
            Key={"finding_id": finding_id},
            UpdateExpression="SET runbook_status = :rs, runbook_logs = :l, runbook_applied_at = :t",
            ExpressionAttributeValues={
                ":rs": "ADVISORY",
                ":l": json.dumps(logs, default=str),
                ":t": now_iso(),
            },
        )
        return respond(200, {
            "success": False,
            "advisory": True,
            "runbook_status": "ADVISORY",
            "logs": logs,
            "can_undo": False,
            "message": (
                f"{resource_type} has no inline executor. "
                "Follow the runbook steps manually via AWS Console or CLI."
            ),
        })

    new_status = "RUNBOOK_APPLIED" if success else "RUNBOOK_FAILED"
    findings_table.update_item(
        Key={"finding_id": finding_id},
        UpdateExpression="SET runbook_status = :rs, runbook_logs = :l, undo_data = :u, runbook_applied_at = :t, #st = :fs",
        ExpressionAttributeNames={"#st": "status"},
        ExpressionAttributeValues={
            ":rs": new_status,
            ":l": json.dumps(logs, default=str),
            ":u": json.dumps(undo_data, default=str),
            ":t": now_iso(),
            ":fs": "RESOLVED" if success else item.get("status", "PENDING_APPROVAL"),
        },
    )
    return respond(200, {
        "success": success,
        "runbook_status": new_status,
        "logs": logs,
        "can_undo": success and bool(undo_data),
    })


def undo_runbook(body_str):
    body = parse_body(body_str)
    if body is None:
        return respond(400, {"error": "Invalid JSON"})
    finding_id = body.get("finding_id", "")
    if not finding_id:
        return respond(400, {"error": "finding_id required"})

    result = findings_table.get_item(Key={"finding_id": finding_id})
    item = result.get("Item")
    if not item:
        return respond(404, {"error": "Finding not found"})

    undo_str = item.get("undo_data", "{}")
    try:
        undo_data = json.loads(undo_str) if isinstance(undo_str, str) else (undo_str or {})
    except Exception:
        return respond(400, {"error": "Invalid undo data"})

    if not undo_data:
        return respond(400, {"error": "No undo data available — cannot undo this remediation"})

    resource_type = item.get("resource_type", "")
    logs = []
    success = False

    try:
        if "S3" in resource_type:
            success, logs = _undo_s3_block(undo_data, logs)
        elif "SecurityGroup" in resource_type or "Ec2" in resource_type:
            success, logs = _undo_sg_revoke(undo_data, logs)
        elif "Iam" in resource_type or "iam" in resource_type.lower():
            success, logs = _undo_iam_disable(undo_data, logs)
        else:
            logs.append(f"ERROR: Cannot undo resource type: {resource_type}")
    except Exception as e:
        logs.append(f"EXCEPTION during undo: {e}")

    if success:
        findings_table.update_item(
            Key={"finding_id": finding_id},
            UpdateExpression="SET runbook_status = :rs, runbook_logs = :l, undo_data = :u, #st = :fs",
            ExpressionAttributeNames={"#st": "status"},
            ExpressionAttributeValues={
                ":rs": "UNDONE",
                ":l": json.dumps(logs, default=str),
                ":u": json.dumps({}),
                ":fs": "PENDING_APPROVAL",
            },
        )
    return respond(200, {"success": success, "logs": logs})


# ── INLINE REMEDIATION HELPERS ─────────────────────────────────────────────────

def _s3_put_public_access_block(bucket, block_acls, ignore_acls, block_policy, restrict_buckets):
    """
    Call the S3 public access block API using the correct method name for the runtime's
    boto3 version. boto3 < 1.9.84 uses put_public_access_block; newer uses
    put_bucket_public_access_block. Try both names so the code works on any Lambda runtime.
    """
    cfg = {
        "BlockPublicAcls": bool(block_acls),
        "IgnorePublicAcls": bool(ignore_acls),
        "BlockPublicPolicy": bool(block_policy),
        "RestrictPublicBuckets": bool(restrict_buckets),
    }
    if hasattr(s3, "put_public_access_block"):
        s3.put_public_access_block(Bucket=bucket, PublicAccessBlockConfiguration=cfg)
    else:
        s3.put_bucket_public_access_block(Bucket=bucket, PublicAccessBlockConfiguration=cfg)


def _apply_s3_block(resource_id, logs):
    bucket = resource_id.split(":::")[-1].split("/")[0]
    if not bucket:
        logs.append("[S3] \u2717 Could not parse bucket name from resource_id")
        return False, {}, logs
    logs.append(f"[S3] Target bucket: {bucket}")
    undo_data = {"type": "s3", "bucket": bucket, "original": {}}
    # Capture pre-state for undo; NoSuchPublicAccessBlockConfiguration means defaults (all False)
    try:
        r = s3.get_public_access_block(Bucket=bucket)
        undo_data["original"] = r.get("PublicAccessBlockConfiguration", {})
        logs.append(f"[S3] Pre-state captured: {undo_data['original']}")
        # Idempotency: if already fully blocked, skip the write
        cfg = undo_data["original"]
        if all(cfg.get(k) for k in ("BlockPublicAcls", "IgnorePublicAcls", "BlockPublicPolicy", "RestrictPublicBuckets")):
            logs.append("[S3] \u2713 Already fully blocked — no changes needed")
            return True, undo_data, logs
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "NoSuchPublicAccessBlockConfiguration":
            logs.append("[S3] No existing public access block — will apply fresh configuration")
            undo_data["original"] = {"BlockPublicAcls": False, "IgnorePublicAcls": False,
                                     "BlockPublicPolicy": False, "RestrictPublicBuckets": False}
        elif code == "NoSuchBucket":
            logs.append(f"[S3] \u2717 Bucket '{bucket}' does not exist — may have been deleted")
            return False, undo_data, logs
        else:
            logs.append(f"[S3] Pre-state warning ({code}): proceeding with remediation")
    try:
        _s3_put_public_access_block(bucket, True, True, True, True)
        logs.append("[S3] \u2713 Applied: all public access blocked (BlockPublicAcls, IgnorePublicAcls, BlockPublicPolicy, RestrictPublicBuckets = True)")
    except ClientError as e:
        code = e.response["Error"]["Code"]
        msg  = e.response["Error"]["Message"]
        if code == "AccessDenied":
            logs.append(f"[S3] \u2717 Access denied — likely blocked by account-level S3 policy. The bucket may already be protected.")
        else:
            logs.append(f"[S3] \u2717 Failed ({code}): {msg}")
        return False, undo_data, logs
    try:
        r = s3.get_public_access_block(Bucket=bucket)
        cfg = r.get("PublicAccessBlockConfiguration", {})
        if all(cfg.get(k) for k in ("BlockPublicAcls", "IgnorePublicAcls", "BlockPublicPolicy", "RestrictPublicBuckets")):
            logs.append("[S3] \u2713 Verified: all public access blocked")
            return True, undo_data, logs
        logs.append(f"[S3] \u2717 Verification failed — unexpected state: {cfg}")
        return False, undo_data, logs
    except ClientError:
        logs.append("[S3] \u2713 Applied (verification read skipped)")
        return True, undo_data, logs


def _apply_sg_revoke(resource_id, logs):
    sg_id = resource_id.split("/")[-1]
    logs.append(f"[SG] Target: {sg_id}")
    undo_data = {"type": "sg", "sg_id": sg_id, "revoked_rules": []}
    try:
        r = ec2.describe_security_groups(GroupIds=[sg_id])
        sg = r["SecurityGroups"][0]
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code in ("InvalidGroup.NotFound", "InvalidGroupId.NotFound"):
            logs.append(f"[SG] \u2717 Security group '{sg_id}' not found — may have been deleted")
        else:
            logs.append(f"[SG] \u2717 Cannot describe SG: {code}: {e.response['Error']['Message']}")
        return False, undo_data, logs

    rules_to_revoke = []
    for perm in sg.get("IpPermissions", []):
        open_v4 = [x for x in perm.get("IpRanges", []) if x.get("CidrIp") in ("0.0.0.0/0",)]
        open_v6 = [x for x in perm.get("Ipv6Ranges", []) if x.get("CidrIpv6") == "::/0"]
        if open_v4 or open_v6:
            rule = {"IpProtocol": perm.get("IpProtocol", "-1")}
            if perm.get("FromPort") is not None:
                rule["FromPort"] = perm["FromPort"]
                rule["ToPort"]   = perm["ToPort"]
            if open_v4:
                rule["IpRanges"] = open_v4
            if open_v6:
                rule["Ipv6Ranges"] = open_v6
            rules_to_revoke.append(rule)
            port_str = f":{perm.get('FromPort',0)}-{perm.get('ToPort',65535)}" if perm.get("FromPort") is not None else ":all"
            logs.append(f"[SG] Found open rule: {perm.get('IpProtocol','-1')}{port_str} from 0.0.0.0/0")

    if not rules_to_revoke:
        logs.append("[SG] No unrestricted ingress rules found — already clean")
        return True, undo_data, logs

    undo_data["revoked_rules"] = rules_to_revoke
    try:
        ec2.revoke_security_group_ingress(GroupId=sg_id, IpPermissions=rules_to_revoke)
        logs.append(f"[SG] \u2713 Revoked {len(rules_to_revoke)} unrestricted ingress rule(s)")
    except ClientError as e:
        logs.append(f"[SG] \u2717 Revoke failed: {e.response['Error']['Code']}: {e.response['Error']['Message']}")
        return False, undo_data, logs

    try:
        r = ec2.describe_security_groups(GroupIds=[sg_id])
        still_open = [
            rng.get("CidrIp") or rng.get("CidrIpv6", "")
            for perm in r["SecurityGroups"][0].get("IpPermissions", [])
            for rng in perm.get("IpRanges", []) + perm.get("Ipv6Ranges", [])
            if (rng.get("CidrIp") or rng.get("CidrIpv6", "")) in ("0.0.0.0/0", "::/0")
        ]
        if still_open:
            logs.append(f"[SG] \u2717 Verification: {len(still_open)} open rule(s) remaining")
            return False, undo_data, logs
        logs.append("[SG] \u2713 Verified: no unrestricted ingress rules remaining")
    except ClientError:
        logs.append("[SG] \u2713 Applied (verification skipped)")
    return True, undo_data, logs


def _apply_iam_disable(resource_id, logs):
    username = resource_id.split("/")[-1]
    logs.append(f"[IAM] Target user: {username}")
    undo_data = {"type": "iam", "username": username, "disabled_keys": []}
    try:
        keys = iam.list_access_keys(UserName=username)
        active_keys = [k["AccessKeyId"] for k in keys.get("AccessKeyMetadata", []) if k["Status"] == "Active"]
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "NoSuchEntity":
            logs.append(f"[IAM] \u2717 IAM user '{username}' does not exist — may have been deleted")
        else:
            logs.append(f"[IAM] \u2717 Cannot list access keys: {code}: {e.response['Error']['Message']}")
        return False, undo_data, logs

    if not active_keys:
        logs.append("[IAM] No active access keys — already clean")
        return True, undo_data, logs

    disabled = []
    for key_id in active_keys:
        try:
            iam.update_access_key(UserName=username, AccessKeyId=key_id, Status="Inactive")
            logs.append(f"[IAM] \u2713 Disabled key: {key_id[:12]}...")
            disabled.append(key_id)
        except ClientError as e:
            logs.append(f"[IAM] \u2717 Failed to disable {key_id[:12]}...: {e.response['Error']['Code']}")

    undo_data["disabled_keys"] = disabled
    if not disabled:
        return False, undo_data, logs

    try:
        keys = iam.list_access_keys(UserName=username)
        still_active = [k for k in keys.get("AccessKeyMetadata", []) if k["Status"] == "Active"]
        if still_active:
            logs.append(f"[IAM] \u2717 Verification: {len(still_active)} key(s) still Active")
        else:
            logs.append("[IAM] \u2713 Verified: all access keys Inactive")
    except ClientError:
        logs.append("[IAM] \u2713 Applied (verification skipped)")

    return len(disabled) == len(active_keys), undo_data, logs


def _undo_s3_block(undo_data, logs):
    bucket   = undo_data.get("bucket")
    original = undo_data.get("original") or {"BlockPublicAcls": False, "IgnorePublicAcls": False, "BlockPublicPolicy": False, "RestrictPublicBuckets": False}
    if not bucket:
        logs.append("ERROR: Missing bucket name in undo data")
        return False, logs
    logs.append(f"[UNDO S3] Restoring bucket: {bucket} to original state: {original}")
    try:
        _s3_put_public_access_block(
            bucket,
            original.get("BlockPublicAcls", False),
            original.get("IgnorePublicAcls", False),
            original.get("BlockPublicPolicy", False),
            original.get("RestrictPublicBuckets", False),
        )
        logs.append("[UNDO S3] \u2713 Restored original public access block settings")
        return True, logs
    except ClientError as e:
        logs.append(f"[UNDO S3] \u2717 Failed: {e.response['Error']['Code']}: {e.response['Error']['Message']}")
        return False, logs


def _undo_sg_revoke(undo_data, logs):
    sg_id   = undo_data.get("sg_id")
    revoked = undo_data.get("revoked_rules", [])
    if not sg_id or not revoked:
        logs.append("ERROR: Missing sg_id or revoked_rules in undo data")
        return False, logs
    logs.append(f"[UNDO SG] Re-adding {len(revoked)} rule(s) to {sg_id}")
    try:
        ec2.authorize_security_group_ingress(GroupId=sg_id, IpPermissions=revoked)
        logs.append(f"[UNDO SG] \u2713 Restored {len(revoked)} ingress rule(s)")
        return True, logs
    except ClientError as e:
        logs.append(f"[UNDO SG] \u2717 Failed: {e.response['Error']['Code']}: {e.response['Error']['Message']}")
        return False, logs


def _undo_iam_disable(undo_data, logs):
    username     = undo_data.get("username")
    disabled_keys = undo_data.get("disabled_keys", [])
    if not username or not disabled_keys:
        logs.append("ERROR: Missing username or disabled_keys in undo data")
        return False, logs
    logs.append(f"[UNDO IAM] Re-enabling {len(disabled_keys)} key(s) for user: {username}")
    re_enabled = 0
    for key_id in disabled_keys:
        try:
            iam.update_access_key(UserName=username, AccessKeyId=key_id, Status="Active")
            logs.append(f"[UNDO IAM] \u2713 Re-enabled: {key_id[:12]}...")
            re_enabled += 1
        except ClientError as e:
            logs.append(f"[UNDO IAM] \u2717 Failed re-enable {key_id[:12]}...: {e.response['Error']['Code']}")
    return re_enabled == len(disabled_keys), logs


def take_action(body_str):
    body = parse_body(body_str)
    if body is None:
        return respond(400, {"error": "Invalid JSON"})

    finding_id = body.get("finding_id", "")
    action     = body.get("action", "").lower()
    action_id  = body.get("action_id")

    if not finding_id:
        return respond(400, {"error": "finding_id required"})
    if action not in ("approve", "reject", "manual"):
        return respond(400, {"error": "action must be approve, reject, or manual"})

    result = findings_table.get_item(Key={"finding_id": finding_id})
    item = result.get("Item")
    if not item:
        return respond(404, {"error": f"Finding not found: {finding_id[:80]}"})

    task_token = item.get("task_token")
    if not task_token:
        return respond(400, {"error": "No pending approval token — finding may have already been actioned"})
    if item.get("status") != "PENDING_APPROVAL":
        return respond(400, {"error": f"Finding status is '{item.get('status')}', not PENDING_APPROVAL"})

    if action == "approve":
        task_out = json.dumps({"admin_decision": "APPROVED", "approved_action": int(action_id) if action_id is not None else 1})
    elif action == "reject":
        task_out = json.dumps({"admin_decision": "REJECTED"})
    else:
        task_out = json.dumps({"admin_decision": "MANUAL"})

    try:
        sfn.send_task_success(taskToken=task_token, output=task_out)
    except sfn.exceptions.TaskTimedOut:
        return respond(410, {"error": "Approval window expired (1-hour timeout exceeded)"})
    except sfn.exceptions.InvalidToken:
        return respond(410, {"error": "Invalid or already-used approval token"})
    except Exception as e:
        return respond(500, {"error": str(e)})

    new_status = {"approve": "APPROVED", "reject": "REJECTED", "manual": "MANUAL_REVIEW"}[action]
    findings_table.update_item(
        Key={"finding_id": finding_id},
        UpdateExpression="SET #s = :s, action_taken = :a, updated_at = :u REMOVE task_token",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":s": new_status, ":a": action, ":u": now_iso()},
    )
    return respond(200, {"status": "ok", "action": action, "finding_id": finding_id})


def resend_email(body_str):
    if not SNS_TOPIC_ARN:
        return respond(400, {"error": "SNS topic not configured"})
    body = parse_body(body_str)
    if body is None:
        return respond(400, {"error": "Invalid JSON"})

    finding_id = body.get("finding_id", "")
    if not finding_id:
        return respond(400, {"error": "finding_id required"})

    result = findings_table.get_item(Key={"finding_id": finding_id})
    item = result.get("Item")
    if not item:
        return respond(404, {"error": "Finding not found"})

    severity    = item.get("severity", "HIGH")
    title       = item.get("title", "Security Finding")
    resource_id = item.get("resource_id", "N/A")

    subject = f"[{severity}] Security Alert: {title[:60]}"
    msg = (
        f"Security Finding Alert\n\nTitle: {title}\nSeverity: {severity}\n"
        f"Resource: {item.get('resource_type','')} — {resource_id}\n"
        f"Status: {item.get('status','')}\nFinding ID: {finding_id}\n\n"
        f"AI Analysis:\n{item.get('ai_analysis', 'No AI analysis.')}\n\nVisit the dashboard to take action."
    )
    try:
        sns.publish(TopicArn=SNS_TOPIC_ARN, Subject=subject[:100], Message=msg)
    except Exception as e:
        return respond(500, {"error": f"SNS publish failed: {e}"})
    return respond(200, {"status": "ok", "message": "Email sent"})


def get_pipeline_status():
    try:
        rule = events.describe_rule(Name=EB_RULE_NAME)
        return respond(200, {"pipeline": rule.get("State", "UNKNOWN")})
    except Exception as e:
        return respond(500, {"error": str(e)})


def control_pipeline(body_str, context=None):
    body = parse_body(body_str)
    if body is None:
        return respond(400, {"error": "Invalid JSON"})
    action = body.get("action", "")
    if action not in ("shutdown", "start", "terminate"):
        return respond(400, {"error": "action must be shutdown, start, or terminate"})
    if action == "terminate":
        return _initiate_terminate(context)
    try:
        if action == "shutdown":
            events.disable_rule(Name=EB_RULE_NAME)
            state = "DISABLED"
        else:
            events.enable_rule(Name=EB_RULE_NAME)
            state = "ENABLED"
    except Exception as e:
        return respond(500, {"error": str(e)})
    return respond(200, {"status": "ok", "pipeline": state})


def _initiate_terminate(context):
    """Invoke self asynchronously to destroy all infrastructure, then respond."""
    fn_name = os.environ.get("AWS_LAMBDA_FUNCTION_NAME", "")
    if not fn_name:
        return respond(500, {"error": "Cannot determine Lambda function name"})
    try:
        lam.invoke(
            FunctionName=fn_name,
            InvocationType="Event",  # async — fire and forget
            Payload=json.dumps({"__terminate": True}).encode(),
        )
    except Exception as e:
        return respond(500, {"error": f"Failed to initiate termination: {e}"})
    return respond(200, {
        "status": "terminating",
        "message": "Infrastructure termination initiated. All AWS resources will be deleted in ~30 seconds.",
    })


def _do_terminate():
    """
    Destroy all security automation AWS resources.
    Called via async self-invocation so the HTTP response is already sent.
    Stops SFN executions, deletes DynamoDB, Lambda functions, SNS, EventBridge,
    CloudWatch logs, Secrets Manager, API Gateway, then self.
    """
    time.sleep(3)  # brief pause to ensure HTTP response fully delivered
    results = {}

    # 1. Stop all running Step Functions executions
    try:
        if STATE_MACHINE_ARN:
            pager = sfn.get_paginator("list_executions")
            stopped = 0
            for page in pager.paginate(stateMachineArn=STATE_MACHINE_ARN, statusFilter="RUNNING"):
                for ex in page.get("executions", []):
                    try:
                        sfn.stop_execution(executionArn=ex["executionArn"], cause="infrastructure-terminated")
                        stopped += 1
                    except Exception:
                        pass
            results["sfn_stopped"] = stopped
    except Exception as e:
        results["sfn_error"] = str(e)

    # 2. Delete DynamoDB tables
    db = boto3.client("dynamodb", region_name=REGION)
    for table_name in [FINDINGS_TABLE, SETTINGS_TABLE]:
        if table_name:
            try:
                db.delete_table(TableName=table_name)
            except Exception:
                pass
    results["dynamodb"] = "deleted"

    # 3. Delete all other security-auto-* Lambda functions
    fn_name = os.environ.get("AWS_LAMBDA_FUNCTION_NAME", "")
    try:
        pager = lam.get_paginator("list_functions")
        for page in pager.paginate():
            for fn in page.get("Functions", []):
                name = fn["FunctionName"]
                if name.startswith("security-auto-") and name != fn_name:
                    try:
                        lam.delete_function(FunctionName=name)
                    except Exception:
                        pass
        results["lambdas"] = "deleted"
    except Exception as e:
        results["lambda_error"] = str(e)

    # 4. Delete SNS topic (subscriptions first)
    try:
        if SNS_TOPIC_ARN:
            try:
                subs = sns.list_subscriptions_by_topic(TopicArn=SNS_TOPIC_ARN)
                for sub in subs.get("Subscriptions", []):
                    if sub.get("SubscriptionArn", "").startswith("arn:"):
                        try:
                            sns.unsubscribe(SubscriptionArn=sub["SubscriptionArn"])
                        except Exception:
                            pass
            except Exception:
                pass
            sns.delete_topic(TopicArn=SNS_TOPIC_ARN)
        results["sns"] = "deleted"
    except Exception as e:
        results["sns_error"] = str(e)

    # 5. Delete EventBridge rules (targets must be removed first)
    def _delete_eb_rule(rule_name):
        try:
            targets = events.list_targets_by_rule(Rule=rule_name)
            tids = [t["Id"] for t in targets.get("Targets", [])]
            if tids:
                events.remove_targets(Rule=rule_name, Ids=tids)
        except Exception:
            pass
        try:
            events.delete_rule(Name=rule_name)
        except Exception:
            pass

    try:
        _delete_eb_rule(EB_RULE_NAME)
        _delete_eb_rule("security-auto-ttl")  # cleanup auto-TTL rule if set
        results["eventbridge"] = "deleted"
    except Exception as e:
        results["eventbridge_error"] = str(e)

    # 6. Delete CloudWatch log groups
    try:
        logs = boto3.client("logs", region_name=REGION)
        pager = logs.get_paginator("describe_log_groups")
        for page in pager.paginate(logGroupNamePrefix="/aws/lambda/security-auto"):
            for lg in page.get("logGroups", []):
                try:
                    logs.delete_log_group(logGroupName=lg["logGroupName"])
                except Exception:
                    pass
        for lg_name in ["/aws/security-automation", "/aws/lambda/security-auto-dashboard"]:
            try:
                logs.delete_log_group(logGroupName=lg_name)
            except Exception:
                pass
        results["logs"] = "deleted"
    except Exception as e:
        results["logs_error"] = str(e)

    # 7. Delete Secrets Manager secret
    try:
        sm = boto3.client("secretsmanager", region_name=REGION)
        sm.delete_secret(SecretId="security-automation/ai-api-key", ForceDeleteWithoutRecovery=True)
        results["secret"] = "deleted"
    except Exception as e:
        results["secret_error"] = str(e)

    # 8. Discover and delete API Gateway REST API
    try:
        agw = boto3.client("apigateway", region_name=REGION)
        pager = agw.get_paginator("get_rest_apis")
        for page in pager.paginate():
            for api in page.get("items", []):
                if api.get("name") == "SecurityAutomationApprovalAPI":
                    try:
                        agw.delete_rest_api(restApiId=api["id"])
                        results["api_gateway"] = "deleted"
                    except Exception:
                        pass
    except Exception as e:
        results["api_gateway_error"] = str(e)

    # 9. Delete self (dashboard Lambda) — must be last
    try:
        if fn_name:
            lam.delete_function(FunctionName=fn_name)
            results["self"] = "deleted"
    except Exception as e:
        results["self_error"] = str(e)

    return results


def start_simulation(body_str):
    body = parse_body(body_str)
    if body is None:
        return respond(400, {"error": "Invalid JSON"})

    case_id = body.get("case_id", "").upper()
    if case_id not in SIMULATION_CASES:
        return respond(400, {"error": f"Unknown case_id. Must be one of: {list(SIMULATION_CASES.keys())}"})
    if not STATE_MACHINE_ARN:
        return respond(500, {"error": "STATE_MACHINE_ARN not configured"})

    case   = SIMULATION_CASES[case_id]
    ts     = int(time.time())
    sim_id = f"sim-{case_id.lower()}-{ts}"

    try:
        resource_id, resource_info = _create_sim_resource(case_id, sim_id, ts)
    except Exception as e:
        return respond(500, {"error": f"Failed to create simulation resource: {e}"})

    finding_id = f"{sim_id}-finding"
    sfn_input  = {
        "detail": {
            "findings": [{
                "Id": finding_id,
                "ProductArn": f"arn:aws:securityhub:{REGION}:{ACCOUNT_ID}:product/aws/securityhub",
                "Resources": [{"Type": case["resource_type"], "Id": resource_id}],
                "Severity": {"Label": case["severity"]},
                "Title": case["title"],
                "Description": case["description"],
                "Compliance": {"Status": "FAILED"},
                "WorkflowState": "NEW",
                "RecordState": "ACTIVE",
            }]
        },
        "region": REGION,
        "account": ACCOUNT_ID,
    }

    try:
        sfn.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            name=sim_id,
            input=json.dumps(sfn_input),
        )
    except Exception as e:
        try:
            _delete_sim_resource(case["resource_type"], resource_info)
        except Exception:
            pass
        return respond(500, {"error": f"Failed to start Step Functions: {e}"})

    return respond(200, {
        "status": "started",
        "case_id": case_id,
        "finding_id": finding_id,
        "sim_resource_id": resource_id,
        "sim_resource_type": case["resource_type"],
        "sim_resource_info": resource_info,
        "message": f"Case {case_id} started. Findings appear in ~60 seconds.",
    })


def cleanup_simulation(body_str):
    body = parse_body(body_str)
    if body is None:
        return respond(400, {"error": "Invalid JSON"})
    resource_type = body.get("sim_resource_type", "")
    resource_info = body.get("sim_resource_info", {})
    if not resource_type or not resource_info:
        return respond(400, {"error": "sim_resource_type and sim_resource_info required"})
    try:
        _delete_sim_resource(resource_type, resource_info)
    except Exception as e:
        return respond(500, {"error": f"Cleanup failed: {e}"})
    return respond(200, {"status": "ok", "message": "Simulation resource deleted"})


# ── SIMULATION RESOURCE HELPERS ───────────────────────────────────────────────

def _get_default_vpc():
    vpcs = ec2.describe_vpcs(Filters=[{"Name": "isDefault", "Values": ["true"]}])
    if not vpcs["Vpcs"]:
        raise ValueError("No default VPC found")
    return vpcs["Vpcs"][0]["VpcId"]


def _create_sim_resource(case_id, sim_id, ts):
    if case_id == "A1":
        bucket = f"sim-pub-{ts}"
        try:
            if REGION == "us-east-1":
                s3.create_bucket(Bucket=bucket)
            else:
                s3.create_bucket(Bucket=bucket, CreateBucketConfiguration={"LocationConstraint": REGION})
        except ClientError as e:
            if e.response["Error"]["Code"] != "BucketAlreadyOwnedByYou":
                raise
        # Attempt to disable Block Public Access to simulate the misconfiguration.
        # This may fail if account-level S3 block is enforced — simulation proceeds regardless.
        try:
            s3.put_public_access_block(
                Bucket=bucket,
                PublicAccessBlockConfiguration={
                    "BlockPublicAcls": False, "IgnorePublicAcls": False,
                    "BlockPublicPolicy": False, "RestrictPublicBuckets": False,
                },
            )
        except ClientError:
            # AccessDenied or account-level block — bucket created, finding injected anyway
            pass
        return f"arn:aws:s3:::{bucket}", {"bucket_name": bucket}

    elif case_id in ("A2", "A3", "B2"):
        vpc_id  = _get_default_vpc()
        sg_name = f"{sim_id}-sg"
        sg      = ec2.create_security_group(
            GroupName=sg_name,
            Description=f"SecurityAutomation Sim {case_id}",
            VpcId=vpc_id,
        )
        sg_id = sg["GroupId"]
        if case_id == "A2":
            ec2.authorize_security_group_ingress(
                GroupId=sg_id,
                IpPermissions=[{"IpProtocol": "tcp", "FromPort": 22, "ToPort": 22,
                                 "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}],
            )
        elif case_id == "A3":
            ec2.authorize_security_group_ingress(
                GroupId=sg_id,
                IpPermissions=[{"IpProtocol": "-1", "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}],
            )
        elif case_id == "B2":
            ec2.create_tags(Resources=[sg_id], Tags=[
                {"Key": "Environment", "Value": "Production"},
                {"Key": "Name", "Value": sg_name},
            ])
            ec2.authorize_security_group_ingress(
                GroupId=sg_id,
                IpPermissions=[{"IpProtocol": "tcp", "FromPort": 3389, "ToPort": 3389,
                                 "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}],
            )
        return f"arn:aws:ec2:{REGION}:{ACCOUNT_ID}:security-group/{sg_id}", {"sg_id": sg_id}

    elif case_id == "B1":
        username = f"{sim_id}-u"[:32]
        iam.create_user(UserName=username, Tags=[
            {"Key": "Role", "Value": "CI-Pipeline"},
            {"Key": "CreatedBy", "Value": "SimulationLab"},
        ])
        key_resp = iam.create_access_key(UserName=username)
        return (
            f"arn:aws:iam::{ACCOUNT_ID}:user/{username}",
            {"username": username, "access_key_id": key_resp["AccessKey"]["AccessKeyId"]},
        )

    raise ValueError(f"Unknown case: {case_id}")


def _delete_sim_resource(resource_type, resource_info):
    if "bucket_name" in resource_info:
        bucket = resource_info["bucket_name"]
        try:
            objs = s3.list_objects_v2(Bucket=bucket).get("Contents", [])
            if objs:
                s3.delete_objects(Bucket=bucket, Delete={"Objects": [{"Key": o["Key"]} for o in objs]})
        except ClientError:
            pass
        try:
            s3.delete_bucket(Bucket=bucket)
        except ClientError:
            pass

    elif "sg_id" in resource_info:
        try:
            ec2.delete_security_group(GroupId=resource_info["sg_id"])
        except ClientError:
            pass

    elif "username" in resource_info:
        uname = resource_info["username"]
        for fn in [
            lambda: [iam.delete_access_key(UserName=uname, AccessKeyId=k["AccessKeyId"])
                     for k in iam.list_access_keys(UserName=uname).get("AccessKeyMetadata", [])],
            lambda: [iam.delete_user_policy(UserName=uname, PolicyName=p)
                     for p in iam.list_user_policies(UserName=uname).get("PolicyNames", [])],
            lambda: [iam.detach_user_policy(UserName=uname, PolicyArn=p["PolicyArn"])
                     for p in iam.list_attached_user_policies(UserName=uname).get("AttachedPolicies", [])],
            lambda: iam.delete_user(UserName=uname),
        ]:
            try:
                fn()
            except ClientError:
                pass


# ── BATCH REMEDIATION ─────────────────────────────────────────────────────────

def get_batch_status():
    """GET /dashboard/api/remediate-all — return current batch job status."""
    item = settings_table.get_item(Key={"setting_key": "batch_remediation_status"}).get("Item", {})
    return respond(200, {
        "status":       item.get("value", "idle"),
        "total":        int(item.get("batch_total", 0)),
        "done":         int(item.get("batch_done", 0)),
        "resolved":     int(item.get("batch_resolved", 0)),
        "failed":       int(item.get("batch_failed", 0)),
        "advisory":     int(item.get("batch_advisory", 0)),
        "summary":      item.get("batch_summary", ""),
        "started_at":   item.get("batch_started_at", ""),
        "completed_at": item.get("batch_completed_at", ""),
    })


def start_batch_remediate(body_str, context):
    """POST /dashboard/api/remediate-all — kick off async batch remediation."""
    body = parse_body(body_str) or {}
    retry_enabled = bool(body.get("retry_enabled", True))
    settings = {
        "runbook_priority": bool(body.get("runbook_priority", True)),
        "retry_enabled":    retry_enabled,
        "max_retries":      max(1, min(int(body.get("max_retries", 3)), 5)),
    }

    scan     = findings_table.scan(FilterExpression=Attr("status").eq("PENDING_APPROVAL"))
    eligible = scan.get("Items", [])

    if not eligible:
        return respond(200, {"status": "no_eligible_findings", "count": 0})

    fn_name = os.environ.get("AWS_LAMBDA_FUNCTION_NAME", "")
    if not fn_name:
        return respond(500, {"error": "Cannot determine Lambda function name for self-invoke"})

    settings_table.put_item(Item={
        "setting_key":      "batch_remediation_status",
        "value":            "running",
        "batch_total":      len(eligible),
        "batch_done":       0,
        "batch_resolved":   0,
        "batch_failed":     0,
        "batch_advisory":   0,
        "batch_started_at": now_iso(),
        "updated_at":       now_iso(),
    })

    try:
        lam.invoke(
            FunctionName=fn_name,
            InvocationType="Event",
            Payload=json.dumps({"__batch_remediate": True, "settings": settings}).encode(),
        )
    except Exception as e:
        settings_table.put_item(Item={
            "setting_key": "batch_remediation_status",
            "value": "idle", "updated_at": now_iso(),
        })
        return respond(500, {"error": f"Failed to start batch: {e}"})

    return respond(200, {"status": "started", "count": len(eligible)})


def _do_batch_remediate(settings: dict):
    """
    Internal async worker — iterates all PENDING_APPROVAL findings and attempts
    AI-guided remediation with optional runbook priority and retry logic.
    """
    runbook_priority = settings.get("runbook_priority", True)
    retry_enabled    = settings.get("retry_enabled", True)
    max_retries      = int(settings.get("max_retries", 3)) if retry_enabled else 1

    scan     = findings_table.scan(FilterExpression=Attr("status").eq("PENDING_APPROVAL"))
    eligible = scan.get("Items", [])

    total    = len(eligible)
    resolved = failed_count = advisory_count = 0

    for idx, item in enumerate(eligible):
        # Update progress counter
        try:
            settings_table.update_item(
                Key={"setting_key": "batch_remediation_status"},
                UpdateExpression="SET batch_done = :d",
                ExpressionAttributeValues={":d": idx},
            )
        except Exception:
            pass

        finding_id    = item["finding_id"]
        resource_type = item.get("resource_type", "")
        resource_id   = item.get("resource_id", "")
        failure_history: list = []
        success = False

        # ── STEP 1: Try existing READY runbook if priority mode is on ──────────
        if (runbook_priority
                and item.get("runbook")
                and item.get("runbook_status") == "READY"):
            logs = ["[Batch] Priority mode: applying existing runbook..."]
            try:
                s, undo_data, logs, inline = _apply_inline_for_finding(resource_type, resource_id, logs)
                if not inline:
                    logs.append("[Batch] Resource type is advisory-only — skipping inline apply")
                elif s:
                    _update_finding_batch_result(finding_id, True, logs, undo_data, item)
                    resolved += 1
                    success = True
                else:
                    failure_history.append({"attempt": 0, "source": "existing_runbook", "logs": logs})
            except Exception as e:
                failure_history.append({"attempt": 0, "source": "existing_runbook",
                                        "logs": [f"Exception: {e}"]})

        if success:
            continue

        # ── STEP 2: AI generation + inline apply, with retries ─────────────────
        for attempt in range(1, max_retries + 1):
            attempt_logs = [f"[Batch] AI attempt {attempt}/{max_retries}"]

            if failure_history:
                attempt_logs.append(f"[Context] {len(failure_history)} prior failure(s) fed to AI:")
                for fh in failure_history:
                    for ll in fh.get("logs", [])[-4:]:
                        attempt_logs.append(f"  ↳ {ll}")

            runbook, err = _generate_runbook_with_context(item, failure_history)
            if err:
                attempt_logs.append(f"[Batch] Runbook generation failed: {err}")
                failure_history.append({"attempt": attempt, "source": "ai_generate",
                                        "logs": attempt_logs[:]})
                continue

            try:
                s, undo_data, all_logs, inline = _apply_inline_for_finding(
                    resource_type, resource_id, attempt_logs
                )

                if not inline:
                    # Advisory resource — store runbook + mark MANUAL_REVIEW
                    _update_finding_batch_result(finding_id, False, all_logs, {}, item, advisory=True)
                    advisory_count += 1
                    success = True  # exit retry loop — nothing more to try inline
                    break

                if s:
                    _update_finding_batch_result(finding_id, True, all_logs, undo_data, item)
                    resolved += 1
                    success = True
                    break
                else:
                    failure_history.append({"attempt": attempt, "source": "ai_apply",
                                            "logs": all_logs[:]})
            except Exception as e:
                attempt_logs.append(f"Exception during apply: {e}")
                failure_history.append({"attempt": attempt, "source": "exception",
                                        "logs": attempt_logs[:]})

        if not success:
            all_fail_logs: list = []
            for fh in failure_history:
                all_fail_logs.extend(fh.get("logs", []))
            _update_finding_batch_result(finding_id, False, all_fail_logs, {}, item, failed=True)
            failed_count += 1

    # ── Finalise batch status ──────────────────────────────────────────────────
    try:
        settings_table.put_item(Item={
            "setting_key":        "batch_remediation_status",
            "value":              "idle",
            "batch_total":        total,
            "batch_done":         total,
            "batch_resolved":     resolved,
            "batch_failed":       failed_count,
            "batch_advisory":     advisory_count,
            "batch_summary": (
                f"Resolved: {resolved}  |  Advisory: {advisory_count}  |  Failed: {failed_count}"
            ),
            "batch_completed_at": now_iso(),
            "updated_at":         now_iso(),
        })
    except Exception:
        pass


# ── MAIN HANDLER ──────────────────────────────────────────────────────────────

def lambda_handler(event, context):
    # Async self-invocation for infrastructure termination
    if event.get("__terminate"):
        _do_terminate()
        return {"status": "terminated"}

    # Async self-invocation for batch remediation
    if event.get("__batch_remediate"):
        _do_batch_remediate(event.get("settings", {}))
        return {"status": "batch_complete"}

    method = event.get("httpMethod", "GET")
    path   = event.get("path", "/dashboard").rstrip("/") or "/dashboard"
    body   = event.get("body") or ""

    if method == "OPTIONS":
        return respond(200, "")

    if method == "GET" and path in ("/dashboard", "/prod/dashboard"):
        from dashboard_html import DASHBOARD_HTML
        return respond(200, DASHBOARD_HTML, content_type="text/html")

    if method == "GET" and path.endswith("/api/findings"):
        return list_findings()
    if method == "DELETE" and path.endswith("/api/findings"):
        return clear_findings()

    if method == "GET" and path.endswith("/api/settings"):
        return get_settings()
    if method == "PUT" and path.endswith("/api/settings"):
        return update_settings(body)

    if method == "POST" and path.endswith("/api/action"):
        return take_action(body)

    if method == "POST" and path.endswith("/api/email"):
        return resend_email(body)

    if method == "GET" and path.endswith("/api/control"):
        return get_pipeline_status()
    if method == "POST" and path.endswith("/api/control"):
        return control_pipeline(body, context)

    if method == "POST" and path.endswith("/api/simulate"):
        return start_simulation(body)
    if method == "DELETE" and path.endswith("/api/simulate"):
        return cleanup_simulation(body)

    if method == "GET" and path.endswith("/api/ai-config"):
        return get_ai_config()
    if method == "PUT" and path.endswith("/api/ai-config"):
        return update_ai_config(body)
    if method == "POST" and path.endswith("/api/ai-models"):
        return fetch_ai_models(body)

    if method == "POST" and path.endswith("/api/ai-runbook"):
        return generate_runbook(body)
    if method == "POST" and path.endswith("/api/apply-runbook"):
        return apply_runbook(body)
    if method == "POST" and path.endswith("/api/undo-runbook"):
        return undo_runbook(body)

    if method == "GET" and path.endswith("/api/remediate-all"):
        return get_batch_status()
    if method == "POST" and path.endswith("/api/remediate-all"):
        return start_batch_remediate(body, context)

    return respond(404, {"error": f"Unknown route: {method} {path}"})
