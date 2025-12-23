variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "guardduty_finding_frequency" {
  description = "Frequency for GuardDuty findings"
  type        = string
  default     = "FIFTEEN_MINUTES"
}

variable "security_alert_emails" {
  description = "List of email addresses for security alerts"
  type        = list(string)
  default     = []
}

variable "waf_rate_limit" {
  description = "Rate limit for WAF rule (requests per 5 minutes)"
  type        = number
  default     = 2000
}

variable "enable_waf_logging" {
  description = "Whether to enable WAF logging"
  type        = bool
  default     = false
}

variable "waf_log_retention_days" {
  description = "Retention period for WAF logs"
  type        = number
  default     = 30
}

variable "enable_shield_advanced" {
  description = "Whether to enable Shield Advanced (costs $3000/month)"
  type        = bool
  default     = false
}

variable "enable_security_hub" {
  description = "Whether to enable Security Hub"
  type        = bool
  default     = true
}

variable "enable_cloudtrail" {
  description = "Whether to enable CloudTrail"
  type        = bool
  default     = false
}

variable "kms_key_id" {
  description = "KMS key ID for encryption"
  type        = string
  default     = null
}

variable "alb_arn" {
  description = "ARN of the ALB to protect with Shield Advanced"
  type        = string
  default     = null
} 