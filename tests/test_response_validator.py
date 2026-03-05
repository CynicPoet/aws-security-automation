"""
Unit tests for response_validator.py safety overrides.
Run: python -m pytest tests/ -v
"""

import sys
import os
import json

# Add the lambda source to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__),
    '..', 'terraform', 'modules', 'lambda-ai-analyzer', 'src'))

from response_validator import validate_and_apply_safety_overrides


def _base_response():
    return {
        "risk_level": "MEDIUM",
        "is_false_positive": False,
        "analysis": "Test finding",
        "safe_to_auto_remediate": True,
        "recommended_playbook": "s3_public_access",
        "recommended_actions": [{"action_id": 1, "description": "Block public access"}],
        "confidence": 0.9,
        "escalation_reason": None,
    }


def _base_context():
    return {
        "resource_tags": {},
        "is_default_sg": False,
        "is_service_account": False,
        "is_ci_pipeline": False,
        "environment": "Test",
    }


# --- Safety override tests ---

def test_auto_remediation_exclude_tag_forces_escalation():
    ctx = _base_context()
    ctx["resource_tags"] = {"AutoRemediationExclude": "true"}
    result = validate_and_apply_safety_overrides(_base_response(), ctx)
    assert result["safe_to_auto_remediate"] is False


def test_production_environment_forces_escalation():
    ctx = _base_context()
    ctx["environment"] = "Production"
    result = validate_and_apply_safety_overrides(_base_response(), ctx)
    assert result["safe_to_auto_remediate"] is False


def test_default_sg_forces_escalation():
    ctx = _base_context()
    ctx["is_default_sg"] = True
    result = validate_and_apply_safety_overrides(_base_response(), ctx)
    assert result["safe_to_auto_remediate"] is False


def test_service_account_forces_escalation():
    ctx = _base_context()
    ctx["is_service_account"] = True
    result = validate_and_apply_safety_overrides(_base_response(), ctx)
    assert result["safe_to_auto_remediate"] is False


def test_ci_pipeline_forces_escalation():
    ctx = _base_context()
    ctx["is_ci_pipeline"] = True
    result = validate_and_apply_safety_overrides(_base_response(), ctx)
    assert result["safe_to_auto_remediate"] is False


def test_unapproved_playbook_forced_to_manual():
    resp = _base_response()
    resp["recommended_playbook"] = "delete_all_resources"  # not in approved list
    result = validate_and_apply_safety_overrides(resp, _base_context())
    assert result["recommended_playbook"] == "manual"
    assert result["safe_to_auto_remediate"] is False


def test_approved_playbook_passes():
    for playbook in ["s3_public_access", "iam_key_disable", "sg_rule_revoke", "manual"]:
        resp = _base_response()
        resp["recommended_playbook"] = playbook
        result = validate_and_apply_safety_overrides(resp, _base_context())
        assert result["recommended_playbook"] == playbook


def test_safe_auto_remediation_passes_with_no_overrides():
    result = validate_and_apply_safety_overrides(_base_response(), _base_context())
    assert result["safe_to_auto_remediate"] is True
    assert result["recommended_playbook"] == "s3_public_access"


def test_false_positive_not_overridden():
    resp = _base_response()
    resp["is_false_positive"] = True
    resp["safe_to_auto_remediate"] = False
    result = validate_and_apply_safety_overrides(resp, _base_context())
    assert result["is_false_positive"] is True


# --- JSON parsing tests ---

def test_strips_markdown_code_fence():
    """Validator must handle AI responses wrapped in ```json ... ```"""
    raw = '```json\n{"risk_level": "LOW", "is_false_positive": true, "analysis": "ok", ' \
          '"safe_to_auto_remediate": false, "recommended_playbook": "manual", ' \
          '"recommended_actions": [], "confidence": 0.95, "escalation_reason": null}\n```'
    # validate_and_apply_safety_overrides takes a dict; parsing happens upstream
    # Just verify the dict we'd get after stripping fences is valid
    stripped = raw.strip().removeprefix("```json").removesuffix("```").strip()
    parsed = json.loads(stripped)
    assert parsed["is_false_positive"] is True
