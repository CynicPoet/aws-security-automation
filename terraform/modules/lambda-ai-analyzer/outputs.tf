output "function_arn" {
  description = "ARN of the AI analyzer Lambda function"
  value       = aws_lambda_function.ai_analyzer.arn
}
