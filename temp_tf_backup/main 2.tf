resource "aws_sns_topic_subscription" "budget_alerts_explicit" {
  topic_arn = module.budget.budget_alerts_topic_arn
  protocol  = "email"
  endpoint  = "alexgrgs2314@gmail.com"
}

resource "aws_sns_topic_subscription" "security_alerts_explicit" {
  topic_arn = module.security.security_alerts_topic_arn
  protocol  = "email"
  endpoint  = "alexgrgs2314@gmail.com"
} 