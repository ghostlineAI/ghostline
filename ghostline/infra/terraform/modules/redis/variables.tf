variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID for the Redis cluster"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs for the Redis cluster"
  type        = list(string)
}

variable "ecs_security_group_id" {
  description = "Security group ID for the ECS tasks to allow Redis access"
  type        = string
}

variable "node_type" {
  description = "Node type for the Redis cluster"
  type        = string
  default     = "cache.t3.micro"
} 