output "lambda_remediation_role_arn" {
  description = "ARN of the Lambda remediation IAM role"
  value       = aws_iam_role.lambda_remediation.arn
}

output "lambda_ai_analyzer_role_arn" {
  description = "ARN of the Lambda AI analyzer IAM role"
  value       = aws_iam_role.lambda_ai_analyzer.arn
}

output "lambda_notification_role_arn" {
  description = "ARN of the Lambda notification IAM role"
  value       = aws_iam_role.lambda_notification.arn
}

output "lambda_approval_role_arn" {
  description = "ARN of the Lambda approval IAM role"
  value       = aws_iam_role.lambda_approval.arn
}

output "lambda_verification_role_arn" {
  description = "ARN of the Lambda verification IAM role"
  value       = aws_iam_role.lambda_verification.arn
}

output "step_functions_role_arn" {
  description = "ARN of the Step Functions IAM role"
  value       = aws_iam_role.step_functions.arn
}

output "eventbridge_role_arn" {
  description = "ARN of the EventBridge IAM role"
  value       = aws_iam_role.eventbridge.arn
}

output "lambda_dashboard_role_arn" {
  description = "ARN of the Lambda dashboard IAM role"
  value       = aws_iam_role.lambda_dashboard.arn
}
