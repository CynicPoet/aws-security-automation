# ─────────────────────────────────────────────
# CLOUDWATCH LOG GROUP
# ─────────────────────────────────────────────

resource "aws_cloudwatch_log_group" "security_automation" {
  name              = "/aws/security-automation"
  retention_in_days = 90

  tags = {
    Name = "/aws/security-automation"
  }
}

# ─────────────────────────────────────────────
# CLOUDWATCH DASHBOARD — Live Monitor
# ─────────────────────────────────────────────

resource "aws_cloudwatch_dashboard" "live_monitor" {
  dashboard_name = "SecurityAutomation-LiveMonitor"

  dashboard_body = jsonencode({
    widgets = [
      # ── Row 1: Execution counts ──────────────────
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 8
        height = 6
        properties = {
          title  = "Step Functions — Executions"
          view   = "timeSeries"
          region = "us-east-1"
          metrics = [
            ["AWS/States", "ExecutionsStarted", "StateMachineArn", "arn:aws:states:us-east-1:*:stateMachine:SecurityRemediationStateMachine"],
            ["AWS/States", "ExecutionsSucceeded", "StateMachineArn", "arn:aws:states:us-east-1:*:stateMachine:SecurityRemediationStateMachine"],
            ["AWS/States", "ExecutionsFailed", "StateMachineArn", "arn:aws:states:us-east-1:*:stateMachine:SecurityRemediationStateMachine"],
          ]
          period = 300
          stat   = "Sum"
        }
      },
      # ── Row 1: Lambda errors ─────────────────────
      {
        type   = "metric"
        x      = 8
        y      = 0
        width  = 8
        height = 6
        properties = {
          title  = "Lambda — Errors"
          view   = "timeSeries"
          region = "us-east-1"
          metrics = [
            ["AWS/Lambda", "Errors", "FunctionName", "security-auto-s3-remediation"],
            ["AWS/Lambda", "Errors", "FunctionName", "security-auto-iam-remediation"],
            ["AWS/Lambda", "Errors", "FunctionName", "security-auto-vpc-remediation"],
            ["AWS/Lambda", "Errors", "FunctionName", "security-auto-ai-analyzer"],
            ["AWS/Lambda", "Errors", "FunctionName", "security-auto-notification"],
            ["AWS/Lambda", "Errors", "FunctionName", "security-auto-approval-handler"],
            ["AWS/Lambda", "Errors", "FunctionName", "security-auto-verification"],
          ]
          period = 300
          stat   = "Sum"
        }
      },
      # ── Row 1: Lambda duration ───────────────────
      {
        type   = "metric"
        x      = 16
        y      = 0
        width  = 8
        height = 6
        properties = {
          title  = "Lambda — Duration (p99)"
          view   = "timeSeries"
          region = "us-east-1"
          metrics = [
            ["AWS/Lambda", "Duration", "FunctionName", "security-auto-s3-remediation"],
            ["AWS/Lambda", "Duration", "FunctionName", "security-auto-iam-remediation"],
            ["AWS/Lambda", "Duration", "FunctionName", "security-auto-vpc-remediation"],
            ["AWS/Lambda", "Duration", "FunctionName", "security-auto-ai-analyzer"],
          ]
          period = 300
          stat   = "p99"
        }
      },
      # ── Row 2: Security Hub findings ─────────────
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          title  = "Security Hub — Findings by Severity"
          view   = "timeSeries"
          region = "us-east-1"
          metrics = [
            ["AWS/SecurityHub", "Findings", "SeverityLabel", "CRITICAL"],
            ["AWS/SecurityHub", "Findings", "SeverityLabel", "HIGH"],
            ["AWS/SecurityHub", "Findings", "SeverityLabel", "MEDIUM"],
          ]
          period = 3600
          stat   = "Sum"
        }
      },
      # ── Row 2: Step Functions execution time ─────
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        properties = {
          title  = "Step Functions — Execution Time (ms)"
          view   = "timeSeries"
          region = "us-east-1"
          metrics = [
            ["AWS/States", "ExecutionTime", "StateMachineArn", "arn:aws:states:us-east-1:*:stateMachine:SecurityRemediationStateMachine"],
          ]
          period = 300
          stat   = "Average"
        }
      },
      # ── Row 3: Log insights — recent events ──────
      {
        type   = "log"
        x      = 0
        y      = 12
        width  = 24
        height = 6
        properties = {
          title   = "Security Automation — Recent Events"
          region  = "us-east-1"
          view    = "table"
          query   = "SOURCE '/aws/security-automation' | fields @timestamp, level, event_type, resource_id, action, status | sort @timestamp desc | limit 50"
          period  = 3600
        }
      },
    ]
  })
}

# ─────────────────────────────────────────────
# CLOUDWATCH METRIC ALARMS
# ─────────────────────────────────────────────

resource "aws_cloudwatch_metric_alarm" "step_functions_failed" {
  alarm_name          = "${var.project_name}-step-functions-failed"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "ExecutionsFailed"
  namespace           = "AWS/States"
  period              = 300
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "One or more Step Functions executions failed"
  treat_missing_data  = "notBreaching"

  dimensions = {
    StateMachineArn = "arn:aws:states:us-east-1:*:stateMachine:SecurityRemediationStateMachine"
  }

  tags = { Name = "${var.project_name}-step-functions-failed" }
}

resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${var.project_name}-lambda-errors"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  threshold           = 3
  alarm_description   = "Three or more Lambda errors in 5 minutes across remediation functions"
  treat_missing_data  = "notBreaching"

  metric_query {
    id          = "total_errors"
    expression  = "SUM(METRICS())"
    label       = "Total Lambda Errors"
    return_data = true
  }

  metric_query {
    id = "e1"
    metric {
      metric_name = "Errors"
      namespace   = "AWS/Lambda"
      period      = 300
      stat        = "Sum"
      dimensions  = { FunctionName = "security-auto-s3-remediation" }
    }
  }

  metric_query {
    id = "e2"
    metric {
      metric_name = "Errors"
      namespace   = "AWS/Lambda"
      period      = 300
      stat        = "Sum"
      dimensions  = { FunctionName = "security-auto-iam-remediation" }
    }
  }

  metric_query {
    id = "e3"
    metric {
      metric_name = "Errors"
      namespace   = "AWS/Lambda"
      period      = 300
      stat        = "Sum"
      dimensions  = { FunctionName = "security-auto-vpc-remediation" }
    }
  }

  tags = { Name = "${var.project_name}-lambda-errors" }
}
