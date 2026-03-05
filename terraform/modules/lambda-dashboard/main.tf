data "archive_file" "dashboard" {
  type        = "zip"
  source_dir  = "${path.module}/src"
  output_path = "${path.module}/dashboard.zip"
}

resource "aws_lambda_function" "dashboard" {
  filename         = data.archive_file.dashboard.output_path
  function_name    = "security-auto-dashboard"
  role             = var.lambda_dashboard_role_arn
  handler          = "dashboard_handler.lambda_handler"
  runtime          = "python3.11"
  timeout          = 30
  memory_size      = 256
  source_code_hash = data.archive_file.dashboard.output_base64sha256

  environment {
    variables = {
      FINDINGS_TABLE    = var.findings_table_name
      SETTINGS_TABLE    = var.settings_table_name
      LOG_GROUP_NAME    = var.log_group_name
      STATE_MACHINE_ARN = var.state_machine_arn
      EB_RULE_NAME      = var.eventbridge_rule_name
      SNS_TOPIC_ARN     = var.sns_topic_arn
      ACCOUNT_ID        = var.account_id
    }
  }

  tags = { Name = "security-auto-dashboard" }
}

resource "aws_cloudwatch_log_group" "dashboard" {
  name              = "/aws/lambda/security-auto-dashboard"
  retention_in_days = 30
}
