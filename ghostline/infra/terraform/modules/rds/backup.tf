# Enhanced RDS Backup Configuration

# Note: The RDS instance is defined in main.tf with backup settings
# This file contains additional backup infrastructure using AWS Backup

# Create a backup vault for AWS Backup
resource "aws_backup_vault" "database" {
  name = "${var.project_name}-${var.environment}-db-vault"
  
  tags = {
    Name        = "${var.project_name}-${var.environment}-db-vault"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Backup plan for additional protection
resource "aws_backup_plan" "database" {
  name = "${var.project_name}-${var.environment}-db-backup-plan"

  rule {
    rule_name         = "daily_backups"
    target_vault_name = aws_backup_vault.database.name
    schedule          = "cron(0 5 * * ? *)"  # Daily at 5 AM UTC
    
    lifecycle {
      delete_after = 30  # Keep daily backups for 30 days
    }
    
    recovery_point_tags = {
      Type = "DailyBackup"
    }
  }

  rule {
    rule_name         = "weekly_backups"
    target_vault_name = aws_backup_vault.database.name
    schedule          = "cron(0 6 ? * SUN *)"  # Weekly on Sunday at 6 AM UTC
    
    lifecycle {
      delete_after = 90  # Keep weekly backups for 90 days
    }
    
    recovery_point_tags = {
      Type = "WeeklyBackup"
    }
  }
}

# Backup selection
resource "aws_backup_selection" "database" {
  name         = "${var.project_name}-${var.environment}-db-selection"
  plan_id      = aws_backup_plan.database.id
  iam_role_arn = aws_iam_role.backup.arn

  resources = [
    aws_db_instance.main.arn
  ]
}

# IAM role for AWS Backup
resource "aws_iam_role" "backup" {
  name = "${var.project_name}-${var.environment}-backup-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "backup.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "backup" {
  role       = aws_iam_role.backup.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForBackup"
}

# CloudWatch alarm for backup failures
resource "aws_cloudwatch_metric_alarm" "backup_failed" {
  alarm_name          = "${var.project_name}-${var.environment}-backup-failed"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "NumberOfBackupJobsFailed"
  namespace           = "AWS/Backup"
  period              = "86400"  # 1 day
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "This metric monitors backup failures"
  treat_missing_data  = "notBreaching"

  dimensions = {
    BackupVaultName = aws_backup_vault.database.name
  }
}

# Output backup configuration
output "backup_vault_arn" {
  value = aws_backup_vault.database.arn
}

output "backup_plan_id" {
  value = aws_backup_plan.database.id
} 