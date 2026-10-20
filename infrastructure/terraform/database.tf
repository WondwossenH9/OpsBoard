resource "aws_db_subnet_group" "opsboard" {
  name = "opsboard-db-subnet-group"

  subnet_ids = [
    aws_subnet.db_private_a.id,
    aws_subnet.db_private_b.id
  ]

  tags = {
    Name = "opsboard-db-subnet-group"
  }
}

resource "aws_db_instance" "opsboard" {
  identifier = "opsboard-db"

  engine         = "mysql"
  engine_version = "8.0.46"
  instance_class = "db.t4g.micro"

  allocated_storage = 20
  storage_type      = "gp3"
  storage_encrypted = true

  db_name  = "mydatabase"
  username = var.db_username
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.opsboard.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  publicly_accessible     = false
  multi_az                = false
  backup_retention_period = 1

  deletion_protection = false
  skip_final_snapshot = true

  tags = {
    Name = "opsboard-db"
  }
}
