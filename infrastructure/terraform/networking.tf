resource "aws_vpc" "opsboard" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "opsboard-vpc"
  }
}
resource "aws_subnet" "public_a" {
  vpc_id                  = aws_vpc.opsboard.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "us-east-1a"
  map_public_ip_on_launch = true

  tags = {
    Name = "opsboard-public-a"
  }
}

resource "aws_subnet" "public_b" {
  vpc_id                  = aws_vpc.opsboard.id
  cidr_block              = "10.0.2.0/24"
  availability_zone       = "us-east-1b"
  map_public_ip_on_launch = true

  tags = {
    Name = "opsboard-public-b"
  }
}

resource "aws_subnet" "db_private_a" {
  vpc_id                  = aws_vpc.opsboard.id
  cidr_block              = "10.0.11.0/24"
  availability_zone       = "us-east-1a"
  map_public_ip_on_launch = false

  tags = {
    Name = "opsboard-db-private-a"
  }
}

resource "aws_subnet" "db_private_b" {
  vpc_id                  = aws_vpc.opsboard.id
  cidr_block              = "10.0.12.0/24"
  availability_zone       = "us-east-1b"
  map_public_ip_on_launch = false

  tags = {
    Name = "opsboard-db-private-b"
  }
}

resource "aws_internet_gateway" "opsboard" {
  vpc_id = aws_vpc.opsboard.id

  tags = {
    Name = "opsboard-igw"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.opsboard.id

  tags = {
    Name = "opsboard-public-rt"
  }
}

resource "aws_route_table" "db_private" {
  vpc_id = aws_vpc.opsboard.id

  tags = {
    Name = "opsboard-db-private-rt"
  }
}

resource "aws_route" "public_internet" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.opsboard.id
}

resource "aws_route_table_association" "public_a" {
  subnet_id      = aws_subnet.public_a.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "public_b" {
  subnet_id      = aws_subnet.public_b.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "db_private_a" {
  subnet_id      = aws_subnet.db_private_a.id
  route_table_id = aws_route_table.db_private.id
}

resource "aws_route_table_association" "db_private_b" {
  subnet_id      = aws_subnet.db_private_b.id
  route_table_id = aws_route_table.db_private.id
}
