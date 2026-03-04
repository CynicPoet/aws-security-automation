module "iam" {
  source       = "./modules/iam"
  project_name = var.project_name
  aws_region   = var.aws_region
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

  depends_on = [module.iam, module.cloudwatch]
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

  depends_on = [module.iam, module.cloudwatch, module.sns, module.api_gateway]
}

module "lambda_approval" {
  source                   = "./modules/lambda-approval"
  project_name             = var.project_name
  aws_region               = var.aws_region
  lambda_approval_role_arn = module.iam.lambda_approval_role_arn
  log_group_name           = module.cloudwatch.log_group_name

  depends_on = [module.iam, module.cloudwatch]
}

module "api_gateway" {
  source                        = "./modules/api-gateway"
  project_name                  = var.project_name
  lambda_approval_function_arn  = module.lambda_approval.function_arn
  lambda_approval_function_name = module.lambda_approval.function_name

  depends_on = [module.lambda_approval]
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
