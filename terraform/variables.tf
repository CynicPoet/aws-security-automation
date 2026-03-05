variable "aws_region" {
  description = "AWS region to deploy all resources"
  type        = string
  default     = "us-east-1"

  validation {
    condition     = can(regex("^[a-z]{2}-[a-z]+-[0-9]$", var.aws_region))
    error_message = "Must be a valid AWS region (e.g. us-east-1)."
  }
}

variable "project_name" {
  description = "Short prefix used in all resource names"
  type        = string
  default     = "security-auto"
}

variable "admin_email" {
  description = "Email address to receive admin security alerts"
  type        = string

  validation {
    condition     = can(regex("^[^@]+@[^@]+\\.[^@]+$", var.admin_email))
    error_message = "Must be a valid email address."
  }
}

variable "ai_provider" {
  description = "AI provider to use for analysis (gemini or claude)"
  type        = string
  default     = "gemini"

  validation {
    condition     = contains(["gemini", "claude"], var.ai_provider)
    error_message = "Must be either 'gemini' or 'claude'."
  }
}

variable "ai_model" {
  description = "AI model name to use"
  type        = string
  default     = "gemini-2.5-flash"
}

variable "budget_limit_usd" {
  description = "Monthly budget alert threshold in USD"
  type        = number
  default     = 5
}
