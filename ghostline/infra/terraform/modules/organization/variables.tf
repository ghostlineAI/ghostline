variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "create_accounts" {
  description = "Whether to create new AWS accounts (set to false if using existing accounts)"
  type        = bool
  default     = false
}

variable "allowed_regions" {
  description = "List of allowed AWS regions"
  type        = list(string)
  default     = ["us-east-1", "us-west-2"]
}

variable "log_archive_email" {
  description = "Email for log archive account"
  type        = string
  default     = ""
}

variable "audit_email" {
  description = "Email for audit account"
  type        = string
  default     = ""
}

variable "dev_email" {
  description = "Email for development account"
  type        = string
  default     = ""
}

variable "staging_email" {
  description = "Email for staging account"
  type        = string
  default     = ""
}

variable "prod_email" {
  description = "Email for production account"
  type        = string
  default     = ""
} 