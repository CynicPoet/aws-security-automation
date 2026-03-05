output "public_bucket_name" {
  description = "Category A: S3 bucket with public-read ACL (auto-remediate)"
  value       = aws_s3_bucket.test_public.bucket
}

output "fp_website_bucket_name" {
  description = "False positive: S3 bucket tagged PublicAccess=Intentional (should be suppressed)"
  value       = aws_s3_bucket.test_fp_website.bucket
}

output "open_ssh_sg_id" {
  description = "Category A: Security group with SSH open to 0.0.0.0/0 (auto-remediate)"
  value       = aws_security_group.test_open_ssh.id
}

output "open_all_sg_id" {
  description = "Category A: Security group with all traffic open (auto-remediate)"
  value       = aws_security_group.test_open_all.id
}

output "open_rdp_sg_id" {
  description = "Category B: Security group with RDP open, Environment=Production (admin approval)"
  value       = aws_security_group.test_open_rdp.id
}

output "risky_iam_user_name" {
  description = "Category B: IAM user with AdministratorAccess + active key (admin approval)"
  value       = aws_iam_user.test_risky.name
}
