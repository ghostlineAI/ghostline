# GhostLine Infrastructure

This repository contains Infrastructure as Code (IaC) for the GhostLine platform.

## Overview

This repository manages:
- AWS infrastructure provisioning via Terraform
- Kubernetes manifests and Helm charts
- CI/CD pipeline configurations
- Security policies and compliance
- Monitoring and alerting setup
- Backup and disaster recovery procedures

## Tech Stack

- **IaC**: Terraform / AWS CDK
- **Container Orchestration**: Amazon ECS Fargate
- **CI/CD**: GitHub Actions
- **Monitoring**: CloudWatch, X-Ray
- **Security**: AWS WAF, Shield, GuardDuty

## Prerequisites

- Terraform >= 1.5
- AWS CLI configured
- kubectl (if using K8s)
- Helm 3.x (if using Helm charts)

## Getting Started

```bash
# Initialize Terraform
cd terraform/environments/dev
terraform init

# Plan infrastructure changes
terraform plan

# Apply infrastructure changes
terraform apply

# Destroy infrastructure (use with caution!)
terraform destroy
```

## Project Structure

```
infra/
├── terraform/
│   ├── modules/       # Reusable Terraform modules
│   ├── environments/  # Environment-specific configs
│   └── backend/       # State management
├── k8s/               # Kubernetes manifests
├── helm/              # Helm charts
├── scripts/           # Utility scripts
├── security/          # Security policies
└── docs/              # Infrastructure documentation
```

## Environments

- **Development**: Low-cost, single-region setup
- **Staging**: Production-like, single-region
- **Production**: Multi-region, high availability

## Security

- All S3 buckets encrypted with KMS
- VPC with private subnets for compute
- WAF rules for API protection
- Secrets managed via AWS Secrets Manager

## Contributing

Please see our [Contributing Guide](../docs/CONTRIBUTING.md) for details.

## License

Copyright © 2025 GhostLine. All rights reserved. 