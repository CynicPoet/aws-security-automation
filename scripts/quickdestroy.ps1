# quickdestroy.ps1 — Full teardown for AWS Security Automation
# Cleans up ALL resources: Terraform-managed + simulation leftovers + Config + Security Hub
# Usage: .\scripts\quickdestroy.ps1

$ErrorActionPreference = "SilentlyContinue"   # don't abort on individual resource failures
$SCRIPTS_DIR = $PSScriptRoot
$TF_DIR      = [System.IO.Path]::GetFullPath("$SCRIPTS_DIR\..\terraform")

# ── Load credentials ──────────────────────────────────────────────────────────
$CONFIG = "$SCRIPTS_DIR\config.ps1"
if (-not (Test-Path $CONFIG)) {
    Write-Host "ERROR: scripts\config.ps1 not found." -ForegroundColor Red; exit 1
}
. $CONFIG
$env:AWS_ACCESS_KEY_ID     = $AWS_ACCESS_KEY_ID
$env:AWS_SECRET_ACCESS_KEY = $AWS_SECRET_ACCESS_KEY
$env:AWS_DEFAULT_REGION    = $AWS_REGION

# ── Helpers ───────────────────────────────────────────────────────────────────
function Write-Header($msg) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "  $msg" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
}
function Write-Step($n, $total, $msg) {
    Write-Host ""
    Write-Host "[$n/$total] $msg" -ForegroundColor Yellow
    Write-Host ("-" * 48) -ForegroundColor DarkGray
}
function Write-SectionHeader($msg) {
    Write-Host ""
    Write-Host "  $msg" -ForegroundColor Cyan
}

# ── Write Python helper to temp file (avoids all PowerShell/Python escaping issues) ──
$tmpPy = "$env:TEMP\sa_destroy.py"

Set-Content -Path $tmpPy -Encoding UTF8 -Value @'
"""
quickdestroy helper — called by quickdestroy.ps1 with a mode argument.
Modes: discover | sfn | config | securityhub | sim | post | verify
"""
import boto3, sys, os

REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
KEY    = os.environ.get("AWS_ACCESS_KEY_ID", "")
SEC    = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
creds  = dict(region_name=REGION, aws_access_key_id=KEY, aws_secret_access_key=SEC)

def tag_del(msg):  print(f"  [DELETED]   {msg}", flush=True)
def tag_skip(msg): print(f"  [SKIPPED]   {msg}", flush=True)
def tag_info(msg): print(f"  [INFO]      {msg}", flush=True)
def tag_found(msg):print(f"  [FOUND]     {msg}", flush=True)
def tag_clean(msg):print(f"  [CLEAN]     {msg}", flush=True)

# Validate connectivity
sts = boto3.client("sts", **creds)
try:
    ACCOUNT_ID = sts.get_caller_identity()["Account"]
except Exception as e:
    print(f"ERROR: Cannot connect to AWS - {e}"); sys.exit(1)

mode = sys.argv[1] if len(sys.argv) > 1 else "verify"

# =============================================================================
# DISCOVER — show every billable resource before deletion
# =============================================================================
if mode == "discover":
    found = {}

    # AWS Config
    cfg = boto3.client("config", **creds)
    recorders = cfg.describe_configuration_recorders().get("ConfigurationRecorders", [])
    statuses  = {s["name"]: s for s in
                 cfg.describe_configuration_recorder_status().get("ConfigurationRecordersStatus", [])}
    for r in recorders:
        s = statuses.get(r["name"], {})
        found.setdefault("AWS Config Recorders", []).append(
            f"{r['name']}  recording={s.get('recording', '?')}")

    # Config delivery channels
    channels = cfg.describe_delivery_channels().get("DeliveryChannels", [])
    for ch in channels:
        found.setdefault("AWS Config Delivery Channels", []).append(ch["name"])

    # Security Hub standards
    sh = boto3.client("securityhub", **creds)
    try:
        subs = sh.get_enabled_standards().get("StandardsSubscriptions", [])
        for s in subs:
            if s.get("StandardsStatus") not in ("DELETING", "INCOMPLETE"):
                label = s["StandardsArn"].split("/")[-3] if "/" in s["StandardsArn"] else s["StandardsArn"]
                found.setdefault("Security Hub Standards", []).append(
                    f"{label}  [{s.get('StandardsStatus')}]")
    except: pass

    # Step Functions
    sfn = boto3.client("stepfunctions", **creds)
    for sm in sfn.list_state_machines().get("stateMachines", []):
        if "Security" in sm["name"] or "security" in sm["name"]:
            execs = sfn.list_executions(stateMachineArn=sm["stateMachineArn"],
                                         statusFilter="RUNNING").get("executions", [])
            found.setdefault("Step Functions State Machines", []).append(
                f"{sm['name']}  ({len(execs)} running executions)")

    # Lambda
    lam = boto3.client("lambda", **creds)
    fns = [f["FunctionName"] for f in lam.list_functions().get("Functions", [])
           if "security-auto" in f["FunctionName"]]
    if fns: found["Lambda Functions"] = fns

    # DynamoDB
    db = boto3.client("dynamodb", **creds)
    tables = [t for t in db.list_tables().get("TableNames", []) if "security" in t]
    if tables: found["DynamoDB Tables"] = tables

    # API Gateway
    apigw = boto3.client("apigateway", **creds)
    apis = [f"{a['name']}  (id={a['id']})" for a in apigw.get_rest_apis().get("items", [])
            if "security" in a["name"].lower()]
    if apis: found["API Gateway"] = apis

    # SNS
    sns = boto3.client("sns", **creds)
    topics = [t["TopicArn"].split(":")[-1] for t in sns.list_topics().get("Topics", [])
              if "security" in t["TopicArn"]]
    if topics: found["SNS Topics"] = topics

    # Secrets Manager
    sm_client = boto3.client("secretsmanager", **creds)
    secrets = [s["Name"] for s in sm_client.list_secrets().get("SecretList", [])
               if "security-automation" in s["Name"]]
    if secrets: found["Secrets Manager"] = secrets

    # EventBridge
    eb = boto3.client("events", **creds)
    rules = [f"{r['Name']}  [{r.get('State','?')}]"
             for r in eb.list_rules().get("Rules", [])
             if "securityhub" in r["Name"].lower() or "security-auto" in r["Name"].lower()]
    if rules: found["EventBridge Rules"] = rules

    # S3 — sim + config buckets
    s3 = boto3.client("s3", **creds)
    buckets = [b["Name"] for b in s3.list_buckets().get("Buckets", [])
               if b["Name"].startswith("sim-pub-") or
                  ("security-auto" in b["Name"] and "config" in b["Name"])]
    if buckets: found["S3 Buckets (sim + config)"] = buckets

    # IAM — sim users
    iam = boto3.client("iam", **creds)
    users = [u["UserName"] for u in iam.list_users().get("Users", [])
             if u["UserName"].startswith("sim-")]
    if users: found["IAM Users (sim)"] = users

    # EC2 — sim security groups
    ec2 = boto3.client("ec2", **creds)
    sgs = ec2.describe_security_groups(
        Filters=[{"Name": "group-name", "Values": ["sim-sg-*"]}]
    ).get("SecurityGroups", [])
    if sgs: found["EC2 Security Groups (sim)"] = [f"{s['GroupId']} ({s['GroupName']})" for s in sgs]

    # CloudWatch Log Groups
    logs = boto3.client("logs", **creds)
    lgs = [g["logGroupName"] for g in logs.describe_log_groups().get("logGroups", [])
           if "security-auto" in g["logGroupName"]]
    if lgs: found["CloudWatch Log Groups"] = lgs

    # Print results
    if found:
        total = sum(len(v) for v in found.values())
        print(f"\n  Found {total} resource(s) to delete:\n")
        for category, items in found.items():
            print(f"  {category}:")
            for item in items:
                print(f"    - {item}")
    else:
        print("\n  No project resources found. Account is already clean.")
    sys.exit(0)

# =============================================================================
# SFN — stop all running executions
# =============================================================================
if mode == "sfn":
    sfn = boto3.client("stepfunctions", **creds)
    sms = sfn.list_state_machines().get("stateMachines", [])
    project_sms = [sm for sm in sms if "Security" in sm["name"] or "security" in sm["name"]]
    if not project_sms:
        tag_skip("No project Step Functions state machines found")
    for sm in project_sms:
        try:
            pager = sfn.get_paginator("list_executions")
            stopped = 0
            for page in pager.paginate(stateMachineArn=sm["stateMachineArn"],
                                        statusFilter="RUNNING"):
                for ex in page["executions"]:
                    try:
                        sfn.stop_execution(executionArn=ex["executionArn"], cause="quickdestroy")
                        stopped += 1
                    except: pass
            if stopped:
                tag_del(f"Stopped {stopped} execution(s) in: {sm['name']}")
            else:
                tag_skip(f"No running executions in: {sm['name']}")
        except Exception as e:
            tag_skip(f"SFN {sm['name']}: {e}")

# =============================================================================
# CONFIG — stop recorder, delete delivery channel, recorder, S3 bucket
# =============================================================================
if mode == "config":
    cfg = boto3.client("config", **creds)
    s3  = boto3.client("s3",     **creds)

    recorders = cfg.describe_configuration_recorders().get("ConfigurationRecorders", [])
    if not recorders:
        tag_skip("AWS Config: no recorders found")
    for r in recorders:
        rname = r["name"]
        # Stop
        try:
            cfg.stop_configuration_recorder(ConfigurationRecorderName=rname)
            tag_del(f"Config recorder stopped: {rname}")
        except Exception as e:
            tag_skip(f"Stop recorder {rname}: {e}")
        # Delete delivery channels (must go before recorder)
        try:
            channels = cfg.describe_delivery_channels().get("DeliveryChannels", [])
            if not channels:
                tag_skip("No Config delivery channels")
            for ch in channels:
                try:
                    cfg.delete_delivery_channel(DeliveryChannelName=ch["name"])
                    tag_del(f"Config delivery channel: {ch['name']}")
                except Exception as e:
                    tag_skip(f"Delivery channel {ch['name']}: {e}")
        except Exception as e:
            tag_skip(f"List delivery channels: {e}")
        # Delete recorder
        try:
            cfg.delete_configuration_recorder(ConfigurationRecorderName=rname)
            tag_del(f"Config recorder deleted: {rname}")
        except Exception as e:
            tag_skip(f"Delete recorder {rname}: {e}")

    # Delete Config S3 buckets
    try:
        buckets = [b["Name"] for b in s3.list_buckets().get("Buckets", [])
                   if "config-logs" in b["Name"] and "security-auto" in b["Name"]]
        if not buckets:
            tag_skip("No Config S3 buckets found")
        for bucket in buckets:
            try:
                pager = s3.get_paginator("list_object_versions")
                for page in pager.paginate(Bucket=bucket):
                    objs = [{"Key": o["Key"], "VersionId": o["VersionId"]}
                            for o in page.get("Versions", []) + page.get("DeleteMarkers", [])]
                    if objs:
                        s3.delete_objects(Bucket=bucket, Delete={"Objects": objs})
                resp = s3.list_objects_v2(Bucket=bucket)
                objs = [{"Key": o["Key"]} for o in resp.get("Contents", [])]
                if objs:
                    s3.delete_objects(Bucket=bucket, Delete={"Objects": objs})
                s3.delete_bucket(Bucket=bucket)
                tag_del(f"Config S3 bucket: {bucket}")
            except Exception as e:
                tag_skip(f"Config S3 {bucket}: {e}")
    except Exception as e:
        tag_skip(f"Config S3 scan: {e}")

# =============================================================================
# SECURITYHUB — disable all active standards subscriptions
# =============================================================================
if mode == "securityhub":
    sh = boto3.client("securityhub", **creds)
    try:
        subs = sh.get_enabled_standards().get("StandardsSubscriptions", [])
        active_arns = [s["StandardsSubscriptionArn"] for s in subs
                       if s.get("StandardsStatus") not in ("DELETING", "INCOMPLETE")]
        if not active_arns:
            tag_skip("Security Hub: no active standards subscriptions")
        else:
            sh.batch_disable_standards(StandardsSubscriptionArns=active_arns)
            tag_del(f"Disabled {len(active_arns)} Security Hub standard(s)")
    except Exception as e:
        tag_skip(f"Security Hub standards: {e}")

# =============================================================================
# SIM — simulation resources (not in Terraform state)
# =============================================================================
if mode == "sim":
    s3  = boto3.client("s3",  **creds)
    iam = boto3.client("iam", **creds)
    ec2 = boto3.client("ec2", **creds)

    # Sim S3 buckets (sim-pub-*)
    try:
        buckets = [b["Name"] for b in s3.list_buckets().get("Buckets", [])
                   if b["Name"].startswith("sim-pub-")]
        if not buckets:
            tag_skip("Sim S3 buckets: none")
        for bucket in buckets:
            try:
                pager = s3.get_paginator("list_object_versions")
                for page in pager.paginate(Bucket=bucket):
                    objs = [{"Key": o["Key"], "VersionId": o["VersionId"]}
                            for o in page.get("Versions", []) + page.get("DeleteMarkers", [])]
                    if objs:
                        s3.delete_objects(Bucket=bucket, Delete={"Objects": objs})
                resp = s3.list_objects_v2(Bucket=bucket)
                objs = [{"Key": o["Key"]} for o in resp.get("Contents", [])]
                if objs:
                    s3.delete_objects(Bucket=bucket, Delete={"Objects": objs})
                s3.delete_bucket(Bucket=bucket)
                tag_del(f"Sim S3 bucket: {bucket}")
            except Exception as e:
                tag_skip(f"Sim S3 {bucket}: {e}")
    except Exception as e:
        tag_skip(f"Sim S3 scan: {e}")

    # Sim IAM users (sim-b1-*, sim-*)
    try:
        users = [u["UserName"] for u in iam.list_users().get("Users", [])
                 if u["UserName"].startswith("sim-")]
        if not users:
            tag_skip("Sim IAM users: none")
        for uname in users:
            try:
                for k in iam.list_access_keys(UserName=uname).get("AccessKeyMetadata", []):
                    iam.delete_access_key(UserName=uname, AccessKeyId=k["AccessKeyId"])
                try: iam.delete_login_profile(UserName=uname)
                except: pass
                for p in iam.list_attached_user_policies(UserName=uname).get("AttachedPolicies", []):
                    iam.detach_user_policy(UserName=uname, PolicyArn=p["PolicyArn"])
                for g in iam.list_groups_for_user(UserName=uname).get("Groups", []):
                    iam.remove_user_from_group(UserName=uname, GroupName=g["GroupName"])
                for p in iam.list_user_policies(UserName=uname).get("PolicyNames", []):
                    iam.delete_user_policy(UserName=uname, PolicyName=p)
                iam.delete_user(UserName=uname)
                tag_del(f"Sim IAM user: {uname}")
            except Exception as e:
                tag_skip(f"Sim IAM user {uname}: {e}")
    except Exception as e:
        tag_skip(f"Sim IAM scan: {e}")

    # Sim security groups (sim-sg-*)
    try:
        sgs = ec2.describe_security_groups(
            Filters=[{"Name": "group-name", "Values": ["sim-sg-*"]}]
        ).get("SecurityGroups", [])
        if not sgs:
            tag_skip("Sim security groups: none")
        for sg in sgs:
            try:
                if sg.get("IpPermissions"):
                    ec2.revoke_security_group_ingress(
                        GroupId=sg["GroupId"], IpPermissions=sg["IpPermissions"])
                ec2.delete_security_group(GroupId=sg["GroupId"])
                tag_del(f"Sim security group: {sg['GroupId']} ({sg['GroupName']})")
            except Exception as e:
                tag_skip(f"Sim SG {sg['GroupId']}: {e}")
    except Exception as e:
        tag_skip(f"Sim SG scan: {e}")

# =============================================================================
# POST — post-Terraform cleanup (CloudWatch logs, EventBridge rules)
# =============================================================================
if mode == "post":
    logs = boto3.client("logs",   **creds)
    eb   = boto3.client("events", **creds)

    # CloudWatch log groups
    try:
        lgs = [g["logGroupName"] for g in logs.describe_log_groups().get("logGroups", [])
               if "security-auto" in g["logGroupName"]]
        if not lgs:
            tag_skip("CloudWatch log groups: none")
        for lg in lgs:
            try:
                logs.delete_log_group(logGroupName=lg)
                tag_del(f"CloudWatch log group: {lg}")
            except Exception as e:
                tag_skip(f"CW log {lg}: {e}")
    except Exception as e:
        tag_skip(f"CW log scan: {e}")

    # EventBridge rules (in case Terraform missed them)
    try:
        rules = [r for r in eb.list_rules().get("Rules", [])
                 if "securityhub" in r["Name"].lower() or "security-auto" in r["Name"].lower()]
        if not rules:
            tag_skip("EventBridge rules: none")
        for rule in rules:
            rname = rule["Name"]
            try:
                targets = eb.list_targets_by_rule(Rule=rname).get("Targets", [])
                if targets:
                    eb.remove_targets(Rule=rname, Ids=[t["Id"] for t in targets])
                eb.delete_rule(Name=rname)
                tag_del(f"EventBridge rule: {rname}")
            except Exception as e:
                tag_skip(f"EventBridge rule {rname}: {e}")
    except Exception as e:
        tag_skip(f"EventBridge scan: {e}")

# =============================================================================
# VERIFY — final check; exit 1 if anything remains
# =============================================================================
if mode == "verify":
    all_clean = True

    def check(label, check_fn):
        global all_clean
        try:
            if check_fn():
                tag_clean(label)
            else:
                print(f"  [REMAINING] {label}", flush=True)
                all_clean = False
        except Exception as e:
            print(f"  [ERROR]     {label}: {e}", flush=True)

    cfg  = boto3.client("config",        **creds)
    s3   = boto3.client("s3",            **creds)
    iam  = boto3.client("iam",           **creds)
    lam  = boto3.client("lambda",        **creds)
    db   = boto3.client("dynamodb",      **creds)
    sfn  = boto3.client("stepfunctions", **creds)
    sns  = boto3.client("sns",           **creds)
    logs = boto3.client("logs",          **creds)

    check("AWS Config recorder",
          lambda: len(cfg.describe_configuration_recorders()["ConfigurationRecorders"]) == 0)
    check("Sim S3 buckets",
          lambda: not any(b["Name"].startswith("sim-pub-") or
                          ("security-auto" in b["Name"] and "config" in b["Name"])
                          for b in s3.list_buckets()["Buckets"]))
    check("Sim IAM users",
          lambda: not any(u["UserName"].startswith("sim-")
                          for u in iam.list_users()["Users"]))
    check("Lambda functions",
          lambda: not any("security-auto" in f["FunctionName"]
                          for f in lam.list_functions()["Functions"]))
    check("DynamoDB tables",
          lambda: not any("security" in t for t in db.list_tables()["TableNames"]))
    check("Step Functions",
          lambda: not any("Security" in sm["name"] or "security" in sm["name"]
                          for sm in sfn.list_state_machines()["stateMachines"]))
    check("SNS topics",
          lambda: not any("security" in t["TopicArn"]
                          for t in sns.list_topics()["Topics"]))
    check("CloudWatch log groups",
          lambda: not any("security-auto" in g["logGroupName"]
                          for g in logs.describe_log_groups()["logGroups"]))

    sys.exit(0 if all_clean else 1)
'@

# ── Banner ────────────────────────────────────────────────────────────────────
Write-Header "AWS Security Automation — Quick Destroy"
Write-Host ""
Write-Host "  Cleans up:" -ForegroundColor White
Write-Host "    Step Functions executions" -ForegroundColor DarkGray
Write-Host "    AWS Config recorder, delivery channel, S3 bucket" -ForegroundColor DarkGray
Write-Host "    Security Hub standards subscriptions" -ForegroundColor DarkGray
Write-Host "    Simulation resources  (S3 buckets, IAM users, security groups)" -ForegroundColor DarkGray
Write-Host "    Terraform infrastructure  (Lambda, DynamoDB, API GW, SNS, SFN...)" -ForegroundColor DarkGray
Write-Host "    CloudWatch log groups, EventBridge rules" -ForegroundColor DarkGray

# ── Discovery ─────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Scanning account..." -ForegroundColor Cyan
py -3 $tmpPy discover
$discoverExit = $LASTEXITCODE

Write-Host ""
$confirm = Read-Host "Type 'yes' to delete all resources above"
if ($confirm -ne "yes") {
    Write-Host ""
    Write-Host "Aborted — nothing was deleted." -ForegroundColor Yellow
    Remove-Item $tmpPy -ErrorAction SilentlyContinue
    exit 0
}

# ── Step 1: Stop Step Functions executions ────────────────────────────────────
Write-Step 1 6 "Stopping Step Functions executions"
py -3 $tmpPy sfn

# ── Step 2: AWS Config ────────────────────────────────────────────────────────
Write-Step 2 6 "Removing AWS Config (recorder + delivery channel + S3)"
py -3 $tmpPy config

# ── Step 3: Security Hub standards ───────────────────────────────────────────
Write-Step 3 6 "Disabling Security Hub standards"
py -3 $tmpPy securityhub

# ── Step 4: Simulation resources ─────────────────────────────────────────────
Write-Step 4 6 "Deleting simulation resources (S3 buckets, IAM users, security groups)"
py -3 $tmpPy sim

# ── Step 5: Terraform destroy ─────────────────────────────────────────────────
Write-Step 5 6 "Running Terraform destroy"
$tfState = "$TF_DIR\terraform.tfstate"
if (Test-Path $tfState) {
    Push-Location $TF_DIR
    terraform destroy `
        -var="admin_email=$ADMIN_EMAIL" `
        -var="aws_region=$AWS_REGION" `
        -auto-approve 2>&1
    $tfExit = $LASTEXITCODE
    Pop-Location
    if ($tfExit -ne 0) {
        Write-Host "  [WARN]  Terraform destroy had errors — continuing with manual cleanup." -ForegroundColor Yellow
    } else {
        Write-Host "  [DELETED]   Terraform-managed infrastructure" -ForegroundColor Red
    }
} else {
    Write-Host "  [SKIPPED]   No terraform.tfstate — infrastructure was not deployed via Terraform" -ForegroundColor Gray
}

# ── Step 6: Post-Terraform cleanup ────────────────────────────────────────────
Write-Step 6 6 "Post-Terraform cleanup (CloudWatch logs, EventBridge rules)"
py -3 $tmpPy post

# ── Final verification ────────────────────────────────────────────────────────
Write-Host ""
Write-Host "========================================"  -ForegroundColor Cyan
Write-Host "  Final Verification" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
py -3 $tmpPy verify
$verifyExit = $LASTEXITCODE

# Cleanup temp file
Remove-Item $tmpPy -ErrorAction SilentlyContinue

# ── Result ────────────────────────────────────────────────────────────────────
Write-Host ""
if ($verifyExit -eq 0) {
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  DESTROY COMPLETE" -ForegroundColor Green
    Write-Host "  Account is clean. No ongoing charges." -ForegroundColor Green
    Write-Host "  Re-deploy:  .\scripts\quickdeploy.ps1" -ForegroundColor Gray
    Write-Host "========================================" -ForegroundColor Green
} else {
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host "  DESTROY COMPLETE (with warnings)" -ForegroundColor Yellow
    Write-Host "  Some [REMAINING] resources need" -ForegroundColor Yellow
    Write-Host "  manual review in the AWS console." -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Yellow
}
