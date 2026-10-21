resource "aws_security_group" "alb" {
  name        = "opsboard-alb-sg"
  description = "OpsBoard Application Load Balancer security group"
  vpc_id      = aws_vpc.opsboard.id

  tags = {
    Name = "opsboard-alb-sg"
  }
}

resource "aws_security_group" "ec2" {
  name        = "opsboard-ec2-sg"
  description = "OpsBoard application EC2 security group"
  vpc_id      = aws_vpc.opsboard.id

  tags = {
    Name = "opsboard-ec2-sg"
  }
}

resource "aws_security_group" "rds" {
  name        = "opsboard-rds-sg"
  description = "OpsBoard RDS MySQL security group"
  vpc_id      = aws_vpc.opsboard.id

  tags = {
    Name = "opsboard-rds-sg"
  }
}

resource "aws_vpc_security_group_ingress_rule" "alb_http" {
  security_group_id = aws_security_group.alb.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 80
  to_port           = 80
  ip_protocol       = "tcp"

  description = "Allow HTTP from the Internet"
}

resource "aws_vpc_security_group_ingress_rule" "ec2_http_from_alb" {
  security_group_id            = aws_security_group.ec2.id
  referenced_security_group_id = aws_security_group.alb.id
  from_port                    = 80
  to_port                      = 80
  ip_protocol                  = "tcp"

  description = "Allow HTTP from ALB"
}

resource "aws_vpc_security_group_ingress_rule" "rds_mysql_from_ec2" {
  security_group_id            = aws_security_group.rds.id
  referenced_security_group_id = aws_security_group.ec2.id
  from_port                    = 3306
  to_port                      = 3306
  ip_protocol                  = "tcp"

  description = "Allow MySQL from EC2"
}

resource "aws_vpc_security_group_egress_rule" "alb_all_outbound" {
  security_group_id = aws_security_group.alb.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"

  description = "Allow all outbound traffic"
}

resource "aws_vpc_security_group_egress_rule" "ec2_all_outbound" {
  security_group_id = aws_security_group.ec2.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"

  description = "Allow all outbound traffic"
}

resource "aws_vpc_security_group_egress_rule" "rds_all_outbound" {
  security_group_id = aws_security_group.rds.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"

  description = "Allow all outbound traffic"
}
