data "aws_caller_identity" "current" {}

resource "aws_cloudwatch_log_group" "state_machine" {
  name              = "/aws/states/SecurityRemediationStateMachine"
  retention_in_days = 30
}

resource "aws_sfn_state_machine" "security_remediation" {
  name     = "SecurityRemediationStateMachine"
  role_arn = var.step_functions_role_arn
  type     = "STANDARD"

  definition = templatefile("${path.module}/state-machine.asl.json", {
    ai_analyzer_function_arn     = var.ai_analyzer_function_arn
    s3_remediation_function_arn  = var.s3_remediation_function_arn
    iam_remediation_function_arn = var.iam_remediation_function_arn
    vpc_remediation_function_arn = var.vpc_remediation_function_arn
    verification_function_arn    = var.verification_function_arn
    notification_function_arn    = var.notification_function_arn
  })

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.state_machine.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  tags = { Name = "SecurityRemediationStateMachine" }
}
