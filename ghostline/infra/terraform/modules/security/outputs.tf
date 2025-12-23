output "guardduty_detector_id" {
  description = "The ID of the GuardDuty detector"
  value       = aws_guardduty_detector.main.id
}

output "waf_web_acl_id" {
  description = "The ID of the WAF Web ACL"
  value       = aws_wafv2_web_acl.main.id
}

output "waf_web_acl_arn" {
  description = "The ARN of the WAF Web ACL"
  value       = aws_wafv2_web_acl.main.arn
}

output "security_alerts_topic_arn" {
  description = "The ARN of the security alerts SNS topic"
  value       = aws_sns_topic.security_alerts.arn
}

output "access_analyzer_arn" {
  description = "The ARN of the IAM Access Analyzer"
  value       = aws_accessanalyzer_analyzer.main.arn
}

output "cloudtrail_arn" {
  description = "The ARN of the CloudTrail"
  value       = var.enable_cloudtrail ? aws_cloudtrail.main[0].arn : null
}

output "cloudtrail_s3_bucket" {
  description = "The S3 bucket for CloudTrail logs"
  value       = var.enable_cloudtrail ? aws_s3_bucket.cloudtrail[0].id : null
} 