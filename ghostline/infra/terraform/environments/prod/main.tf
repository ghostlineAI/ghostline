terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  # Backend configured from bootstrap
  backend "s3" {
    bucket         = "ghostline-terraform-state-820242943150"
    key            = "prod/terraform.tfstate"
    region         = "us-west-2"
    dynamodb_table = "ghostline-terraform-locks"
    encrypt        = true
    kms_key_id     = "arn:aws:kms:us-west-2:820242943150:key/de0480bb-1e42-4b2c-b61a-0d16ba6db385"
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# Provider for us-east-1 (required for CloudFront ACM certificates)
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
  
  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# Data source for current AWS account
data "aws_caller_identity" "current" {}

# KMS Module
module "kms" {
  source = "../../modules/kms"
  
  project_name = var.project_name
  environment  = var.environment
  aws_region   = var.aws_region
}

# VPC Module
module "vpc" {
  source = "../../modules/vpc"
  
  project_name       = var.project_name
  environment        = var.environment
  aws_region         = var.aws_region
  vpc_cidr          = var.vpc_cidr
  availability_zones = var.availability_zones
  enable_nat_gateway = true  # Always enable NAT gateway for production
  enable_flow_logs   = true
  kms_key_arn       = module.kms.logs_key_arn
}

# Security Module
module "security" {
  source = "../../modules/security"
  
  project_name          = var.project_name
  environment           = var.environment
  aws_region            = var.aws_region
  security_alert_emails = var.security_alert_emails
  kms_key_id           = module.kms.main_key_arn
  enable_shield_advanced = false  # Shield Advanced costs $3000/month
}

# Budget Module
module "budget" {
  source = "../../modules/budget"
  
  project_name        = var.project_name
  environment         = var.environment
  budget_alert_emails = var.budget_alert_emails
  
  # Production budget limits
  monthly_budget_limit = 5000
  bedrock_budget_limit = 2000
  s3_budget_limit      = 500
  ecs_budget_limit     = 1000
  rds_budget_limit     = 500
  
  kms_key_id = module.kms.sns_key_arn
}

# Route 53 Module
module "route53" {
  source = "../../modules/route53"
  
  providers = {
    aws.us_east_1 = aws.us_east_1
  }
  
  domain_name         = var.domain_name
  subdomain           = var.environment
  environment         = var.environment
  create_hosted_zone  = false  # Hosted zone already created in dev
  
  create_cloudfront_records = true
  cloudfront_domain_name    = module.frontend.cloudfront_domain_name
  cloudfront_hosted_zone_id = module.frontend.cloudfront_hosted_zone_id
}

# Frontend Module
module "frontend" {
  source = "../../modules/frontend"
  
  project_name        = var.project_name
  environment         = var.environment
  domain_name         = "${var.environment}.${var.domain_name}"
  acm_certificate_arn = module.route53.certificate_arn
  waf_web_acl_arn     = ""  # WAF for CloudFront must be in us-east-1
}

# S3 Buckets for application data
resource "aws_s3_bucket" "source_materials" {
  bucket = "${var.project_name}-${var.environment}-source-materials-${data.aws_caller_identity.current.account_id}"
  
  tags = {
    Name = "${var.project_name}-${var.environment}-source-materials"
  }
}

resource "aws_s3_bucket_versioning" "source_materials" {
  bucket = aws_s3_bucket.source_materials.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "source_materials" {
  bucket = aws_s3_bucket.source_materials.id
  
  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = module.kms.s3_key_arn
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "source_materials" {
  bucket = aws_s3_bucket.source_materials.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 bucket for generated outputs
resource "aws_s3_bucket" "outputs" {
  bucket = "${var.project_name}-${var.environment}-outputs-${data.aws_caller_identity.current.account_id}"
  
  tags = {
    Name = "${var.project_name}-${var.environment}-outputs"
  }
}

resource "aws_s3_bucket_versioning" "outputs" {
  bucket = aws_s3_bucket.outputs.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "outputs" {
  bucket = aws_s3_bucket.outputs.id
  
  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = module.kms.s3_key_arn
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "outputs" {
  bucket = aws_s3_bucket.outputs.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 bucket lifecycle policies
resource "aws_s3_bucket_lifecycle_configuration" "source_materials" {
  bucket = aws_s3_bucket.source_materials.id
  
  rule {
    id     = "transition-to-ia"
    status = "Enabled"
    
    filter {}
    
    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }
    
    transition {
      days          = 90
      storage_class = "GLACIER"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "outputs" {
  bucket = aws_s3_bucket.outputs.id
  
  rule {
    id     = "expire-old-outputs"
    status = "Enabled"
    
    filter {}
    
    expiration {
      days = 365  # Keep production outputs longer
    }
    
    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}

# S3 bucket for ALB logs
resource "aws_s3_bucket" "alb_logs" {
  bucket = "${var.project_name}-${var.environment}-alb-logs-${data.aws_caller_identity.current.account_id}"
  
  tags = {
    Name = "${var.project_name}-${var.environment}-alb-logs"
  }
}

resource "aws_s3_bucket_public_access_block" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

data "aws_elb_service_account" "main" {}

resource "aws_s3_bucket_policy" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = data.aws_elb_service_account.main.arn
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.alb_logs.arn}/alb/*"
      }
    ]
  })
}

# ACM Certificate for ALB (in us-west-2)
resource "aws_acm_certificate" "alb" {
  domain_name       = "api.${var.environment}.${var.domain_name}"
  validation_method = "DNS"
  
  tags = {
    Name = "${var.project_name}-${var.environment}-alb-cert"
  }
  
  lifecycle {
    create_before_destroy = true
  }
}

# RDS Module
module "rds" {
  source = "../../modules/rds"
  
  project_name               = var.project_name
  environment                = var.environment
  aws_region                 = var.aws_region
  db_subnet_ids              = module.vpc.private_subnet_ids
  security_group_id          = module.vpc.rds_security_group_id
  kms_key_id                 = module.kms.rds_key_arn
  
  # Production database settings
  instance_class             = "db.t3.medium"
  allocated_storage          = 100
  max_allocated_storage      = 1000
  backup_retention_period    = 30
  backup_window              = "03:00-04:00"
  maintenance_window         = "sun:04:00-sun:05:00"
  enable_deletion_protection = true
  
  db_name     = var.db_name
  db_username = var.db_username
  db_password = var.db_password
}

# Redis Module
module "redis" {
  source = "../../modules/redis"
  
  project_name      = var.project_name
  environment       = var.environment
  aws_region        = var.aws_region
  subnet_ids        = module.vpc.private_subnet_ids
  security_group_id = module.vpc.redis_security_group_id
  
  # Production Redis settings
  node_type                  = "cache.t3.small"
  num_cache_nodes            = 2  # Enable multi-AZ
  automatic_failover_enabled = true
  snapshot_retention_limit   = 7
  snapshot_window            = "03:00-05:00"
}

# ECS Module
module "ecs" {
  source = "../../modules/ecs"
  
  project_name = var.project_name
  environment  = var.environment
  aws_region   = var.aws_region
  vpc_id       = module.vpc.vpc_id
  
  # Production ECS settings
  enable_container_insights = true
}

# ALB Module
module "alb" {
  source = "../../modules/alb"
  
  project_name      = var.project_name
  environment       = var.environment
  public_subnet_ids = module.vpc.public_subnet_ids
  security_group_id = module.vpc.alb_security_group_id
  log_bucket_id     = aws_s3_bucket.alb_logs.id
  certificate_arn   = aws_acm_certificate.alb.arn
  vpc_id            = module.vpc.vpc_id
  domain_name       = "${var.environment}.${var.domain_name}"
}

# Output important values
output "source_materials_bucket" {
  value = aws_s3_bucket.source_materials.id
  description = "Name of the source materials S3 bucket"
}

output "outputs_bucket" {
  value = aws_s3_bucket.outputs.id
  description = "Name of the outputs S3 bucket"
}

output "vpc_id" {
  value = module.vpc.vpc_id
  description = "ID of the VPC"
}

output "alb_dns_name" {
  value = module.alb.dns_name
  description = "DNS name of the load balancer"
}

output "rds_endpoint" {
  value = module.rds.endpoint
  sensitive = true
  description = "RDS instance endpoint"
}

output "redis_endpoint" {
  value = module.redis.endpoint
  sensitive = true
  description = "Redis cluster endpoint"
} 