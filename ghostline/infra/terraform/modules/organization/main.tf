# AWS Organizations configuration for GhostLine

# Enable AWS Organizations (if not already enabled)
resource "aws_organizations_organization" "main" {
  feature_set = "ALL"
  
  aws_service_access_principals = [
    "cloudtrail.amazonaws.com",
    "config.amazonaws.com",
    "ram.amazonaws.com",
    "ssm.amazonaws.com",
    "sso.amazonaws.com",
    "tagpolicies.tag.amazonaws.com",
    "guardduty.amazonaws.com",
    "securityhub.amazonaws.com",
    "access-analyzer.amazonaws.com",
    "macie.amazonaws.com"
  ]
  
  enabled_policy_types = [
    "SERVICE_CONTROL_POLICY",
    "TAG_POLICY"
  ]
}

# Root Organizational Unit
data "aws_organizations_organizational_units" "root" {
  parent_id = aws_organizations_organization.main.roots[0].id
}

# Security OU
resource "aws_organizations_organizational_unit" "security" {
  name      = "Security"
  parent_id = aws_organizations_organization.main.roots[0].id
}

# Production OU
resource "aws_organizations_organizational_unit" "production" {
  name      = "Production"
  parent_id = aws_organizations_organization.main.roots[0].id
}

# Non-Production OU
resource "aws_organizations_organizational_unit" "non_production" {
  name      = "Non-Production"
  parent_id = aws_organizations_organization.main.roots[0].id
}

# Create Log Archive Account
resource "aws_organizations_account" "log_archive" {
  count = var.create_accounts ? 1 : 0
  
  name      = "${var.project_name}-log-archive"
  email     = var.log_archive_email
  parent_id = aws_organizations_organizational_unit.security.id
  
  # Prevent accidental deletion
  lifecycle {
    prevent_destroy = true
  }
}

# Create Audit Account
resource "aws_organizations_account" "audit" {
  count = var.create_accounts ? 1 : 0
  
  name      = "${var.project_name}-audit"
  email     = var.audit_email
  parent_id = aws_organizations_organizational_unit.security.id
  
  lifecycle {
    prevent_destroy = true
  }
}

# Create Development Account
resource "aws_organizations_account" "dev" {
  count = var.create_accounts ? 1 : 0
  
  name      = "${var.project_name}-dev"
  email     = var.dev_email
  parent_id = aws_organizations_organizational_unit.non_production.id
  
  lifecycle {
    prevent_destroy = true
  }
}

# Create Staging Account
resource "aws_organizations_account" "staging" {
  count = var.create_accounts ? 1 : 0
  
  name      = "${var.project_name}-staging"
  email     = var.staging_email
  parent_id = aws_organizations_organizational_unit.non_production.id
  
  lifecycle {
    prevent_destroy = true
  }
}

# Create Production Account
resource "aws_organizations_account" "prod" {
  count = var.create_accounts ? 1 : 0
  
  name      = "${var.project_name}-prod"
  email     = var.prod_email
  parent_id = aws_organizations_organizational_unit.production.id
  
  lifecycle {
    prevent_destroy = true
  }
}

# Service Control Policy to deny risky actions
resource "aws_organizations_policy" "security_guardrails" {
  name        = "SecurityGuardrails"
  description = "Baseline security controls for all accounts"
  type        = "SERVICE_CONTROL_POLICY"
  
  content = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Deny"
        Action = [
          "ec2:TerminateInstances"
        ]
        Resource = "*"
        Condition = {
          StringNotEquals = {
            "aws:RequestedRegion" = var.allowed_regions
          }
        }
      },
      {
        Effect = "Deny"
        Action = [
          "s3:DeleteBucket",
          "s3:DeleteBucketPolicy",
          "s3:PutBucketAcl",
          "s3:PutBucketPolicy"
        ]
        Resource = "*"
        Condition = {
          StringLike = {
            "aws:PrincipalOrgID" = ["!${aws_organizations_organization.main.id}"]
          }
        }
      },
      {
        Effect = "Deny"
        Action = [
          "iam:DeleteRole",
          "iam:DeleteRolePolicy",
          "iam:DeleteUserPolicy",
          "iam:PutUserPolicy",
          "iam:PutRolePolicy"
        ]
        Resource = [
          "arn:aws:iam::*:role/OrganizationAccountAccessRole",
          "arn:aws:iam::*:role/aws-controltower-*",
          "arn:aws:iam::*:role/aws-reserved/*"
        ]
      }
    ]
  })
}

# Attach Security Guardrails to all OUs
resource "aws_organizations_policy_attachment" "security_guardrails_root" {
  policy_id = aws_organizations_policy.security_guardrails.id
  target_id = aws_organizations_organization.main.roots[0].id
}

# Tag Policy for consistent tagging
resource "aws_organizations_policy" "tagging" {
  name        = "RequiredTags"
  description = "Enforce required tags on resources"
  type        = "TAG_POLICY"
  
  content = jsonencode({
    tags = {
      Project = {
        tag_key = {
          "@@assign" = "Project"
        }
        tag_value = {
          "@@assign" = [var.project_name]
        }
        enforced_for = {
          "@@assign" = [
            "ec2:instance",
            "ec2:volume",
            "s3:bucket",
            "rds:db",
            "lambda:function"
          ]
        }
      }
      Environment = {
        tag_key = {
          "@@assign" = "Environment"
        }
        tag_value = {
          "@@assign" = ["dev", "staging", "prod", "shared"]
        }
        enforced_for = {
          "@@assign" = [
            "ec2:instance",
            "ec2:volume",
            "s3:bucket",
            "rds:db",
            "lambda:function"
          ]
        }
      }
    }
  })
} 