data "aws_caller_identity" "current" {}

# ── SECRETS MANAGER — AI API KEY ──────────────────────────────────────────────
# Value must be updated after first deploy:
# aws secretsmanager put-secret-value --secret-id security-automation/ai-api-key \
#   --secret-string '{"api_key":"YOUR_GEMINI_API_KEY","provider":"gemini"}'

resource "aws_secretsmanager_secret" "ai_api_key" {
  name                    = "security-automation/ai-api-key"
  description             = "AI provider API key for security-auto-ai-analyzer Lambda"
  recovery_window_in_days = 0

  tags = { Name = "security-automation/ai-api-key" }
}

resource "aws_secretsmanager_secret_version" "ai_api_key_placeholder" {
  secret_id = aws_secretsmanager_secret.ai_api_key.id
  secret_string = jsonencode({
    api_key  = "REPLACE_WITH_YOUR_GEMINI_API_KEY"
    provider = var.ai_provider
  })

  lifecycle {
    ignore_changes = [secret_string]
  }
}

# ── LAMBDA ZIP ────────────────────────────────────────────────────────────────

data "archive_file" "ai_analyzer" {
  type        = "zip"
  source_dir  = "${path.module}/src"
  output_path = "${path.module}/ai_analyzer.zip"
}

# ── LAMBDA FUNCTION ───────────────────────────────────────────────────────────

resource "aws_lambda_function" "ai_analyzer" {
  filename         = data.archive_file.ai_analyzer.output_path
  function_name    = "security-auto-ai-analyzer"
  role             = var.lambda_ai_role_arn
  handler          = "ai_analyzer.lambda_handler"
  runtime          = "python3.11"
  timeout          = 60
  memory_size      = 256
  source_code_hash = data.archive_file.ai_analyzer.output_base64sha256

  environment {
    variables = {
      AI_PROVIDER    = var.ai_provider
      AI_MODEL       = var.ai_model
      SECRET_NAME    = aws_secretsmanager_secret.ai_api_key.name
      LOG_GROUP_NAME = var.log_group_name
      SETTINGS_TABLE = var.settings_table_name
    }
  }

  tags = { Name = "security-auto-ai-analyzer" }

  depends_on = [aws_secretsmanager_secret_version.ai_api_key_placeholder]
}

resource "aws_cloudwatch_log_group" "ai_analyzer" {
  name              = "/aws/lambda/security-auto-ai-analyzer"
  retention_in_days = 30
}
