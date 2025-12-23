# KMS keys for GhostLine encryption

# Main KMS key for general encryption
resource "aws_kms_key" "main" {
  description             = "${var.project_name}-${var.environment} main encryption key"
  deletion_window_in_days = var.deletion_window_days
  enable_key_rotation     = true
  
  tags = {
    Name = "${var.project_name}-${var.environment}-main-key"
  }
}

resource "aws_kms_alias" "main" {
  name          = "alias/${var.project_name}-${var.environment}-main"
  target_key_id = aws_kms_key.main.key_id
}

# KMS key for S3 encryption
resource "aws_kms_key" "s3" {
  description             = "${var.project_name}-${var.environment} S3 encryption key"
  deletion_window_in_days = var.deletion_window_days
  enable_key_rotation     = true
  
  tags = {
    Name = "${var.project_name}-${var.environment}-s3-key"
  }
}

resource "aws_kms_alias" "s3" {
  name          = "alias/${var.project_name}-${var.environment}-s3"
  target_key_id = aws_kms_key.s3.key_id
}

# KMS key for RDS encryption
resource "aws_kms_key" "rds" {
  description             = "${var.project_name}-${var.environment} RDS encryption key"
  deletion_window_in_days = var.deletion_window_days
  enable_key_rotation     = true
  
  tags = {
    Name = "${var.project_name}-${var.environment}-rds-key"
  }
}

resource "aws_kms_alias" "rds" {
  name          = "alias/${var.project_name}-${var.environment}-rds"
  target_key_id = aws_kms_key.rds.key_id
}

# KMS key for Secrets Manager
resource "aws_kms_key" "secrets" {
  description             = "${var.project_name}-${var.environment} Secrets Manager encryption key"
  deletion_window_in_days = var.deletion_window_days
  enable_key_rotation     = true
  
  tags = {
    Name = "${var.project_name}-${var.environment}-secrets-key"
  }
}

resource "aws_kms_alias" "secrets" {
  name          = "alias/${var.project_name}-${var.environment}-secrets"
  target_key_id = aws_kms_key.secrets.key_id
}

# KMS key for CloudWatch Logs
resource "aws_kms_key" "logs" {
  description             = "${var.project_name}-${var.environment} CloudWatch Logs encryption key"
  deletion_window_in_days = var.deletion_window_days
  enable_key_rotation     = true
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Enable CloudWatch Logs"
        Effect = "Allow"
        Principal = {
          Service = "logs.${var.aws_region}.amazonaws.com"
        }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:CreateGrant",
          "kms:DescribeKey"
        ]
        Resource = "*"
        Condition = {
          ArnLike = {
            "kms:EncryptionContext:aws:logs:arn" = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:*"
          }
        }
      }
    ]
  })
  
  tags = {
    Name = "${var.project_name}-${var.environment}-logs-key"
  }
}

resource "aws_kms_alias" "logs" {
  name          = "alias/${var.project_name}-${var.environment}-logs"
  target_key_id = aws_kms_key.logs.key_id
}

# KMS key for SNS encryption
resource "aws_kms_key" "sns" {
  description             = "${var.project_name}-${var.environment} SNS encryption key"
  deletion_window_in_days = var.deletion_window_days
  enable_key_rotation     = true
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Enable SNS"
        Effect = "Allow"
        Principal = {
          Service = "sns.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = "*"
      },
      {
        Sid    = "Enable CloudWatch"
        Effect = "Allow"
        Principal = {
          Service = "cloudwatch.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = "*"
      },
      {
        Sid    = "Enable Events"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = "*"
      }
    ]
  })
  
  tags = {
    Name = "${var.project_name}-${var.environment}-sns-key"
  }
}

resource "aws_kms_alias" "sns" {
  name          = "alias/${var.project_name}-${var.environment}-sns"
  target_key_id = aws_kms_key.sns.key_id
}

# Data source for current AWS account
data "aws_caller_identity" "current" {} 