variable "db_username" {
  description = "OpsBoard RDS master username"
  type        = string
  default     = "opsboardadmin"
}

variable "db_password" {
  description = "OpsBoard RDS master password"
  type        = string
  sensitive   = true
  ephemeral   = true
}

variable "alert_email" {
  description = "Email address subscribed to OpsBoard SNS alerts"
  type        = string

  validation {
    condition = can(regex(
      "^[^@[:space:]]+@[^@[:space:]]+\\.[^@[:space:]]+$",
      var.alert_email
    ))

    error_message = "alert_email must be a valid email address."
  }
}

variable "backend_image" {
  description = "Immutable OpsBoard backend container image"
  type        = string
  default     = "ghcr.io/wondwossenh9/opsboard-backend:b58b1c51c20196dc3d5c382dc31681bd5b755800"
}
