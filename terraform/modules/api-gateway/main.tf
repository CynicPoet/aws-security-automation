data "aws_caller_identity" "current" {}

# ── REST API ──────────────────────────────────────────────────────────────────

resource "aws_api_gateway_rest_api" "approval_api" {
  name        = "SecurityAutomationApprovalAPI"
  description = "Admin approval endpoints for Security Automation pipeline"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = { Name = "SecurityAutomationApprovalAPI" }
}

# ── SHARED LAMBDA INTEGRATION ─────────────────────────────────────────────────

resource "aws_api_gateway_integration" "approve" {
  rest_api_id             = aws_api_gateway_rest_api.approval_api.id
  resource_id             = aws_api_gateway_resource.approve.id
  http_method             = aws_api_gateway_method.approve_get.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = "arn:aws:apigateway:${data.aws_region.current.name}:lambda:path/2015-03-31/functions/${var.lambda_approval_function_arn}/invocations"
}

resource "aws_api_gateway_integration" "reject" {
  rest_api_id             = aws_api_gateway_rest_api.approval_api.id
  resource_id             = aws_api_gateway_resource.reject.id
  http_method             = aws_api_gateway_method.reject_get.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = "arn:aws:apigateway:${data.aws_region.current.name}:lambda:path/2015-03-31/functions/${var.lambda_approval_function_arn}/invocations"
}

resource "aws_api_gateway_integration" "manual" {
  rest_api_id             = aws_api_gateway_rest_api.approval_api.id
  resource_id             = aws_api_gateway_resource.manual.id
  http_method             = aws_api_gateway_method.manual_get.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = "arn:aws:apigateway:${data.aws_region.current.name}:lambda:path/2015-03-31/functions/${var.lambda_approval_function_arn}/invocations"
}

data "aws_region" "current" {}

# ── /approve ──────────────────────────────────────────────────────────────────

resource "aws_api_gateway_resource" "approve" {
  rest_api_id = aws_api_gateway_rest_api.approval_api.id
  parent_id   = aws_api_gateway_rest_api.approval_api.root_resource_id
  path_part   = "approve"
}

resource "aws_api_gateway_method" "approve_get" {
  rest_api_id   = aws_api_gateway_rest_api.approval_api.id
  resource_id   = aws_api_gateway_resource.approve.id
  http_method   = "GET"
  authorization = "NONE"

  request_parameters = {
    "method.request.querystring.token"  = true
    "method.request.querystring.action" = true
  }
}

# ── /reject ───────────────────────────────────────────────────────────────────

resource "aws_api_gateway_resource" "reject" {
  rest_api_id = aws_api_gateway_rest_api.approval_api.id
  parent_id   = aws_api_gateway_rest_api.approval_api.root_resource_id
  path_part   = "reject"
}

resource "aws_api_gateway_method" "reject_get" {
  rest_api_id   = aws_api_gateway_rest_api.approval_api.id
  resource_id   = aws_api_gateway_resource.reject.id
  http_method   = "GET"
  authorization = "NONE"

  request_parameters = {
    "method.request.querystring.token" = true
  }
}

# ── /manual ───────────────────────────────────────────────────────────────────

resource "aws_api_gateway_resource" "manual" {
  rest_api_id = aws_api_gateway_rest_api.approval_api.id
  parent_id   = aws_api_gateway_rest_api.approval_api.root_resource_id
  path_part   = "manual"
}

resource "aws_api_gateway_method" "manual_get" {
  rest_api_id   = aws_api_gateway_rest_api.approval_api.id
  resource_id   = aws_api_gateway_resource.manual.id
  http_method   = "GET"
  authorization = "NONE"

  request_parameters = {
    "method.request.querystring.token" = true
  }
}

# ── DEPLOYMENT + STAGE ────────────────────────────────────────────────────────

resource "aws_api_gateway_deployment" "prod" {
  rest_api_id = aws_api_gateway_rest_api.approval_api.id

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.approve.id,
      aws_api_gateway_method.approve_get.id,
      aws_api_gateway_integration.approve.id,
      aws_api_gateway_resource.reject.id,
      aws_api_gateway_method.reject_get.id,
      aws_api_gateway_integration.reject.id,
      aws_api_gateway_resource.manual.id,
      aws_api_gateway_method.manual_get.id,
      aws_api_gateway_integration.manual.id,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [
    aws_api_gateway_integration.approve,
    aws_api_gateway_integration.reject,
    aws_api_gateway_integration.manual,
  ]
}

resource "aws_api_gateway_stage" "prod" {
  deployment_id = aws_api_gateway_deployment.prod.id
  rest_api_id   = aws_api_gateway_rest_api.approval_api.id
  stage_name    = "prod"

  tags = { Name = "SecurityAutomationApprovalAPI-prod" }
}

# ── LAMBDA PERMISSION ─────────────────────────────────────────────────────────

resource "aws_lambda_permission" "api_gateway_invoke" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_approval_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.approval_api.execution_arn}/*/*"
}
