output "function_arn" {
  description = "ARN of the dashboard Lambda"
  value       = aws_lambda_function.dashboard.arn
}

output "function_name" {
  description = "Name of the dashboard Lambda"
  value       = aws_lambda_function.dashboard.function_name
}
