# Create A record for CloudFront distribution
resource "aws_route53_record" "cloudfront" {
  count   = var.create_cloudfront_records ? 1 : 0
  zone_id = local.zone_id
  name    = var.subdomain != "" ? var.subdomain : var.domain_name
  type    = "A"
  
  alias {
    name                   = var.cloudfront_domain_name
    zone_id                = var.cloudfront_hosted_zone_id
    evaluate_target_health = false
  }
}

# Create AAAA record for CloudFront distribution (IPv6)
resource "aws_route53_record" "cloudfront_ipv6" {
  count   = var.create_cloudfront_records ? 1 : 0
  zone_id = local.zone_id
  name    = var.subdomain != "" ? var.subdomain : var.domain_name
  type    = "AAAA"
  
  alias {
    name                   = var.cloudfront_domain_name
    zone_id                = var.cloudfront_hosted_zone_id
    evaluate_target_health = false
  }
} 