variable "project_name" {
  description = "Short prefix used in all resource names"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "lambda_remediation_role_arn" {
  description = "IAM role ARN for the remediation Lambda functions"
  type        = string
}

variable "lambda_verify_role_arn" {
  description = "IAM role ARN for the verification Lambda function"
  type        = string
}

variable "log_group_name" {
  description = "CloudWatch log group name to send structured logs to"
  type        = string
}
