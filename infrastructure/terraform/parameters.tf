resource "aws_ssm_parameter" "db_password" {
  name        = "/opsboard/db/password"
  description = "OpsBoard database password"
  type        = "SecureString"

  value_wo         = var.db_password
  value_wo_version = 1

  tags = {
    Name = "opsboard-db-password"
  }
}
