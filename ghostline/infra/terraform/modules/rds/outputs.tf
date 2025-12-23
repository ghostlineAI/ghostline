output "db_instance_endpoint" {
  description = "The endpoint of the RDS instance"
  value       = aws_db_instance.main.endpoint
}

output "db_instance_port" {
  description = "The port of the RDS instance"
  value       = aws_db_instance.main.port
}

output "db_credentials_secret_arn" {
  description = "ARN of the secret containing DB credentials"
  value       = aws_secretsmanager_secret.db_credentials.arn
}

output "db_password" {
  description = "The database password"
  value       = random_password.db_password.result
  sensitive   = true
} 