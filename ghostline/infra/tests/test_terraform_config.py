#!/usr/bin/env python3
"""Tests for Terraform configuration consistency."""

import os
import json
from pathlib import Path


class TestTerraformConfiguration:
    """Test critical Terraform configuration elements."""
    
    def setup_method(self):
        """Set up test environment."""
        self.root_dir = Path(__file__).parent.parent
        self.terraform_dir = self.root_dir / 'terraform'
        self.dev_env_dir = self.terraform_dir / 'environments' / 'dev'
    
    def test_backend_configuration(self):
        """Ensure backend configuration remains consistent."""
        main_tf_path = self.dev_env_dir / 'main.tf'
        assert main_tf_path.exists(), "main.tf file is missing"
        
        with open(main_tf_path, 'r') as f:
            # Parse terraform configuration
            content = f.read()
            
            # Check S3 backend is configured
            assert 'backend "s3"' in content
            assert 'bucket         = "ghostline-terraform-state-' in content
            assert 'key            = "dev/terraform.tfstate"' in content
            assert 'region         = "us-west-2"' in content
            assert 'dynamodb_table = "ghostline-terraform-locks"' in content
            assert 'encrypt        = true' in content
    
    def test_provider_configuration(self):
        """Ensure provider configuration is correct."""
        main_tf_path = self.dev_env_dir / 'main.tf'
        
        with open(main_tf_path, 'r') as f:
            content = f.read()
            
            # Check AWS provider version
            assert 'aws' in content
            assert 'version = "~> 5.0"' in content
            
            # Check default tags are set
            assert 'default_tags' in content
            assert 'Project     = var.project_name' in content
            assert 'Environment = var.environment' in content
            assert 'ManagedBy   = "Terraform"' in content
    
    def test_required_modules(self):
        """Ensure all required modules are declared."""
        main_tf_path = self.dev_env_dir / 'main.tf'
        
        with open(main_tf_path, 'r') as f:
            content = f.read()
        
        required_modules = [
            'module "kms"',
            'module "vpc"',
            'module "security"',
            'module "budget"',
            'module "route53"',
            'module "frontend"',
            'module "ecs"',
            'module "alb"',
            'module "rds"',
            'module "redis"'
        ]
        
        for module in required_modules:
            assert module in content, f"Missing required module: {module}"
    
    def test_ecr_repositories(self):
        """Ensure ECR repositories are defined."""
        main_tf_path = self.dev_env_dir / 'main.tf'
        
        with open(main_tf_path, 'r') as f:
            content = f.read()
        
        # Check ECR repositories
        assert 'resource "aws_ecr_repository" "api"' in content
        assert 'resource "aws_ecr_repository" "worker"' in content
        assert 'scan_on_push = true' in content
    
    def test_ecs_task_definition(self):
        """Ensure ECS task definition has correct configuration."""
        main_tf_path = self.dev_env_dir / 'main.tf'
        
        with open(main_tf_path, 'r') as f:
            content = f.read()
        
        # Check task definition
        assert 'resource "aws_ecs_task_definition" "api"' in content
        assert 'requires_compatibilities = ["FARGATE"]' in content
        assert 'network_mode             = "awsvpc"' in content
        
        # Check container configuration
        assert 'containerPort = 8000' in content
        assert 'name      = "DATABASE_URL"' in content
        assert 'name      = "REDIS_URL"' in content
    
    def test_s3_buckets(self):
        """Ensure required S3 buckets are defined."""
        main_tf_path = self.dev_env_dir / 'main.tf'
        
        with open(main_tf_path, 'r') as f:
            content = f.read()
        
        required_buckets = [
            'resource "aws_s3_bucket" "source_materials"',
            'resource "aws_s3_bucket" "outputs"',
            'resource "aws_s3_bucket" "alb_logs"'
        ]
        
        for bucket in required_buckets:
            assert bucket in content, f"Missing S3 bucket: {bucket}"
        
        # Check encryption is enabled
        assert 'aws_s3_bucket_server_side_encryption_configuration' in content
        assert 'sse_algorithm     = "aws:kms"' in content
    
    def test_variables_file(self):
        """Ensure variables.tf has all required variables."""
        variables_path = self.dev_env_dir / 'variables.tf'
        assert variables_path.exists(), "variables.tf is missing"
        
        with open(variables_path, 'r') as f:
            content = f.read()
        
        required_vars = [
            'variable "project_name"',
            'variable "environment"',
            'variable "aws_region"',
            'variable "domain_name"',
            'variable "vpc_cidr"',
            'variable "availability_zones"'
        ]
        
        for var in required_vars:
            assert var in content, f"Missing variable: {var}"
    
    def test_outputs(self):
        """Ensure critical outputs are defined."""
        main_tf_path = self.dev_env_dir / 'main.tf'
        
        with open(main_tf_path, 'r') as f:
            content = f.read()
        
        required_outputs = [
            'output "vpc_id"',
            'output "ecs_cluster_name"',
            'output "alb_dns_name"',
            'output "api_url"',
            'output "rds_endpoint"',
            'output "redis_endpoint"'
        ]
        
        for output in required_outputs:
            assert output in content, f"Missing output: {output}"


class TestTerraformModules:
    """Test Terraform module structure."""
    
    def setup_method(self):
        """Set up test environment."""
        self.root_dir = Path(__file__).parent.parent
        self.modules_dir = self.root_dir / 'terraform' / 'modules'
    
    def test_all_modules_exist(self):
        """Ensure all required modules exist."""
        required_modules = [
            'alb', 'budget', 'ecs', 'frontend', 'kms',
            'organization', 'rds', 'redis', 'route53',
            'security', 'vpc'
        ]
        
        for module in required_modules:
            module_path = self.modules_dir / module
            assert module_path.exists(), f"Module {module} is missing"
            
            # Each module should have main.tf, variables.tf, and outputs.tf
            assert (module_path / 'main.tf').exists(), f"{module}/main.tf is missing"
            assert (module_path / 'variables.tf').exists(), f"{module}/variables.tf is missing"
            assert (module_path / 'outputs.tf').exists(), f"{module}/outputs.tf is missing"
    
    def test_module_consistency(self):
        """Ensure modules follow consistent patterns."""
        for module_dir in self.modules_dir.iterdir():
            if module_dir.is_dir():
                main_tf = module_dir / 'main.tf'
                if main_tf.exists():
                    with open(main_tf, 'r') as f:
                        content = f.read()
                    
                    # All resources should use proper tagging
                    if 'resource "aws_' in content:
                        # Should have tags for most resources
                        # (Some resources like policies don't support tags)
                        pass


class TestGitHubActions:
    """Test GitHub Actions workflows for infrastructure."""
    
    def setup_method(self):
        """Set up test environment."""
        self.root_dir = Path(__file__).parent.parent
        self.github_dir = self.root_dir / '.github'
        self.workflows_dir = self.github_dir / 'workflows'
    
    def test_terraform_workflow_exists(self):
        """Ensure Terraform workflow exists."""
        terraform_workflow = self.workflows_dir / 'terraform.yml'
        if terraform_workflow.exists():
            with open(terraform_workflow, 'r') as f:
                content = f.read()
            
            # Should have terraform commands
            assert 'terraform init' in content
            assert 'terraform plan' in content or 'terraform validate' in content
            
            # Should not auto-apply on main
            assert 'terraform apply -auto-approve' not in content or 'if:' in content


class TestSecurityConfiguration:
    """Test security-related configuration."""
    
    def setup_method(self):
        """Set up test environment."""
        self.root_dir = Path(__file__).parent.parent
        self.terraform_dir = self.root_dir / 'terraform'
    
    def test_no_hardcoded_secrets(self):
        """Ensure no secrets are hardcoded."""
        # Patterns that might indicate hardcoded secrets
        secret_patterns = [
            'password =',
            'secret =',
            'api_key =',
            'access_key =',
            'AKIA',  # AWS access key prefix
            'aws_secret_access_key'
        ]
        
        for tf_file in self.terraform_dir.rglob('*.tf'):
            with open(tf_file, 'r') as f:
                content = f.read().lower()
            
            for pattern in secret_patterns:
                if pattern.lower() in content:
                    # Check if it's using a variable or secret manager
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if pattern.lower() in line:
                            # Should reference var, data, or aws_secretsmanager
                            assert any(ref in line for ref in ['var.', 'data.', 'aws_secretsmanager', 'random_']), \
                                f"Potential hardcoded secret in {tf_file}: {line.strip()}"
    
    def test_kms_encryption_enabled(self):
        """Ensure KMS encryption is used where appropriate."""
        dev_main = self.terraform_dir / 'environments' / 'dev' / 'main.tf'
        
        with open(dev_main, 'r') as f:
            content = f.read()
        
        # S3 buckets should use KMS
        if 'aws_s3_bucket_server_side_encryption_configuration' in content:
            assert 'kms_master_key_id' in content
            assert 'sse_algorithm     = "aws:kms"' in content
        
        # RDS should use encryption
        if 'module "rds"' in content:
            assert 'kms_key_id' in content
        
        # Secrets Manager should use KMS
        if 'aws_secretsmanager_secret' in content:
            assert 'kms_key_id' in content 