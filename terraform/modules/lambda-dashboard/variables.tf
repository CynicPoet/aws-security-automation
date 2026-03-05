variable "project_name" {
  type    = string
  default = "security-auto"
}

variable "lambda_dashboard_role_arn" {
  description = "IAM role ARN for the dashboard Lambda"
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

variable "log_group_name" {
  description = "CloudWatch log group name"
  type        = string
}
