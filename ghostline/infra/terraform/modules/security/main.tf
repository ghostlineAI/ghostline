# Security services for GhostLine

# Enable GuardDuty
resource "aws_guardduty_detector" "main" {
  enable                       = true
  finding_publishing_frequency = var.guardduty_finding_frequency
  
  datasources {
    s3_logs {
      enable = true
    }
    kubernetes {
      audit_logs {
        enable = true
      }
    }
    malware_protection {
      scan_ec2_instance_with_findings {
        ebs_volumes {
          enable = true
        }
      }
    }
  }
  
  tags = {
    Name = "${var.project_name}-${var.environment}-guardduty"
  }
}

# CloudWatch Event Rule for GuardDuty findings
resource "aws_cloudwatch_event_rule" "guardduty_findings" {
  name        = "${var.project_name}-${var.environment}-guardduty-findings"
  description = "Capture GuardDuty findings"
  
  event_pattern = jsonencode({
    source      = ["aws.guardduty"]
    detail-type = ["GuardDuty Finding"]
  })
  
  tags = {
    Name = "${var.project_name}-${var.environment}-guardduty-findings"
  }
}

# SNS topic for security alerts
resource "aws_sns_topic" "security_alerts" {
  name              = "${var.project_name}-${var.environment}-security-alerts"
  kms_master_key_id = var.kms_key_id
  
  tags = {
    Name = "${var.project_name}-${var.environment}-security-alerts"
  }
}

# SNS subscription for security alerts
resource "aws_sns_topic_subscription" "security_alerts" {
  count     = length(var.security_alert_emails)
  topic_arn = aws_sns_topic.security_alerts.arn
  protocol  = "email"
  endpoint  = var.security_alert_emails[count.index]
}

# CloudWatch Event Target for GuardDuty to SNS
resource "aws_cloudwatch_event_target" "guardduty_to_sns" {
  rule      = aws_cloudwatch_event_rule.guardduty_findings.name
  target_id = "SendToSNS"
  arn       = aws_sns_topic.security_alerts.arn
}

# IAM policy for CloudWatch Events to publish to SNS
resource "aws_sns_topic_policy" "security_alerts" {
  arn = aws_sns_topic.security_alerts.arn
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudWatchEventsToPublish"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
        Action   = "sns:Publish"
        Resource = aws_sns_topic.security_alerts.arn
      }
    ]
  })
}

# AWS WAF Web ACL
resource "aws_wafv2_web_acl" "main" {
  name  = "${var.project_name}-${var.environment}-waf"
  scope = "REGIONAL"
  
  default_action {
    allow {}
  }
  
  # AWS Managed Core Rule Set
  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 1
    
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }
    
    override_action {
      none {}
    }
    
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesCommonRuleSetMetric"
      sampled_requests_enabled   = true
    }
  }
  
  # AWS Managed Known Bad Inputs Rule Set
  rule {
    name     = "AWSManagedRulesKnownBadInputsRuleSet"
    priority = 2
    
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
        vendor_name = "AWS"
      }
    }
    
    override_action {
      none {}
    }
    
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesKnownBadInputsRuleSetMetric"
      sampled_requests_enabled   = true
    }
  }
  
  # Rate limiting rule
  rule {
    name     = "RateLimitRule"
    priority = 3
    
    statement {
      rate_based_statement {
        limit              = var.waf_rate_limit
        aggregate_key_type = "IP"
      }
    }
    
    action {
      block {}
    }
    
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "RateLimitRuleMetric"
      sampled_requests_enabled   = true
    }
  }
  
  # SQL injection protection
  rule {
    name     = "SQLInjectionRule"
    priority = 4
    
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesSQLiRuleSet"
        vendor_name = "AWS"
      }
    }
    
    override_action {
      none {}
    }
    
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "SQLInjectionRuleMetric"
      sampled_requests_enabled   = true
    }
  }
  
  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${var.project_name}-${var.environment}-waf"
    sampled_requests_enabled   = true
  }
  
  tags = {
    Name = "${var.project_name}-${var.environment}-waf"
  }
}

# WAF Logging Configuration
resource "aws_wafv2_web_acl_logging_configuration" "main" {
  count                   = var.enable_waf_logging ? 1 : 0
  resource_arn           = aws_wafv2_web_acl.main.arn
  log_destination_configs = [aws_cloudwatch_log_group.waf_logs[0].arn]
  
  redacted_fields {
    single_header {
      name = "authorization"
    }
  }
  
  redacted_fields {
    single_header {
      name = "cookie"
    }
  }
}

# CloudWatch Log Group for WAF logs
resource "aws_cloudwatch_log_group" "waf_logs" {
  count             = var.enable_waf_logging ? 1 : 0
  name              = "aws-waf-logs-${var.project_name}-${var.environment}"
  retention_in_days = var.waf_log_retention_days
  kms_key_id        = var.kms_key_id
  
  tags = {
    Name = "${var.project_name}-${var.environment}-waf-logs"
  }
}

# AWS Shield Advanced (Note: This costs $3000/month)
# Uncomment only if you have Shield Advanced subscription
# resource "aws_shield_protection" "alb" {
#   count        = var.enable_shield_advanced ? 1 : 0
#   name         = "${var.project_name}-${var.environment}-alb-shield"
#   resource_arn = var.alb_arn
#   
#   tags = {
#     Name = "${var.project_name}-${var.environment}-alb-shield"
#   }
# }

# Security Hub
resource "aws_securityhub_account" "main" {
  count = var.enable_security_hub ? 1 : 0
}

# Enable Security Hub standards
resource "aws_securityhub_standards_subscription" "aws_foundational" {
  count         = var.enable_security_hub ? 1 : 0
  standards_arn = "arn:aws:securityhub:${var.aws_region}::standards/aws-foundational-security-best-practices/v/1.0.0"
  
  depends_on = [aws_securityhub_account.main]
}

resource "aws_securityhub_standards_subscription" "cis" {
  count         = var.enable_security_hub ? 1 : 0
  standards_arn = "arn:aws:securityhub:::ruleset/cis-aws-foundations-benchmark/v/1.2.0"
  
  depends_on = [aws_securityhub_account.main]
}

# IAM Access Analyzer
resource "aws_accessanalyzer_analyzer" "main" {
  analyzer_name = "${var.project_name}-${var.environment}-analyzer"
  type          = "ACCOUNT"
  
  tags = {
    Name = "${var.project_name}-${var.environment}-analyzer"
  }
}

# CloudTrail for audit logging
resource "aws_cloudtrail" "main" {
  count                      = var.enable_cloudtrail ? 1 : 0
  name                       = "${var.project_name}-${var.environment}-trail"
  s3_bucket_name            = aws_s3_bucket.cloudtrail[0].id
  include_global_service_events = true
  is_multi_region_trail     = true
  enable_logging            = true
  
  event_selector {
    read_write_type           = "All"
    include_management_events = true
    
    data_resource {
      type   = "AWS::S3::Object"
      values = ["arn:aws:s3:::*/*"]
    }
  }
  
  kms_key_id = var.kms_key_id
  
  tags = {
    Name = "${var.project_name}-${var.environment}-trail"
  }
  
  depends_on = [aws_s3_bucket_policy.cloudtrail]
}

# S3 bucket for CloudTrail logs
resource "aws_s3_bucket" "cloudtrail" {
  count  = var.enable_cloudtrail ? 1 : 0
  bucket = "${var.project_name}-${var.environment}-cloudtrail-${data.aws_caller_identity.current.account_id}"
  
  tags = {
    Name = "${var.project_name}-${var.environment}-cloudtrail"
  }
}

# Enable S3 bucket versioning
resource "aws_s3_bucket_versioning" "cloudtrail" {
  count  = var.enable_cloudtrail ? 1 : 0
  bucket = aws_s3_bucket.cloudtrail[0].id
  
  versioning_configuration {
    status = "Enabled"
  }
}

# Enable S3 bucket encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "cloudtrail" {
  count  = var.enable_cloudtrail ? 1 : 0
  bucket = aws_s3_bucket.cloudtrail[0].id
  
  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = var.kms_key_id
      sse_algorithm     = "aws:kms"
    }
  }
}

# Block public access to CloudTrail bucket
resource "aws_s3_bucket_public_access_block" "cloudtrail" {
  count  = var.enable_cloudtrail ? 1 : 0
  bucket = aws_s3_bucket.cloudtrail[0].id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 bucket policy for CloudTrail
resource "aws_s3_bucket_policy" "cloudtrail" {
  count  = var.enable_cloudtrail ? 1 : 0
  bucket = aws_s3_bucket.cloudtrail[0].id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AWSCloudTrailAclCheck"
        Effect = "Allow"
        Principal = {
          Service = "cloudtrail.amazonaws.com"
        }
        Action   = "s3:GetBucketAcl"
        Resource = aws_s3_bucket.cloudtrail[0].arn
      },
      {
        Sid    = "AWSCloudTrailWrite"
        Effect = "Allow"
        Principal = {
          Service = "cloudtrail.amazonaws.com"
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.cloudtrail[0].arn}/*"
        Condition = {
          StringEquals = {
            "s3:x-amz-acl" = "bucket-owner-full-control"
          }
        }
      }
    ]
  })
}

# Data source for current AWS account
data "aws_caller_identity" "current" {} 