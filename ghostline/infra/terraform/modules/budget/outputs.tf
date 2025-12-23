output "budget_alerts_topic_arn" {
  description = "The ARN of the budget alerts SNS topic"
  value       = aws_sns_topic.budget_alerts.arn
}

output "monthly_budget_id" {
  description = "The ID of the monthly total budget"
  value       = aws_budgets_budget.monthly_total.id
}

output "bedrock_budget_id" {
  description = "The ID of the Bedrock budget"
  value       = aws_budgets_budget.bedrock.id
}

output "s3_budget_id" {
  description = "The ID of the S3 budget"
  value       = aws_budgets_budget.s3.id
}

output "ecs_budget_id" {
  description = "The ID of the ECS budget"
  value       = aws_budgets_budget.ecs.id
}

output "rds_budget_id" {
  description = "The ID of the RDS budget"
  value       = aws_budgets_budget.rds.id
}

output "cost_dashboard_url" {
  description = "URL to the CloudWatch cost monitoring dashboard"
  value       = "https://console.aws.amazon.com/cloudwatch/home?region=${var.project_name}-${var.environment}-costs"
}

# Anomaly monitor disabled due to account limit
# output "anomaly_monitor_arn" {
#   description = "The ARN of the cost anomaly monitor"
#   value       = aws_ce_anomaly_monitor.main.arn
# } 