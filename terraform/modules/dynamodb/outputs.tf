output "findings_table_name" {
  description = "DynamoDB table for security findings"
  value       = aws_dynamodb_table.findings.name
}

output "findings_table_arn" {
  description = "ARN of the findings DynamoDB table"
  value       = aws_dynamodb_table.findings.arn
}

output "settings_table_name" {
  description = "DynamoDB table for dashboard settings"
  value       = aws_dynamodb_table.settings.name
}

output "settings_table_arn" {
  description = "ARN of the settings DynamoDB table"
  value       = aws_dynamodb_table.settings.arn
}
