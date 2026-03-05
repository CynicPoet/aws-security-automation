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
import boto3
from datetime import datetime, timezone
from botocore.exceptions import ClientError

FINDINGS_TABLE    = os.environ["FINDINGS_TABLE"]
SETTINGS_TABLE    = os.environ["SETTINGS_TABLE"]
STATE_MACHINE_ARN = os.environ.get("STATE_MACHINE_ARN", "")
EB_RULE_NAME      = os.environ.get("EB_RULE_NAME", "securityhub-finding-rule")
SNS_TOPIC_ARN     = os.environ.get("SNS_TOPIC_ARN", "")
ACCOUNT_ID        = os.environ.get("ACCOUNT_ID", "")
REGION            = os.environ.get("AWS_REGION", "us-east-1")

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
    return respond(200, {
        "email_notifications": email,
        "auto_remediation": auto_rem,
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
    return respond(200, {"status": "ok", "updated": updated})


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

    # 5. Delete EventBridge rule (targets must be removed first)
    try:
        try:
            targets = events.list_targets_by_rule(Rule=EB_RULE_NAME)
            tids = [t["Id"] for t in targets.get("Targets", [])]
            if tids:
                events.remove_targets(Rule=EB_RULE_NAME, Ids=tids)
        except Exception:
            pass
        try:
            events.delete_rule(Name=EB_RULE_NAME)
        except Exception:
            pass
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


# ── MAIN HANDLER ──────────────────────────────────────────────────────────────

def lambda_handler(event, context):
    # Async self-invocation for infrastructure termination
    if event.get("__terminate"):
        _do_terminate()
        return {"status": "terminated"}

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

    return respond(404, {"error": f"Unknown route: {method} {path}"})
