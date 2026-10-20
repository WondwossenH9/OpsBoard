data "aws_iam_policy_document" "ec2_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "ec2" {
  name               = "OpsBoardEC2Role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume_role.json

  tags = {
    Name = "OpsBoardEC2Role"
  }
}

resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.ec2.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "ec2" {
  name = "OpsBoardEC2InstanceProfile"
  role = aws_iam_role.ec2.name

  tags = {
    Name = "OpsBoardEC2InstanceProfile"
  }
}

data "aws_iam_policy_document" "ec2_runtime_secrets" {
  statement {
    effect = "Allow"

    actions = [
      "ssm:GetParameter"
    ]

    resources = [
      aws_ssm_parameter.db_password.arn
    ]
  }
}

resource "aws_iam_role_policy" "ec2_runtime_secrets" {
  name   = "OpsBoardRuntimeSecrets"
  role   = aws_iam_role.ec2.id
  policy = data.aws_iam_policy_document.ec2_runtime_secrets.json
}
