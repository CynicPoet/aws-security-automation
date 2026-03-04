output "state_machine_arn" {
  description = "ARN of the Step Functions state machine"
  value       = module.step_functions.state_machine_arn
}

output "api_gateway_base_url" {
  description = "Base URL for the approval API Gateway"
  value       = module.api_gateway.base_url
}

output "cloudwatch_dashboard_url" {
  description = "Direct URL to the CloudWatch live monitoring dashboard"
  value       = "https://${var.aws_region}.console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=SecurityAutomation-LiveMonitor"
}

output "sns_topic_arn" {
  description = "ARN of the admin alerts SNS topic"
  value       = module.sns.admin_alerts_topic_arn
}

output "log_group_name" {
  description = "CloudWatch log group name for all security automation events"
  value       = module.cloudwatch.log_group_name
}
