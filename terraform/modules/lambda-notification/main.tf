data "archive_file" "notification" {
  type        = "zip"
  source_dir  = "${path.module}/src"
  output_path = "${path.module}/notification.zip"
}

resource "aws_lambda_function" "notification" {
  filename         = data.archive_file.notification.output_path
  function_name    = "security-auto-notification"
  role             = var.lambda_notify_role_arn
  handler          = "send_notification.lambda_handler"
  runtime          = "python3.11"
  timeout          = 30
  memory_size      = 128
  source_code_hash = data.archive_file.notification.output_base64sha256

  environment {
    variables = {
      SNS_TOPIC_ARN        = var.sns_topic_arn
      API_GATEWAY_BASE_URL = var.api_gateway_base_url
      FINDINGS_TABLE       = var.findings_table_name
      SETTINGS_TABLE       = var.settings_table_name
      LOG_GROUP_NAME       = var.log_group_name
    }
  }

  tags = { Name = "security-auto-notification" }
}

resource "aws_cloudwatch_log_group" "notification" {
  name              = "/aws/lambda/security-auto-notification"
  retention_in_days = 30
}
