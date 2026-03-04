output "log_group_name" {
  description = "CloudWatch log group name for security automation events"
  value       = aws_cloudwatch_log_group.security_automation.name
}

output "dashboard_name" {
  description = "CloudWatch dashboard name"
  value       = aws_cloudwatch_dashboard.live_monitor.dashboard_name
}
