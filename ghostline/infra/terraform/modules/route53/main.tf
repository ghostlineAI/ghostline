# Create Route 53 hosted zone if it doesn't exist
resource "aws_route53_zone" "main" {
  count = var.create_hosted_zone ? 1 : 0
  name  = var.domain_name
  
  tags = {
    Name        = var.domain_name
    Environment = var.environment
  }
}

# Data source for existing hosted zone
data "aws_route53_zone" "main" {
  count = var.create_hosted_zone ? 0 : 1
  name  = var.domain_name
}

# Local to get the zone ID regardless of whether we created it or not
locals {
  zone_id = var.create_hosted_zone ? aws_route53_zone.main[0].zone_id : data.aws_route53_zone.main[0].zone_id
}

# Create ACM certificate for the domain (in us-east-1 for CloudFront)
resource "aws_acm_certificate" "main" {
  provider                  = aws.us_east_1
  domain_name               = var.subdomain != "" ? "${var.subdomain}.${var.domain_name}" : var.domain_name
  subject_alternative_names = var.subdomain != "" ? [] : ["*.${var.domain_name}"]
  validation_method         = "DNS"
  
  tags = {
    Name        = var.subdomain != "" ? "${var.subdomain}.${var.domain_name}" : var.domain_name
    Environment = var.environment
  }
  
  lifecycle {
    create_before_destroy = true
  }
}

# Create validation records
resource "aws_route53_record" "validation" {
  for_each = {
    for dvo in aws_acm_certificate.main.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }
  
  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = local.zone_id
}

# Certificate validation
resource "aws_acm_certificate_validation" "main" {
  provider                = aws.us_east_1
  certificate_arn         = aws_acm_certificate.main.arn
  validation_record_fqdns = [for record in aws_route53_record.validation : record.fqdn]
} 