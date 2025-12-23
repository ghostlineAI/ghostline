output "main_key_id" {
  description = "The ID of the main KMS key"
  value       = aws_kms_key.main.id
}

output "main_key_arn" {
  description = "The ARN of the main KMS key"
  value       = aws_kms_key.main.arn
}

output "s3_key_id" {
  description = "The ID of the S3 KMS key"
  value       = aws_kms_key.s3.id
}

output "s3_key_arn" {
  description = "The ARN of the S3 KMS key"
  value       = aws_kms_key.s3.arn
}

output "rds_key_id" {
  description = "The ID of the RDS KMS key"
  value       = aws_kms_key.rds.id
}

output "rds_key_arn" {
  description = "The ARN of the RDS KMS key"
  value       = aws_kms_key.rds.arn
}

output "secrets_key_id" {
  description = "The ID of the Secrets Manager KMS key"
  value       = aws_kms_key.secrets.id
}

output "secrets_key_arn" {
  description = "The ARN of the Secrets Manager KMS key"
  value       = aws_kms_key.secrets.arn
}

output "logs_key_id" {
  description = "The ID of the CloudWatch Logs KMS key"
  value       = aws_kms_key.logs.id
}

output "logs_key_arn" {
  description = "The ARN of the CloudWatch Logs KMS key"
  value       = aws_kms_key.logs.arn
}

output "sns_key_id" {
  description = "The ID of the SNS KMS key"
  value       = aws_kms_key.sns.id
}

output "sns_key_arn" {
  description = "The ARN of the SNS KMS key"
  value       = aws_kms_key.sns.arn
} 