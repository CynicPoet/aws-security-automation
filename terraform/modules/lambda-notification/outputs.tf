output "function_arn" {
  description = "ARN of the notification Lambda function"
  value       = aws_lambda_function.notification.arn
}
