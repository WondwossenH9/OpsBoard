output "state_bucket_name" {
  description = "S3 bucket used for OpsBoard Terraform remote state"
  value       = aws_s3_bucket.terraform_state.id
}

output "state_bucket_arn" {
  description = "ARN of the OpsBoard Terraform state bucket"
  value       = aws_s3_bucket.terraform_state.arn
}
