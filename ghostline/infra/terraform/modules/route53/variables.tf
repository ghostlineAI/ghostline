variable "domain_name" {
  description = "The root domain name (e.g., ghostline.ai)"
  type        = string
}

variable "subdomain" {
  description = "The subdomain to create (e.g., 'dev' for dev.ghostline.ai)"
  type        = string
  default     = ""
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "create_hosted_zone" {
  description = "Whether to create a new hosted zone"
  type        = bool
  default     = false
}

variable "create_cloudfront_records" {
  description = "Whether to create CloudFront alias records"
  type        = bool
  default     = false
}

variable "cloudfront_distribution_id" {
  description = "CloudFront distribution ID to create records for"
  type        = string
  default     = ""
}

variable "cloudfront_domain_name" {
  description = "CloudFront distribution domain name"
  type        = string
  default     = ""
}

variable "cloudfront_hosted_zone_id" {
  description = "CloudFront distribution hosted zone ID"
  type        = string
  default     = ""
} 