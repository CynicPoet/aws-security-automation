"""
response_validator.py — Validate and parse AI provider JSON responses.

The AI must return a strict JSON schema. This module parses the response,
validates required fields, and applies hardcoded safety overrides that
the AI cannot bypass.
"""

import json
import re

VALID_RISK_LEVELS = {"HIGH", "MEDIUM", "LOW"}
VALID_PLAYBOOKS = {"s3_remediation", "iam_remediation", "vpc_remediation", "manual", "none"}

REQUIRED_FIELDS = [
    "risk_level",
    "is_false_positive",
    "analysis",
    "safe_to_auto_remediate",
    "recommended_playbook",
    "recommended_actions",
]


def validate_and_parse(raw_response: str, infrastructure_context: dict) -> dict:
    """
    Parse the AI's raw text response, validate schema, and apply safety overrides.

    Safety overrides (hardcoded — AI cannot bypass):
    - Resources tagged AutoRemediationExclude=true → force safe_to_auto_remediate=False
    - Resources tagged Environment=Production → force safe_to_auto_remediate=False
    - is_default_sg=True in context → force safe_to_auto_remediate=False
    - is_service_account or is_ci_pipeline → force safe_to_auto_remediate=False
    - recommended_playbook not in approved list → force to 'manual'

    Args:
        raw_response:           Raw text from the AI provider.
        infrastructure_context: Context dict built by infrastructure_context.py

    Returns:
        Validated and safety-checked dict.

    Raises:
        ValueError: If the response cannot be parsed or required fields are missing.
    """
    # Strip markdown code fences if present (e.g., ```json ... ```)
    cleaned = raw_response.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"AI response is not valid JSON: {exc}\nRaw: {raw_response[:500]}") from exc

    # ── REQUIRED FIELD CHECK ──────────────────────────────────────────────────
    missing = [f for f in REQUIRED_FIELDS if f not in data]
    if missing:
        raise ValueError(f"AI response missing required fields: {missing}")

    # ── TYPE / ENUM VALIDATION ────────────────────────────────────────────────
    if data["risk_level"] not in VALID_RISK_LEVELS:
        data["risk_level"] = "HIGH"  # Safe default: treat unknown as high risk

    if not isinstance(data["is_false_positive"], bool):
        data["is_false_positive"] = False

    if not isinstance(data["safe_to_auto_remediate"], bool):
        data["safe_to_auto_remediate"] = False

    if data["recommended_playbook"] not in VALID_PLAYBOOKS:
        data["recommended_playbook"] = "manual"

    if not isinstance(data["recommended_actions"], list):
        data["recommended_actions"] = []

    # ── HARDCODED SAFETY OVERRIDES ────────────────────────────────────────────
    tags = infrastructure_context.get("resource_tags", {})
    vpc_ctx = infrastructure_context.get("vpc_context", {})
    iam_ctx = infrastructure_context.get("iam_context", {})

    override_reason = None

    if tags.get("AutoRemediationExclude", "").lower() == "true":
        data["safe_to_auto_remediate"] = False
        override_reason = "Resource tagged AutoRemediationExclude=true"

    elif tags.get("Environment", "").lower() == "production":
        data["safe_to_auto_remediate"] = False
        override_reason = "Production-tagged resource — always requires admin approval"

    elif vpc_ctx.get("is_default_sg"):
        data["safe_to_auto_remediate"] = False
        override_reason = "Default VPC security group — never auto-modify"

    elif iam_ctx.get("is_service_account") or iam_ctx.get("is_ci_pipeline"):
        data["safe_to_auto_remediate"] = False
        override_reason = "IAM user is service account or CI pipeline — admin approval required"

    if override_reason:
        data["safety_override_applied"] = True
        data["safety_override_reason"] = override_reason
        if not data.get("escalation_reason"):
            data["escalation_reason"] = override_reason
    else:
        data["safety_override_applied"] = False

    # Ensure optional fields exist
    data.setdefault("false_positive_reason", None)
    data.setdefault("escalation_reason", None)

    return data
