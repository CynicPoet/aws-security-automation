resource "aws_cloudwatch_event_rule" "security_hub_findings" {
  name        = "securityhub-finding-rule"
  description = "Capture Security Hub FAILED findings and route to Step Functions"
  state       = "DISABLED" # Disabled by default — enable via Dashboard 'Start Pipeline' for real monitoring

  event_pattern = jsonencode({
    source      = ["aws.securityhub"]
    detail-type = ["Security Hub Findings - Imported"]
    detail = {
      findings = {
        Compliance  = { Status = ["FAILED"] }
        Workflow    = { Status = ["NEW"] }
        Severity    = { Label = ["MEDIUM", "HIGH", "CRITICAL"] }
        RecordState = ["ACTIVE"]
      }
    }
  })

  tags = { Name = "securityhub-finding-rule" }
}

resource "aws_cloudwatch_event_target" "step_functions" {
  rule     = aws_cloudwatch_event_rule.security_hub_findings.name
  arn      = var.state_machine_arn
  role_arn = var.eventbridge_role_arn
}
