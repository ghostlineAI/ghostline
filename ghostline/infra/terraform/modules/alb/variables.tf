variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "public_subnet_ids" {
  description = "List of public subnet IDs for the ALB"
  type        = list(string)
}

variable "security_group_id" {
  description = "Security group ID for the ALB"
  type        = string
}

variable "log_bucket_id" {
  description = "S3 bucket ID for access logs"
  type        = string
}

variable "certificate_arn" {
  description = "ARN of the ACM certificate for HTTPS"
  type        = string
}

variable "vpc_id" {
  type        = string
  description = "The ID of the VPC"
}

variable "domain_name" {
  type        = string
  description = "The domain name for the environment"
} 