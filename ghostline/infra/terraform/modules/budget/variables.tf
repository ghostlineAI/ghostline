variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "budget_alert_emails" {
  description = "List of email addresses for budget alerts"
  type        = list(string)
}

variable "monthly_budget_limit" {
  description = "Overall monthly budget limit in USD"
  type        = number
  default     = 1000
}

variable "bedrock_budget_limit" {
  description = "Monthly budget limit for AWS Bedrock in USD"
  type        = number
  default     = 500
}

variable "s3_budget_limit" {
  description = "Monthly budget limit for S3 in USD"
  type        = number
  default     = 100
}

variable "ecs_budget_limit" {
  description = "Monthly budget limit for ECS/Fargate in USD"
  type        = number
  default     = 200
}

variable "rds_budget_limit" {
  description = "Monthly budget limit for RDS in USD"
  type        = number
  default     = 150
}

variable "kms_key_id" {
  description = "KMS key ID for SNS encryption"
  type        = string
  default     = null
} 