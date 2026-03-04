variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Short prefix used in all resource names"
  type        = string
  default     = "security-auto"
}
