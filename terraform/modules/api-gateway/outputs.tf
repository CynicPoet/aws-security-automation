output "base_url" {
  description = "Base URL for the approval API Gateway"
  value       = aws_api_gateway_stage.prod.invoke_url
}
