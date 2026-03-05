variable "project_name" {
  description = "Short prefix used in all resource names"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "lambda_notify_role_arn" {
  description = "IAM role ARN for the notification Lambda function"
  type        = string
}

variable "log_group_name" {
  description = "CloudWatch log group name to send structured logs to"
  type        = string
}

variable "sns_topic_arn" {
  description = "ARN of the SNS topic for admin alerts"
  type        = string
}

variable "api_gateway_base_url" {
  description = "Base URL of the API Gateway approval endpoint"
  type        = string
}

variable "findings_table_name" {
  description = "DynamoDB findings table name"
  type        = string
}

variable "settings_table_name" {
  description = "DynamoDB settings table name"
  type        = string
}
