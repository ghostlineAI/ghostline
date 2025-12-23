output "arn" {
  description = "ARN of the ALB"
  value       = aws_lb.main.arn
}

output "dns_name" {
  description = "DNS name of the ALB"
  value       = aws_lb.main.dns_name
}

output "zone_id" {
  description = "Route 53 zone ID of the ALB"
  value       = aws_lb.main.zone_id
}

output "https_listener_arn" {
  description = "ARN of the HTTPS listener"
  value       = aws_lb_listener.https.arn
} 