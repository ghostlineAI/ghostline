# GhostLine Terraform Infrastructure

## Overview

This directory contains the Infrastructure as Code (IaC) for deploying GhostLine on AWS using Terraform.

## Prerequisites

1. **AWS CLI** configured with credentials
2. **Terraform** >= 1.5.0 installed
3. **AWS Account** with appropriate permissions

## Directory Structure

```
terraform/
├── modules/           # Reusable Terraform modules
│   ├── budget/       # AWS Budgets and cost alerts
│   ├── kms/          # KMS encryption keys
│   ├── organization/ # AWS Organizations setup
│   ├── security/     # WAF, GuardDuty, Shield
│   └── vpc/          # VPC and networking
├── environments/      # Environment-specific configs
│   ├── bootstrap/    # Initial setup (S3 state bucket)
│   ├── dev/          # Development environment
│   ├── staging/      # Staging environment
│   └── prod/         # Production environment
└── README.md         # This file
```

## Deployment Steps

### Step 1: Bootstrap Terraform State Storage

First, we need to create the S3 bucket and DynamoDB table for Terraform state:

```bash
cd environments/bootstrap
terraform init
terraform plan
terraform apply
```

Save the output - you'll need the S3 bucket name and DynamoDB table name.

### Step 2: Configure Development Environment

1. Navigate to the dev environment:
```bash
cd ../dev
```

2. Create `terraform.tfvars` from the example:
```bash
cp terraform.tfvars.example terraform.tfvars
```

3. Edit `terraform.tfvars` with your email addresses:
```hcl
security_alert_emails = ["your-email@example.com"]
budget_alert_emails   = ["your-email@example.com"]
```

4. Update `main.tf` to configure the S3 backend (uncomment and fill in):
```hcl
terraform {
  backend "s3" {
    bucket         = "ghostline-terraform-state-YOUR_ACCOUNT_ID"
    key            = "dev/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "ghostline-terraform-locks"
    encrypt        = true
  }
}
```

### Step 3: Deploy Development Infrastructure

```bash
# Initialize Terraform with the backend
terraform init

# Review the plan
terraform plan

# Apply the infrastructure
terraform apply
```

## Important Notes

### AWS Organizations
The organization module is commented out by default. If you want to use AWS Organizations:
1. Enable it in the AWS Console first
2. Uncomment the organization module in `main.tf`
3. Set `create_accounts = false` unless you want to create new AWS accounts

### AWS Shield Advanced
Shield Advanced costs $3,000/month and is disabled by default. We use standard AWS Shield (free).

### Email Confirmations
After applying, check your email for:
- SNS topic subscription confirmations (click to confirm)
- AWS Budgets notifications

### Cost Optimization
- Development environment uses minimal resources
- NAT Gateway is disabled in dev (saves ~$45/month)
- Fargate Spot is configured for workers (70% savings)

## Module Details

### KMS Module
Creates encryption keys for:
- General encryption
- S3 buckets
- RDS databases
- Secrets Manager
- CloudWatch Logs
- SNS topics

### VPC Module
Creates a three-tier VPC with:
- Public subnets (ALB)
- Private app subnets (ECS tasks)
- Private DB subnets (RDS)
- Security groups for each tier

### Security Module
Configures:
- AWS WAF with managed rules
- GuardDuty threat detection
- CloudTrail audit logging
- Security Hub (optional)
- IAM Access Analyzer

### Budget Module
Sets up cost alerts for:
- Total monthly spend
- Service-specific budgets (Bedrock, S3, ECS, RDS)
- Cost anomaly detection

## Troubleshooting

### Permission Errors
Ensure your AWS credentials have these permissions:
- `AdministratorAccess` (for initial setup)
- Or specific permissions for each service

### State Lock Errors
If Terraform state is locked:
```bash
terraform force-unlock <LOCK_ID>
```

### Budget Alerts Not Working
- Confirm SNS subscriptions in your email
- Check spam folder
- Verify email addresses in `terraform.tfvars`

## Next Steps

After successful deployment:
1. Note the VPC ID and subnet IDs for application deployment
2. Configure RDS PostgreSQL with pgvector (Phase 4)
3. Deploy ECS cluster and services (Phase 5)
4. Set up API Gateway and ALB (Phase 6)

## Clean Up

To destroy resources (WARNING: This will delete everything):
```bash
terraform destroy
```

## Support

For issues or questions:
1. Check CloudWatch Logs
2. Review Terraform state: `terraform state list`
3. Consult the on-call runbook: `/docs/runbooks/oncall.md` 