resource "aws_sns_topic" "admin_alerts" {
  name = "security-automation-admin-alerts"

  tags = { Name = "security-automation-admin-alerts" }
}

resource "aws_sns_topic_subscription" "admin_email" {
  topic_arn = aws_sns_topic.admin_alerts.arn
  protocol  = "email"
  endpoint  = var.admin_email
}
