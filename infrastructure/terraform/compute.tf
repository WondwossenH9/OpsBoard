resource "aws_instance" "app" {
  ami           = "ami-0fa5967347d08d2df"
  instance_type = "t3.micro"

  subnet_id                   = aws_subnet.public_a.id
  vpc_security_group_ids      = [aws_security_group.ec2.id]
  iam_instance_profile        = aws_iam_instance_profile.ec2.name
  associate_public_ip_address = true

  depends_on = [
    aws_iam_role_policy.ec2_runtime_secrets
  ]

  root_block_device {
    volume_type = "gp3"
    volume_size = 8
    encrypted   = true
  }

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 2
    instance_metadata_tags      = "disabled"
  }

  credit_specification {
    cpu_credits = "standard"
  }

  tags = {
    Name = "opsboard-app"
  }
}
