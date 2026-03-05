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

variable "state_machine_arn" {
  description = "Step Functions state machine ARN (for simulation)"
  type        = string
  default     = ""
}

variable "eventbridge_rule_name" {
  description = "EventBridge rule name (for pipeline shutdown/start)"
  type        = string
  default     = "securityhub-finding-rule"
}

variable "sns_topic_arn" {
  description = "SNS topic ARN (for email resend)"
  type        = string
  default     = ""
}

variable "account_id" {
  description = "AWS account ID (for simulation resource ARNs)"
  type        = string
  default     = ""
}
