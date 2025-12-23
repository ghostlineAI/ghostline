output "organization_id" {
  description = "The ID of the organization"
  value       = aws_organizations_organization.main.id
}

output "organization_arn" {
  description = "The ARN of the organization"
  value       = aws_organizations_organization.main.arn
}

output "security_ou_id" {
  description = "The ID of the Security OU"
  value       = aws_organizations_organizational_unit.security.id
}

output "production_ou_id" {
  description = "The ID of the Production OU"
  value       = aws_organizations_organizational_unit.production.id
}

output "non_production_ou_id" {
  description = "The ID of the Non-Production OU"
  value       = aws_organizations_organizational_unit.non_production.id
}

output "log_archive_account_id" {
  description = "The ID of the log archive account"
  value       = var.create_accounts ? aws_organizations_account.log_archive[0].id : null
}

output "audit_account_id" {
  description = "The ID of the audit account"
  value       = var.create_accounts ? aws_organizations_account.audit[0].id : null
}

output "dev_account_id" {
  description = "The ID of the development account"
  value       = var.create_accounts ? aws_organizations_account.dev[0].id : null
}

output "staging_account_id" {
  description = "The ID of the staging account"
  value       = var.create_accounts ? aws_organizations_account.staging[0].id : null
}

output "prod_account_id" {
  description = "The ID of the production account"
  value       = var.create_accounts ? aws_organizations_account.prod[0].id : null
} 