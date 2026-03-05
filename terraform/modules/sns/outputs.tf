output "admin_alerts_topic_arn" {
  description = "ARN of the SNS admin alerts topic"
  value       = aws_sns_topic.admin_alerts.arn
}
