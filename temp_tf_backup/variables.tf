variable "security_alert_emails" {
  description = "Email addresses for security alerts"
  type        = list(string)
  default     = ["alexgrgs2314@gmail.com"]
}

variable "budget_alert_emails" {
  description = "Email addresses for budget alerts"
  type        = list(string)
  default     = ["alexgrgs2314@gmail.com"]
} 