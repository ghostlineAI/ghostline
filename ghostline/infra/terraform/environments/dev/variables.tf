variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "ghostline"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "allowed_regions" {
  description = "List of allowed AWS regions"
  type        = list(string)
  default     = ["us-east-1", "us-west-2"]
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones to use"
  type        = list(string)
  default     = ["us-west-2a", "us-west-2b"]
}

variable "security_alert_emails" {
  description = "Email addresses for security alerts"
  type        = list(string)
  default     = []  # Add your email addresses here
}

variable "budget_alert_emails" {
  description = "Email addresses to receive budget alerts"
  type        = list(string)
  default     = []
}

variable "domain_name" {
  description = "The root domain name (e.g., ghostline.ai)"
  type        = string
  default     = "ghostline.ai"
} 