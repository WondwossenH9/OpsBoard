variable "state_bucket_name" {
  description = "Globally unique S3 bucket name for OpsBoard Terraform state"
  type        = string

  validation {
    condition     = length(var.state_bucket_name) >= 3 && length(var.state_bucket_name) <= 63
    error_message = "state_bucket_name must be between 3 and 63 characters."
  }
}
