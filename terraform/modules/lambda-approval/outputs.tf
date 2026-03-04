output "function_arn" {
  description = "ARN of the approval handler Lambda function"
  value       = aws_lambda_function.approval.arn
}

output "function_name" {
  description = "Name of the approval handler Lambda function"
  value       = aws_lambda_function.approval.function_name
}
