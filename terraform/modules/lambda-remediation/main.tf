data "archive_file" "remediation" {
  type        = "zip"
  source_dir  = "${path.module}/src"
  output_path = "${path.module}/remediation.zip"
}

locals {
  common_env = {
    AWS_REGION     = var.aws_region
    LOG_GROUP_NAME = var.log_group_name
    LOG_LEVEL      = "INFO"
  }
}

# ── S3 REMEDIATION ────────────────────────────────────────────────────────────

resource "aws_lambda_function" "s3_remediation" {
  filename         = data.archive_file.remediation.output_path
  function_name    = "security-auto-s3-remediation"
  role             = var.lambda_remediation_role_arn
  handler          = "s3_remediation.lambda_handler"
  runtime          = "python3.11"
  timeout          = 60
  memory_size      = 128
  source_code_hash = data.archive_file.remediation.output_base64sha256

  environment {
    variables = local.common_env
  }

  tags = { Name = "security-auto-s3-remediation" }
}

resource "aws_cloudwatch_log_group" "s3_remediation" {
  name              = "/aws/lambda/security-auto-s3-remediation"
  retention_in_days = 30
}

# ── IAM REMEDIATION ───────────────────────────────────────────────────────────

resource "aws_lambda_function" "iam_remediation" {
  filename         = data.archive_file.remediation.output_path
  function_name    = "security-auto-iam-remediation"
  role             = var.lambda_remediation_role_arn
  handler          = "iam_remediation.lambda_handler"
  runtime          = "python3.11"
  timeout          = 60
  memory_size      = 128
  source_code_hash = data.archive_file.remediation.output_base64sha256

  environment {
    variables = local.common_env
  }

  tags = { Name = "security-auto-iam-remediation" }
}

resource "aws_cloudwatch_log_group" "iam_remediation" {
  name              = "/aws/lambda/security-auto-iam-remediation"
  retention_in_days = 30
}

# ── VPC REMEDIATION ───────────────────────────────────────────────────────────

resource "aws_lambda_function" "vpc_remediation" {
  filename         = data.archive_file.remediation.output_path
  function_name    = "security-auto-vpc-remediation"
  role             = var.lambda_remediation_role_arn
  handler          = "vpc_remediation.lambda_handler"
  runtime          = "python3.11"
  timeout          = 60
  memory_size      = 128
  source_code_hash = data.archive_file.remediation.output_base64sha256

  environment {
    variables = local.common_env
  }

  tags = { Name = "security-auto-vpc-remediation" }
}

resource "aws_cloudwatch_log_group" "vpc_remediation" {
  name              = "/aws/lambda/security-auto-vpc-remediation"
  retention_in_days = 30
}

# ── VERIFICATION ─────────────────────────────────────────────────────────────

resource "aws_lambda_function" "verification" {
  filename         = data.archive_file.remediation.output_path
  function_name    = "security-auto-verification"
  role             = var.lambda_verify_role_arn
  handler          = "verification.lambda_handler"
  runtime          = "python3.11"
  timeout          = 60
  memory_size      = 128
  source_code_hash = data.archive_file.remediation.output_base64sha256

  environment {
    variables = local.common_env
  }

  tags = { Name = "security-auto-verification" }
}

resource "aws_cloudwatch_log_group" "verification" {
  name              = "/aws/lambda/security-auto-verification"
  retention_in_days = 30
}
