variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID for the RDS instance"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs for the RDS instance"
  type        = list(string)
}

variable "ecs_security_group_id" {
  description = "Security group ID for the ECS tasks to allow DB access"
  type        = string
}

variable "rds_security_group_id" {
  description = "Security group ID for the RDS instance"
  type        = string
}

variable "kms_key_id" {
  description = "KMS key ID for encryption"
  type        = string
}

variable "instance_class" {
  description = "Instance class for the RDS instance"
  type        = string
  default     = "db.t3.micro"
}

variable "allocated_storage" {
  description = "Allocated storage in GB"
  type        = number
  default     = 20
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "ghostline"
}

variable "db_username" {
  description = "Database master username"
  type        = string
  default     = "ghostlineadmin"
} 