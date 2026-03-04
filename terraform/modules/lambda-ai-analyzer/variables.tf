variable "project_name" {
  description = "Short prefix used in all resource names"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "lambda_ai_role_arn" {
  description = "IAM role ARN for the AI analyzer Lambda function"
  type        = string
}

variable "log_group_name" {
  description = "CloudWatch log group name to send structured logs to"
  type        = string
}

variable "ai_provider" {
  description = "AI provider to use (gemini or claude)"
  type        = string
}

variable "ai_model" {
  description = "AI model name to use"
  type        = string
}
