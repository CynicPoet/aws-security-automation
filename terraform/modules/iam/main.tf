data "aws_caller_identity" "current" {}

# ─────────────────────────────────────────────
# SHARED ASSUME-ROLE POLICY DOCUMENTS
# ─────────────────────────────────────────────

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "step_functions_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "eventbridge_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }
  }
}

# ─────────────────────────────────────────────
# LAMBDA — REMEDIATION ROLE
# ─────────────────────────────────────────────

resource "aws_iam_role" "lambda_remediation" {
  name               = "SecurityAutomation-LambdaRemediationRole"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json

  tags = { Name = "SecurityAutomation-LambdaRemediationRole" }
}

data "aws_iam_policy_document" "lambda_remediation_policy" {
  statement {
    sid    = "S3Remediation"
    effect = "Allow"
    actions = [
      "s3:PutBucketPublicAccessBlock",
      "s3:PutBucketAcl",
      "s3:GetBucketPublicAccessBlock",
      "s3:GetBucketAcl",
      "s3:GetBucketTagging",
      "s3:GetBucketWebsite",
      "s3:GetBucketPolicy",
      "s3:ListAllMyBuckets",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "IAMRemediation"
    effect = "Allow"
    actions = [
      "iam:UpdateAccessKey",
      "iam:ListAccessKeys",
      "iam:PutUserPolicy",
      "iam:GetUserPolicy",
      "iam:ListUserPolicies",
      "iam:ListAttachedUserPolicies",
      "iam:GetUser",
      "iam:ListUserTags",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "VPCRemediation"
    effect = "Allow"
    actions = [
      "ec2:RevokeSecurityGroupIngress",
      "ec2:DescribeSecurityGroups",
      "ec2:DescribeNetworkInterfaces",
      "ec2:DescribeInstances",
      "ec2:DescribeTags",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "SecurityHubUpdate"
    effect = "Allow"
    actions = [
      "securityhub:BatchUpdateFindings",
      "securityhub:GetFindings",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "DynamoDBWrite"
    effect = "Allow"
    actions = [
      "dynamodb:PutItem",
    ]
    resources = ["arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/security-automation-*"]
  }

  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/security-automation:*"]
  }
}

resource "aws_iam_role_policy" "lambda_remediation" {
  name   = "SecurityAutomation-LambdaRemediationPolicy"
  role   = aws_iam_role.lambda_remediation.id
  policy = data.aws_iam_policy_document.lambda_remediation_policy.json
}

# ─────────────────────────────────────────────
# LAMBDA — VERIFICATION ROLE
# ─────────────────────────────────────────────

resource "aws_iam_role" "lambda_verification" {
  name               = "SecurityAutomation-LambdaVerificationRole"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json

  tags = { Name = "SecurityAutomation-LambdaVerificationRole" }
}

data "aws_iam_policy_document" "lambda_verification_policy" {
  statement {
    sid    = "ReadChecks"
    effect = "Allow"
    actions = [
      "s3:GetBucketPublicAccessBlock",
      "s3:GetBucketAcl",
      "iam:ListAccessKeys",
      "iam:GetUserPolicy",
      "ec2:DescribeSecurityGroups",
      "securityhub:BatchUpdateFindings",
      "securityhub:GetFindings",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "DynamoDBStatusUpdate"
    effect = "Allow"
    actions = [
      "dynamodb:UpdateItem",
    ]
    resources = ["arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/security-automation-*"]
  }

  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/security-automation:*"]
  }
}

resource "aws_iam_role_policy" "lambda_verification" {
  name   = "SecurityAutomation-LambdaVerificationPolicy"
  role   = aws_iam_role.lambda_verification.id
  policy = data.aws_iam_policy_document.lambda_verification_policy.json
}

# ─────────────────────────────────────────────
# LAMBDA — AI ANALYZER ROLE
# ─────────────────────────────────────────────

resource "aws_iam_role" "lambda_ai_analyzer" {
  name               = "SecurityAutomation-LambdaAIAnalyzerRole"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json

  tags = { Name = "SecurityAutomation-LambdaAIAnalyzerRole" }
}

data "aws_iam_policy_document" "lambda_ai_analyzer_policy" {
  statement {
    sid    = "ReadResourceContext"
    effect = "Allow"
    actions = [
      "s3:GetBucketTagging",
      "s3:GetBucketWebsite",
      "s3:GetBucketPolicy",
      "s3:GetBucketPublicAccessBlock",
      "iam:GetUser",
      "iam:ListUserTags",
      "iam:ListAccessKeys",
      "iam:GetAccessKeyLastUsed",
      "iam:ListAttachedUserPolicies",
      "iam:ListUserPolicies",
      "ec2:DescribeSecurityGroups",
      "ec2:DescribeNetworkInterfaces",
      "ec2:DescribeInstances",
    ]
    resources = ["*"]
  }

  statement {
    sid       = "SecretsManager"
    effect    = "Allow"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = ["arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:security-automation/ai-api-key*"]
  }

  statement {
    sid       = "ReadSettings"
    effect    = "Allow"
    actions   = ["dynamodb:GetItem"]
    resources = ["arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/security-automation-settings"]
  }

  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/security-automation:*"]
  }
}

resource "aws_iam_role_policy" "lambda_ai_analyzer" {
  name   = "SecurityAutomation-LambdaAIAnalyzerPolicy"
  role   = aws_iam_role.lambda_ai_analyzer.id
  policy = data.aws_iam_policy_document.lambda_ai_analyzer_policy.json
}

# ─────────────────────────────────────────────
# LAMBDA — NOTIFICATION ROLE
# ─────────────────────────────────────────────

resource "aws_iam_role" "lambda_notification" {
  name               = "SecurityAutomation-LambdaNotificationRole"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json

  tags = { Name = "SecurityAutomation-LambdaNotificationRole" }
}

data "aws_iam_policy_document" "lambda_notification_policy" {
  statement {
    sid       = "SNSPublish"
    effect    = "Allow"
    actions   = ["sns:Publish"]
    resources = ["arn:aws:sns:${var.aws_region}:${data.aws_caller_identity.current.account_id}:security-automation-admin-alerts"]
  }

  statement {
    sid    = "DynamoDBWrite"
    effect = "Allow"
    actions = [
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:GetItem",
    ]
    resources = ["arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/security-automation-*"]
  }

  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/security-automation:*"]
  }
}

resource "aws_iam_role_policy" "lambda_notification" {
  name   = "SecurityAutomation-LambdaNotificationPolicy"
  role   = aws_iam_role.lambda_notification.id
  policy = data.aws_iam_policy_document.lambda_notification_policy.json
}

# ─────────────────────────────────────────────
# LAMBDA — DASHBOARD ROLE
# ─────────────────────────────────────────────

resource "aws_iam_role" "lambda_dashboard" {
  name               = "SecurityAutomation-LambdaDashboardRole"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json

  tags = { Name = "SecurityAutomation-LambdaDashboardRole" }
}

data "aws_iam_policy_document" "lambda_dashboard_policy" {
  statement {
    sid    = "DynamoDBReadWrite"
    effect = "Allow"
    actions = [
      "dynamodb:Scan", "dynamodb:GetItem", "dynamodb:PutItem",
      "dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:DeleteItem",
    ]
    resources = ["arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/security-automation-*"]
  }

  statement {
    sid    = "StepFunctions"
    effect = "Allow"
    actions = [
      "states:SendTaskSuccess", "states:SendTaskFailure", "states:StartExecution",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "EventBridgeControl"
    effect = "Allow"
    actions = [
      "events:EnableRule", "events:DisableRule", "events:DescribeRule",
    ]
    resources = ["arn:aws:events:${var.aws_region}:${data.aws_caller_identity.current.account_id}:rule/securityhub-finding-rule"]
  }

  statement {
    sid       = "SNSPublish"
    effect    = "Allow"
    actions   = ["sns:Publish"]
    resources = ["arn:aws:sns:${var.aws_region}:${data.aws_caller_identity.current.account_id}:security-automation-admin-alerts"]
  }

  statement {
    sid    = "SimulationEC2"
    effect = "Allow"
    actions = [
      "ec2:CreateSecurityGroup", "ec2:DeleteSecurityGroup",
      "ec2:AuthorizeSecurityGroupIngress", "ec2:RevokeSecurityGroupIngress",
      "ec2:DescribeVpcs", "ec2:DescribeSecurityGroups", "ec2:CreateTags",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "SimulationS3"
    effect = "Allow"
    actions = [
      "s3:CreateBucket", "s3:DeleteBucket",
      "s3:PutPublicAccessBlock", "s3:GetPublicAccessBlock",
      "s3:PutBucketOwnershipControls", "s3:GetBucketOwnershipControls",
      "s3:ListBucket", "s3:DeleteObject", "s3:DeleteObjectVersion",
      "s3:ListBucketVersions", "s3:PutBucketAcl", "s3:GetBucketAcl",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "SimulationIAM"
    effect = "Allow"
    actions = [
      "iam:CreateUser", "iam:DeleteUser", "iam:TagUser",
      "iam:CreateAccessKey", "iam:DeleteAccessKey", "iam:ListAccessKeys",
      "iam:PutUserPolicy", "iam:DeleteUserPolicy", "iam:ListUserPolicies",
      "iam:AttachUserPolicy", "iam:DetachUserPolicy", "iam:ListAttachedUserPolicies",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents",
    ]
    resources = ["arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/security-auto-dashboard:*"]
  }

  statement {
    sid    = "TerminateInfrastructure"
    effect = "Allow"
    actions = [
      "lambda:InvokeFunction", "lambda:DeleteFunction", "lambda:ListFunctions",
      "states:StopExecution", "states:ListExecutions",
      "dynamodb:DeleteTable", "dynamodb:BatchWriteItem",
      "sns:DeleteTopic", "sns:Unsubscribe", "sns:ListSubscriptionsByTopic",
      "events:RemoveTargets", "events:DeleteRule", "events:ListTargetsByRule",
      "logs:DescribeLogGroups", "logs:DeleteLogGroup", "logs:DeleteLogStream",
      "secretsmanager:DeleteSecret",
      "apigateway:GET", "apigateway:DELETE",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "lambda_dashboard" {
  name   = "SecurityAutomation-LambdaDashboardPolicy"
  role   = aws_iam_role.lambda_dashboard.id
  policy = data.aws_iam_policy_document.lambda_dashboard_policy.json
}

# ─────────────────────────────────────────────
# LAMBDA — APPROVAL ROLE
# ─────────────────────────────────────────────

resource "aws_iam_role" "lambda_approval" {
  name               = "SecurityAutomation-LambdaApprovalRole"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json

  tags = { Name = "SecurityAutomation-LambdaApprovalRole" }
}

data "aws_iam_policy_document" "lambda_approval_policy" {
  statement {
    sid    = "StepFunctionsCallback"
    effect = "Allow"
    actions = [
      "states:SendTaskSuccess",
      "states:SendTaskFailure",
      "states:SendTaskHeartbeat",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/security-automation:*"]
  }
}

resource "aws_iam_role_policy" "lambda_approval" {
  name   = "SecurityAutomation-LambdaApprovalPolicy"
  role   = aws_iam_role.lambda_approval.id
  policy = data.aws_iam_policy_document.lambda_approval_policy.json
}

# ─────────────────────────────────────────────
# STEP FUNCTIONS ROLE
# ─────────────────────────────────────────────

resource "aws_iam_role" "step_functions" {
  name               = "SecurityAutomation-StepFunctionsRole"
  assume_role_policy = data.aws_iam_policy_document.step_functions_assume.json

  tags = { Name = "SecurityAutomation-StepFunctionsRole" }
}

data "aws_iam_policy_document" "step_functions_policy" {
  statement {
    sid       = "InvokeLambdas"
    effect    = "Allow"
    actions   = ["lambda:InvokeFunction"]
    resources = ["arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:security-auto-*"]
  }

  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogDelivery",
      "logs:GetLogDelivery",
      "logs:UpdateLogDelivery",
      "logs:DeleteLogDelivery",
      "logs:ListLogDeliveries",
      "logs:PutResourcePolicy",
      "logs:DescribeResourcePolicies",
      "logs:DescribeLogGroups",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "step_functions" {
  name   = "SecurityAutomation-StepFunctionsPolicy"
  role   = aws_iam_role.step_functions.id
  policy = data.aws_iam_policy_document.step_functions_policy.json
}

# ─────────────────────────────────────────────
# EVENTBRIDGE ROLE
# ─────────────────────────────────────────────

resource "aws_iam_role" "eventbridge" {
  name               = "SecurityAutomation-EventBridgeRole"
  assume_role_policy = data.aws_iam_policy_document.eventbridge_assume.json

  tags = { Name = "SecurityAutomation-EventBridgeRole" }
}

data "aws_iam_policy_document" "eventbridge_policy" {
  statement {
    sid       = "StartStateMachine"
    effect    = "Allow"
    actions   = ["states:StartExecution"]
    resources = ["arn:aws:states:${var.aws_region}:${data.aws_caller_identity.current.account_id}:stateMachine:SecurityRemediationStateMachine"]
  }
}

resource "aws_iam_role_policy" "eventbridge" {
  name   = "SecurityAutomation-EventBridgePolicy"
  role   = aws_iam_role.eventbridge.id
  policy = data.aws_iam_policy_document.eventbridge_policy.json
}
