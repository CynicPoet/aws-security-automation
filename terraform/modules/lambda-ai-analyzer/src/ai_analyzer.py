"""
ai_analyzer.py — AI-powered security finding analyzer Lambda.

Receives a Security Hub finding + infrastructure context, calls the configured
AI provider (Gemini or Claude), validates the response, and returns a
structured analysis object used by the Step Functions state machine to decide
the remediation path.

Environment variables:
  AI_PROVIDER   — 'gemini' or 'claude'   (default: gemini)
  AI_MODEL      — model name             (default: gemini-2.5-flash)
  SECRET_NAME   — Secrets Manager name   (default: security-automation/ai-api-key)
  AWS_REGION    — AWS region             (default: us-east-1)

Input event:
  { "finding": { finding_id, resource_type, resource_id, severity, title, description, ... } }

Returns (on success):
  {
    "risk_level": "HIGH"|"MEDIUM"|"LOW",
    "is_false_positive": bool,
    "false_positive_reason": str|null,
    "analysis": str,
    "safe_to_auto_remediate": bool,
    "escalation_reason": str|null,
    "recommended_playbook": str,
    "recommended_actions": [...],
    "safety_override_applied": bool,
    "provider_used": str,
    "model_used": str
  }
"""

import json
import logging
import os
import time
import boto3
from botocore.exceptions import ClientError

from infrastructure_context import build_infrastructure_context
from response_validator import validate_and_parse
from providers import get_provider

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = os.environ.get("AWS_REGION", "us-east-1")
AI_PROVIDER = os.environ.get("AI_PROVIDER", "gemini")
AI_MODEL = os.environ.get("AI_MODEL", "gemini-2.5-flash")
SECRET_NAME = os.environ.get("SECRET_NAME", "security-automation/ai-api-key")
SETTINGS_TABLE = os.environ.get("SETTINGS_TABLE", "")

# Approved playbooks that the AI is allowed to recommend
APPROVED_PLAYBOOKS = ["s3_remediation", "iam_remediation", "vpc_remediation", "manual"]

SYSTEM_PROMPT_TEMPLATE = """AWS security analyst. Analyze finding and return JSON only.

CONTEXT:{infrastructure_context}

FINDING:{finding_details}

RULES(non-negotiable):
1. tag AutoRemediationExclude=true → safe_to_auto_remediate=false
2. tag Environment=Production → safe_to_auto_remediate=false
3. is_default_sg=true → safe_to_auto_remediate=false
4. tag ServiceAccount=true OR Role=CI-Pipeline → safe_to_auto_remediate=false
5. S3 website_hosting_enabled=true AND intentional_public_tag=true → is_false_positive=true
6. playbook must be one of: {approved_playbooks}
7. No deletions. All actions reversible.

Return ONLY this JSON (no markdown, no fences):
{{"risk_level":"HIGH"|"MEDIUM"|"LOW","is_false_positive":true|false,"false_positive_reason":"str"|null,"analysis":"1-2 sentences","safe_to_auto_remediate":true|false,"escalation_reason":"str"|null,"recommended_playbook":"s3_remediation"|"iam_remediation"|"vpc_remediation"|"manual"|"none","recommended_actions":[{{"action_id":1,"playbook":"name","description":"str","risk":"LOW"|"MEDIUM"|"HIGH","reversible":true|false}}]}}"""


def lambda_handler(event: dict, context) -> dict:
    """Entry point — analyze a Security Hub finding with AI."""
    start_ms = int(time.time() * 1000)

    finding = event.get("finding", event)
    finding_id = finding.get("finding_id", finding.get("Id", "unknown"))
    resource_type = finding.get("resource_type", finding.get("ResourceType", "unknown"))
    resource_id = finding.get("resource_id", finding.get("ResourceId", "unknown"))
    severity = finding.get("severity", "MEDIUM")

    # ── 0. CHECK DYNAMODB FOR RUNTIME AI CONFIG OVERRIDES ────────────────────
    active_provider, active_model = _get_ai_config_override()

    _log("AI_ANALYSIS_START", finding_id, resource_type, resource_id, severity,
         message=f"AI analysis started using provider={active_provider} model={active_model}")

    # ── 1. GET API KEY FROM SECRETS MANAGER ──────────────────────────────────
    try:
        api_key = _get_api_key()
    except Exception as exc:
        _log("ERROR", finding_id, resource_type, resource_id, severity,
             message=f"Failed to retrieve AI API key from Secrets Manager: {exc}")
        return _fallback_response(resource_type, f"Could not retrieve API key: {exc}", finding)

    # ── 2. BUILD INFRASTRUCTURE CONTEXT ──────────────────────────────────────
    try:
        infra_context = build_infrastructure_context(finding, region=REGION)
    except Exception as exc:
        _log("ERROR", finding_id, resource_type, resource_id, severity,
             message=f"Failed to build infrastructure context: {exc}")
        infra_context = {"resource_type": resource_type, "resource_id": resource_id, "resource_tags": {}}

    # ── 3. BUILD PROMPT ───────────────────────────────────────────────────────
    finding_details = {
        "finding_id": finding_id,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "severity": severity,
        "title": finding.get("title", finding.get("Title", "")),
        "description": finding.get("description", finding.get("Description", "")),
        "compliance_status": finding.get("compliance_status", "FAILED"),
    }

    prompt = SYSTEM_PROMPT_TEMPLATE.format(
        infrastructure_context=json.dumps(_trim_context(infra_context), default=str),
        finding_details=json.dumps(finding_details, default=str),
        approved_playbooks=",".join(APPROVED_PLAYBOOKS),
    )

    # ── 4. CALL AI PROVIDER ───────────────────────────────────────────────────
    provider = get_provider(active_provider, api_key, active_model)
    try:
        raw_response = provider.analyze(prompt, max_tokens=600)
    except RuntimeError as exc:
        _log("ERROR", finding_id, resource_type, resource_id, severity,
             message=f"AI provider call failed: {exc}")
        return _fallback_response(resource_type, f"AI provider error: {exc}", finding)

    # ── 5. VALIDATE AND APPLY SAFETY OVERRIDES ────────────────────────────────
    try:
        analysis = validate_and_parse(raw_response, infra_context)
    except ValueError as exc:
        _log("ERROR", finding_id, resource_type, resource_id, severity,
             message=f"AI response validation failed: {exc}")
        return _fallback_response(resource_type, f"Response validation failed: {exc}", finding)

    duration_ms = int(time.time() * 1000) - start_ms
    analysis["provider_used"] = active_provider
    analysis["model_used"] = active_model

    # ── 6. CHECK AUTO-REMEDIATION TOGGLE ─────────────────────────────────────
    # If the dashboard toggle is OFF, force all findings to manual approval.
    if not _is_auto_remediation_enabled():
        if analysis.get("safe_to_auto_remediate"):
            analysis["safe_to_auto_remediate"] = False
            analysis["escalation_reason"] = (
                (analysis.get("escalation_reason") or "") +
                " [Auto-remediation disabled via dashboard toggle]"
            ).strip()
            _log("AUTO_REM_DISABLED", finding_id, resource_type, resource_id, severity,
                 message="Auto-remediation override: dashboard toggle is OFF — routing to admin approval")

    _log(
        "AI_ANALYSIS_COMPLETE", finding_id, resource_type, resource_id, severity,
        message=(
            f"AI analysis complete: risk={analysis['risk_level']}, "
            f"auto_remediate={analysis['safe_to_auto_remediate']}, "
            f"false_positive={analysis['is_false_positive']}"
        ),
        ai_risk_level=analysis["risk_level"],
        ai_safe_to_auto=analysis["safe_to_auto_remediate"],
        duration_ms=duration_ms,
    )

    return analysis


# ── HELPERS ───────────────────────────────────────────────────────────────────

def _trim_context(ctx: dict) -> dict:
    """
    Reduce infrastructure context to only the fields the AI needs for safety rules.
    Keeps tags (for safety checks) and key booleans. Drops verbose details.
    """
    trimmed = {
        "resource_type": ctx.get("resource_type", ""),
        "resource_id":   ctx.get("resource_id", ""),
        "resource_tags": ctx.get("resource_tags", {}),
    }
    # Keep only the relevant sub-context (s3/iam/vpc)
    for key in ("s3_context", "iam_context", "vpc_context"):
        if key in ctx:
            sub = ctx[key]
            # Strip verbose keys not needed for safety rule evaluation
            trimmed[key] = {k: v for k, v in sub.items()
                            if k not in ("attached_eni_count", "attached_instance_count",
                                         "has_cloudfront_origin", "last_used_service")}
    return trimmed


def _get_ai_config_override() -> tuple:
    """
    Read ai_provider and ai_model from DynamoDB settings table (hot-swap support).
    Falls back to environment variables if DynamoDB is unreachable or keys not set.
    Returns: (provider, model) tuple.
    """
    if not SETTINGS_TABLE:
        return AI_PROVIDER, AI_MODEL
    try:
        db = boto3.resource("dynamodb", region_name=REGION)
        table = db.Table(SETTINGS_TABLE)
        provider_item = table.get_item(Key={"setting_key": "ai_provider"}).get("Item")
        model_item    = table.get_item(Key={"setting_key": "ai_model"}).get("Item")
        provider = provider_item.get("value", AI_PROVIDER) if provider_item else AI_PROVIDER
        model    = model_item.get("value", AI_MODEL)    if model_item    else AI_MODEL
        return provider, model
    except Exception:
        return AI_PROVIDER, AI_MODEL  # fail-safe: fall back to env vars


def _is_auto_remediation_enabled() -> bool:
    """
    Read the auto_remediation setting from DynamoDB settings table.
    Returns True (auto-remediation ON) if: setting is missing, value='true', or DynamoDB is unreachable.
    Returns False only when setting explicitly set to 'false'.
    """
    if not SETTINGS_TABLE:
        return True  # no table configured → default ON
    try:
        db = boto3.resource("dynamodb", region_name=REGION)
        table = db.Table(SETTINGS_TABLE)
        result = table.get_item(Key={"setting_key": "auto_remediation"})
        item = result.get("Item")
        if item is None:
            return True  # not set → default ON
        return item.get("value", "true").lower() != "false"
    except Exception:
        return True  # fail-safe: if DynamoDB unreachable, don't block remediation


def _get_api_key() -> str:
    """Retrieve the AI API key from AWS Secrets Manager."""
    client = boto3.client("secretsmanager", region_name=REGION)
    response = client.get_secret_value(SecretId=SECRET_NAME)
    secret = json.loads(response["SecretString"])
    return secret["api_key"]


def _fallback_response(resource_type: str, error_reason: str, finding: dict = None) -> dict:
    """
    Return a safe fallback when the AI call fails.

    Auto-remediates if:
      - resource type has a known playbook (S3 / SG / IAM)
      - AND finding title/description contains no safety keywords
        (CI-Pipeline, Production, ServiceAccount, AutoRemediationExclude)

    Escalates to admin otherwise.
    """
    playbook = "manual"
    if "S3" in resource_type:
        playbook = "s3_remediation"
    elif "Iam" in resource_type:
        playbook = "iam_remediation"
    elif "SecurityGroup" in resource_type:
        playbook = "vpc_remediation"

    # Only auto-remediate when we have a known playbook AND no safety keywords
    safe_to_auto = playbook != "manual"
    if safe_to_auto and finding:
        text = (
            finding.get("title", "") + " " + finding.get("description", "")
        ).lower()
        safety_keywords = [
            "ci-pipeline", "ci_pipeline", "production", "service account",
            "serviceaccount", "autoremediationexclude",
        ]
        if any(kw in text for kw in safety_keywords):
            safe_to_auto = False

    action_desc = (
        "Approve automated remediation"
        if safe_to_auto
        else "AI unavailable — admin should review and decide"
    )

    # Respect the dashboard auto-remediation toggle even in fallback path
    if safe_to_auto and not _is_auto_remediation_enabled():
        safe_to_auto = False

    return {
        "risk_level": "HIGH",
        "is_false_positive": False,
        "false_positive_reason": None,
        "analysis": (
            f"AI analysis unavailable ({error_reason}). "
            + ("Proceeding with automated remediation." if safe_to_auto else "Manual review recommended.")
        ),
        "safe_to_auto_remediate": safe_to_auto,
        "escalation_reason": (
            None if safe_to_auto
            else f"AI analysis failed — defaulting to admin escalation."
        ),
        "recommended_playbook": playbook,
        "recommended_actions": [
            {
                "action_id": 1,
                "playbook": playbook,
                "description": action_desc,
                "risk": "MEDIUM" if safe_to_auto else "UNKNOWN",
                "reversible": True,
            }
        ],
        "safety_override_applied": False,
        "provider_used": AI_PROVIDER,  # env-var fallback (no DB override in fallback path)
        "model_used": AI_MODEL,
    }


def _log(event_type: str, finding_id: str, resource_type: str, resource_id: str,
         severity: str, message: str, **kwargs) -> None:
    """Emit a structured JSON log entry."""
    entry = {
        "event_type": event_type,
        "finding_id": finding_id,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "severity": severity,
        "message": message,
    }
    entry.update(kwargs)
    logger.info(json.dumps(entry))
