data "aws_caller_identity" "current" {}

# Pre-compute ARNs to avoid circular module dependencies
locals {
  state_machine_arn = "arn:aws:states:${var.aws_region}:${data.aws_caller_identity.current.account_id}:stateMachine:SecurityRemediationStateMachine"
  sns_topic_arn     = "arn:aws:sns:${var.aws_region}:${data.aws_caller_identity.current.account_id}:security-automation-admin-alerts"
}

module "iam" {
  source       = "./modules/iam"
  project_name = var.project_name
  aws_region   = var.aws_region
}

module "dynamodb" {
  source       = "./modules/dynamodb"
  project_name = var.project_name
}

module "budget" {
  source           = "./modules/budget"
  project_name     = var.project_name
  admin_email      = var.admin_email
  budget_limit_usd = var.budget_limit_usd
}

module "security_hub" {
  source       = "./modules/security-hub"
  project_name = var.project_name
  aws_region   = var.aws_region

  depends_on = [module.iam]
}

module "cloudwatch" {
  source       = "./modules/cloudwatch"
  project_name = var.project_name
}

module "sns" {
  source       = "./modules/sns"
  project_name = var.project_name
  admin_email  = var.admin_email
}

module "lambda_remediation" {
  source                      = "./modules/lambda-remediation"
  project_name                = var.project_name
  aws_region                  = var.aws_region
  lambda_remediation_role_arn = module.iam.lambda_remediation_role_arn
  lambda_verify_role_arn      = module.iam.lambda_verification_role_arn
  log_group_name              = module.cloudwatch.log_group_name
  findings_table_name         = module.dynamodb.findings_table_name

  depends_on = [module.iam, module.cloudwatch, module.dynamodb]
}

module "lambda_ai_analyzer" {
  source             = "./modules/lambda-ai-analyzer"
  project_name       = var.project_name
  aws_region         = var.aws_region
  lambda_ai_role_arn = module.iam.lambda_ai_analyzer_role_arn
  log_group_name     = module.cloudwatch.log_group_name
  ai_provider        = var.ai_provider
  ai_model           = var.ai_model

  depends_on = [module.iam, module.cloudwatch]
}

module "lambda_notification" {
  source                 = "./modules/lambda-notification"
  project_name           = var.project_name
  aws_region             = var.aws_region
  lambda_notify_role_arn = module.iam.lambda_notification_role_arn
  log_group_name         = module.cloudwatch.log_group_name
  sns_topic_arn          = module.sns.admin_alerts_topic_arn
  api_gateway_base_url   = module.api_gateway.base_url
  findings_table_name    = module.dynamodb.findings_table_name
  settings_table_name    = module.dynamodb.settings_table_name

  depends_on = [module.iam, module.cloudwatch, module.sns, module.api_gateway, module.dynamodb]
}

module "lambda_approval" {
  source                   = "./modules/lambda-approval"
  project_name             = var.project_name
  aws_region               = var.aws_region
  lambda_approval_role_arn = module.iam.lambda_approval_role_arn
  log_group_name           = module.cloudwatch.log_group_name

  depends_on = [module.iam, module.cloudwatch]
}

module "lambda_dashboard" {
  source                    = "./modules/lambda-dashboard"
  lambda_dashboard_role_arn = module.iam.lambda_dashboard_role_arn
  findings_table_name       = module.dynamodb.findings_table_name
  settings_table_name       = module.dynamodb.settings_table_name
  log_group_name            = module.cloudwatch.log_group_name
  state_machine_arn         = local.state_machine_arn
  eventbridge_rule_name     = "securityhub-finding-rule"
  sns_topic_arn             = local.sns_topic_arn
  account_id                = data.aws_caller_identity.current.account_id

  depends_on = [module.iam, module.dynamodb, module.cloudwatch]
}

module "api_gateway" {
  source                         = "./modules/api-gateway"
  project_name                   = var.project_name
  lambda_approval_function_arn   = module.lambda_approval.function_arn
  lambda_approval_function_name  = module.lambda_approval.function_name
  lambda_dashboard_function_arn  = module.lambda_dashboard.function_arn
  lambda_dashboard_function_name = module.lambda_dashboard.function_name

  depends_on = [module.lambda_approval, module.lambda_dashboard]
}

module "step_functions" {
  source                       = "./modules/step-functions"
  project_name                 = var.project_name
  aws_region                   = var.aws_region
  step_functions_role_arn      = module.iam.step_functions_role_arn
  ai_analyzer_function_arn     = module.lambda_ai_analyzer.function_arn
  s3_remediation_function_arn  = module.lambda_remediation.s3_remediation_arn
  iam_remediation_function_arn = module.lambda_remediation.iam_remediation_arn
  vpc_remediation_function_arn = module.lambda_remediation.vpc_remediation_arn
  verification_function_arn    = module.lambda_remediation.verification_arn
  notification_function_arn    = module.lambda_notification.function_arn
  log_group_name               = module.cloudwatch.log_group_name

  depends_on = [module.iam, module.lambda_ai_analyzer, module.lambda_remediation, module.lambda_notification]
}

module "eventbridge" {
  source               = "./modules/eventbridge"
  project_name         = var.project_name
  eventbridge_role_arn = module.iam.eventbridge_role_arn
  state_machine_arn    = module.step_functions.state_machine_arn

  depends_on = [module.step_functions]
}
