# AWS Budgets for cost monitoring

# SNS topic for budget alerts
resource "aws_sns_topic" "budget_alerts" {
  name              = "${var.project_name}-${var.environment}-budget-alerts"
  kms_master_key_id = var.kms_key_id
  
  tags = {
    Name = "${var.project_name}-${var.environment}-budget-alerts"
  }
}

# SNS subscriptions for budget alerts
resource "aws_sns_topic_subscription" "budget_alerts" {
  count     = length(var.budget_alert_emails)
  topic_arn = aws_sns_topic.budget_alerts.arn
  protocol  = "email"
  endpoint  = var.budget_alert_emails[count.index]
}

# Overall monthly budget
resource "aws_budgets_budget" "monthly_total" {
  name              = "${var.project_name}-${var.environment}-monthly-total"
  budget_type       = "COST"
  limit_amount      = var.monthly_budget_limit
  limit_unit        = "USD"
  time_unit         = "MONTHLY"
  time_period_start = formatdate("YYYY-MM-01_00:00", timestamp())
  
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type            = "PERCENTAGE"
    notification_type         = "ACTUAL"
    subscriber_email_addresses = var.budget_alert_emails
    subscriber_sns_topic_arns  = [aws_sns_topic.budget_alerts.arn]
  }
  
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type            = "PERCENTAGE"
    notification_type         = "ACTUAL"
    subscriber_email_addresses = var.budget_alert_emails
    subscriber_sns_topic_arns  = [aws_sns_topic.budget_alerts.arn]
  }
  
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 120
    threshold_type            = "PERCENTAGE"
    notification_type         = "ACTUAL"
    subscriber_email_addresses = var.budget_alert_emails
    subscriber_sns_topic_arns  = [aws_sns_topic.budget_alerts.arn]
  }
}

# Bedrock-specific budget
resource "aws_budgets_budget" "bedrock" {
  name              = "${var.project_name}-${var.environment}-bedrock"
  budget_type       = "COST"
  limit_amount      = var.bedrock_budget_limit
  limit_unit        = "USD"
  time_unit         = "MONTHLY"
  time_period_start = formatdate("YYYY-MM-01_00:00", timestamp())
  
  cost_filter {
    name   = "Service"
    values = ["Amazon Bedrock", "AWS Bedrock"]
  }
  
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type            = "PERCENTAGE"
    notification_type         = "ACTUAL"
    subscriber_email_addresses = var.budget_alert_emails
    subscriber_sns_topic_arns  = [aws_sns_topic.budget_alerts.arn]
  }
  
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type            = "PERCENTAGE"
    notification_type         = "ACTUAL"
    subscriber_email_addresses = var.budget_alert_emails
    subscriber_sns_topic_arns  = [aws_sns_topic.budget_alerts.arn]
  }
}

# S3-specific budget
resource "aws_budgets_budget" "s3" {
  name              = "${var.project_name}-${var.environment}-s3"
  budget_type       = "COST"
  limit_amount      = var.s3_budget_limit
  limit_unit        = "USD"
  time_unit         = "MONTHLY"
  time_period_start = formatdate("YYYY-MM-01_00:00", timestamp())
  
  cost_filter {
    name   = "Service"
    values = ["Amazon Simple Storage Service"]
  }
  
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type            = "PERCENTAGE"
    notification_type         = "ACTUAL"
    subscriber_email_addresses = var.budget_alert_emails
    subscriber_sns_topic_arns  = [aws_sns_topic.budget_alerts.arn]
  }
  
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type            = "PERCENTAGE"
    notification_type         = "ACTUAL"
    subscriber_email_addresses = var.budget_alert_emails
    subscriber_sns_topic_arns  = [aws_sns_topic.budget_alerts.arn]
  }
}

# ECS/Fargate-specific budget
resource "aws_budgets_budget" "ecs" {
  name              = "${var.project_name}-${var.environment}-ecs"
  budget_type       = "COST"
  limit_amount      = var.ecs_budget_limit
  limit_unit        = "USD"
  time_unit         = "MONTHLY"
  time_period_start = formatdate("YYYY-MM-01_00:00", timestamp())
  
  cost_filter {
    name   = "Service"
    values = ["Amazon Elastic Container Service", "AWS Fargate"]
  }
  
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type            = "PERCENTAGE"
    notification_type         = "ACTUAL"
    subscriber_email_addresses = var.budget_alert_emails
    subscriber_sns_topic_arns  = [aws_sns_topic.budget_alerts.arn]
  }
  
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type            = "PERCENTAGE"
    notification_type         = "ACTUAL"
    subscriber_email_addresses = var.budget_alert_emails
    subscriber_sns_topic_arns  = [aws_sns_topic.budget_alerts.arn]
  }
}

# RDS-specific budget
resource "aws_budgets_budget" "rds" {
  name              = "${var.project_name}-${var.environment}-rds"
  budget_type       = "COST"
  limit_amount      = var.rds_budget_limit
  limit_unit        = "USD"
  time_unit         = "MONTHLY"
  time_period_start = formatdate("YYYY-MM-01_00:00", timestamp())
  
  cost_filter {
    name   = "Service"
    values = ["Amazon Relational Database Service"]
  }
  
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type            = "PERCENTAGE"
    notification_type         = "ACTUAL"
    subscriber_email_addresses = var.budget_alert_emails
    subscriber_sns_topic_arns  = [aws_sns_topic.budget_alerts.arn]
  }
  
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type            = "PERCENTAGE"
    notification_type         = "ACTUAL"
    subscriber_email_addresses = var.budget_alert_emails
    subscriber_sns_topic_arns  = [aws_sns_topic.budget_alerts.arn]
  }
}

# CloudWatch dashboard for cost monitoring
resource "aws_cloudwatch_dashboard" "costs" {
  dashboard_name = "${var.project_name}-${var.environment}-costs"
  
  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        
        properties = {
          metrics = [
            ["AWS/Billing", "EstimatedCharges", "Currency", "USD", { stat = "Maximum" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "us-east-1"
          title   = "Total Estimated Charges"
          period  = 86400
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        
        properties = {
          metrics = [
            ["AWS/Billing", "EstimatedCharges", "Currency", "USD", "ServiceName", "AmazonBedrock", { stat = "Maximum" }],
            ["...", "AmazonS3", { stat = "Maximum" }],
            ["...", "AmazonECS", { stat = "Maximum" }],
            ["...", "AmazonRDS", { stat = "Maximum" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "us-east-1"
          title   = "Service-Specific Charges"
          period  = 86400
        }
      }
    ]
  })
}

# Cost anomaly detector - Disabled due to account limit
# resource "aws_ce_anomaly_monitor" "main" {
#   name              = "${var.project_name}-${var.environment}-anomaly-monitor"
#   monitor_type      = "DIMENSIONAL"
#   monitor_dimension = "SERVICE"
# }

# Cost anomaly subscription - Disabled due to account limit
# resource "aws_ce_anomaly_subscription" "main" {
#   name      = "${var.project_name}-${var.environment}-anomaly-subscription"
#   frequency = "DAILY"
#   
#   monitor_arn_list = [
#     aws_ce_anomaly_monitor.main.arn
#   ]
#   
#   subscriber {
#     type    = "EMAIL"
#     address = length(var.budget_alert_emails) > 0 ? var.budget_alert_emails[0] : "noreply@example.com"
#   }
#   
#   subscriber {
#     type    = "SNS"
#     address = aws_sns_topic.budget_alerts.arn
#   }
#   
#   threshold_expression {
#     dimension {
#       key           = "ANOMALY_TOTAL_IMPACT_ABSOLUTE"
#       values        = ["100.0"]
#       match_options = ["GREATER_THAN_OR_EQUAL"]
#     }
#   }
# } 