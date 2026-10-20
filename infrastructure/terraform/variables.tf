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
