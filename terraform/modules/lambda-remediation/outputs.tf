output "s3_remediation_arn" {
  description = "ARN of the S3 remediation Lambda function"
  value       = aws_lambda_function.s3_remediation.arn
}

output "iam_remediation_arn" {
  description = "ARN of the IAM remediation Lambda function"
  value       = aws_lambda_function.iam_remediation.arn
}

output "vpc_remediation_arn" {
  description = "ARN of the VPC remediation Lambda function"
  value       = aws_lambda_function.vpc_remediation.arn
}

output "verification_arn" {
  description = "ARN of the verification Lambda function"
  value       = aws_lambda_function.verification.arn
}
