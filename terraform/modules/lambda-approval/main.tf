data "archive_file" "approval" {
  type        = "zip"
  source_dir  = "${path.module}/src"
  output_path = "${path.module}/approval.zip"
}

resource "aws_lambda_function" "approval" {
  filename         = data.archive_file.approval.output_path
  function_name    = "security-auto-approval-handler"
  role             = var.lambda_approval_role_arn
  handler          = "approval_handler.lambda_handler"
  runtime          = "python3.11"
  timeout          = 10
  memory_size      = 128
  source_code_hash = data.archive_file.approval.output_base64sha256

  environment {
    variables = {
      AWS_REGION     = var.aws_region
      LOG_GROUP_NAME = var.log_group_name
    }
  }

  tags = { Name = "security-auto-approval-handler" }
}

resource "aws_cloudwatch_log_group" "approval" {
  name              = "/aws/lambda/security-auto-approval-handler"
  retention_in_days = 30
}
