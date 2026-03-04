variable "project_name" {
  description = "Short prefix used in all resource names"
  type        = string
}

variable "eventbridge_role_arn" {
  description = "IAM role ARN for EventBridge to invoke Step Functions"
  type        = string
}

variable "state_machine_arn" {
  description = "ARN of the Step Functions state machine to trigger"
  type        = string
}
