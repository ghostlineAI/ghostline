variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "domain_name" {
  description = "Domain name for the CloudFront distribution (e.g., dev.ghostline.ai)"
  type        = string
  default     = ""
}

variable "acm_certificate_arn" {
  description = "ARN of the ACM certificate for the domain (must be in us-east-1)"
  type        = string
  default     = ""
}

variable "waf_web_acl_arn" {
  description = "ARN of the WAF Web ACL to associate with CloudFront"
  type        = string
  default     = ""
} 