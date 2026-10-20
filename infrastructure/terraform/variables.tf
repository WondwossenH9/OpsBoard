variable "db_username" {
  description = "OpsBoard RDS master username"
  type        = string
  default     = "opsboardadmin"
}

variable "db_password" {
  description = "OpsBoard RDS master password"
  type        = string
  sensitive   = true
}

variable "alert_email" {
  description = "Email address subscribed to OpsBoard SNS alerts"
  type        = string
}
