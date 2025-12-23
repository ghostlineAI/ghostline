variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "ghostline"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-west-2"
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = "ghostline.ai"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.1.0.0/16"  # Different from dev (10.0.0.0/16)
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
  default     = ["us-west-2a", "us-west-2b", "us-west-2c"]
}

variable "security_alert_emails" {
  description = "Email addresses for security alerts"
  type        = list(string)
  default     = []
}

variable "budget_alert_emails" {
  description = "Email addresses for budget alerts"
  type        = list(string)
  default     = []
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "ghostline"
}

variable "db_username" {
  description = "Database username"
  type        = string
  default     = "ghostline"
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
} 