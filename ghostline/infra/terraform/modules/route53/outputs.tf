output "zone_id" {
  description = "The hosted zone ID"
  value       = local.zone_id
}

output "name_servers" {
  description = "Name servers for the hosted zone"
  value       = var.create_hosted_zone ? aws_route53_zone.main[0].name_servers : []
}

output "certificate_arn" {
  description = "ARN of the ACM certificate"
  value       = aws_acm_certificate.main.arn
}

output "certificate_validation_status" {
  description = "Status of the certificate validation"
  value       = aws_acm_certificate_validation.main.certificate_arn
} 