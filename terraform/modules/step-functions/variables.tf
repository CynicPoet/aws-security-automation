variable "project_name" {
  description = "Short prefix used in all resource names"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "step_functions_role_arn" {
  description = "IAM role ARN for the Step Functions state machine"
  type        = string
}

variable "ai_analyzer_function_arn" {
  description = "ARN of the AI analyzer Lambda function"
  type        = string
}

variable "s3_remediation_function_arn" {
  description = "ARN of the S3 remediation Lambda function"
  type        = string
}

variable "iam_remediation_function_arn" {
  description = "ARN of the IAM remediation Lambda function"
  type        = string
}

variable "vpc_remediation_function_arn" {
  description = "ARN of the VPC remediation Lambda function"
  type        = string
}

variable "verification_function_arn" {
  description = "ARN of the verification Lambda function"
  type        = string
}

variable "notification_function_arn" {
  description = "ARN of the notification Lambda function"
  type        = string
}

variable "log_group_name" {
  description = "CloudWatch log group name for execution logging"
  type        = string
}
