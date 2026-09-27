resource "aws_iam_role" "terraform_deploy" {
  name = "TodoDerechoVecino-TerraformDeployRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Effect = "Allow"

        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:user/Administrator-V3"
        }

        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name    = "TodoDerechoVecino-TerraformDeployRole"
    Project = "todo-derecho-vecino"
  }
}

resource "aws_iam_role_policy" "terraform_deploy" {
  name = "TodoDerechoVecino-TerraformDeployPolicy"
  role = aws_iam_role.terraform_deploy.id

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Sid    = "ManageVpcInfrastructure"
        Effect = "Allow"

        Action = [
          "ec2:CreateVpc",
          "ec2:DeleteVpc",
          "ec2:ModifyVpcAttribute",
          "ec2:CreateSubnet",
          "ec2:DeleteSubnet",
          "ec2:ModifySubnetAttribute",
          "ec2:CreateRouteTable",
          "ec2:DeleteRouteTable",
          "ec2:AssociateRouteTable",
          "ec2:DisassociateRouteTable",
          "ec2:CreateTags",
          "ec2:DeleteTags",
          "ec2:DescribeVpcs",
          "ec2:DescribeVpcAttribute",
          "ec2:DescribeSubnets",
          "ec2:DescribeRouteTables",
          "ec2:DescribeAvailabilityZones"
        ]

        Resource = "*"
      },
      {
        Sid    = "ManageTerraformDeployRole"
        Effect = "Allow"

        Action = [
          "iam:GetRole",
          "iam:UpdateAssumeRolePolicy",
          "iam:DeleteRole",
          "iam:PutRolePolicy",
          "iam:GetRolePolicy",
          "iam:DeleteRolePolicy",
          "iam:ListRolePolicies",
          "iam:ListAttachedRolePolicies",
          "iam:TagRole",
          "iam:UntagRole"
        ]

        Resource = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/TodoDerechoVecino-TerraformDeployRole"
      },
      {
        Sid    = "ManageLegalDocumentsBucket"
        Effect = "Allow"

        Action = [
          "s3:CreateBucket",
          "s3:DeleteBucket",
          "s3:GetBucketLocation",
          "s3:GetBucketVersioning",
          "s3:PutBucketVersioning",
          "s3:GetEncryptionConfiguration",
          "s3:PutEncryptionConfiguration",
          "s3:GetBucketPublicAccessBlock",
          "s3:PutBucketPublicAccessBlock",
          "s3:GetBucketTagging",
          "s3:PutBucketTagging"
        ]

        Resource = "arn:aws:s3:::todo-derecho-vecino-*"
      }
    ]
  })
}
