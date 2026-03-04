variable "project_name" {
  description = "Short prefix used in all resource names"
  type        = string
}

variable "admin_email" {
  description = "Email address to receive budget alerts"
  type        = string
}

variable "budget_limit_usd" {
  description = "Monthly budget alert threshold in USD"
  type        = number
}
