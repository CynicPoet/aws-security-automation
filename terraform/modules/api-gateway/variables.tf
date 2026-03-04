variable "project_name" {
  description = "Short prefix used in all resource names"
  type        = string
}

variable "lambda_approval_function_arn" {
  description = "ARN of the approval handler Lambda function"
  type        = string
}

variable "lambda_approval_function_name" {
  description = "Name of the approval handler Lambda function"
  type        = string
}
