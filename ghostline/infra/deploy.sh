#!/bin/bash
# GhostLine Infrastructure Automated Deployment Script

set -e  # Exit on error

echo "🚀 GhostLine Infrastructure Deployment"
echo "====================================="
echo ""

# Check required tools
echo "Checking required tools..."
if ! command -v terraform &> /dev/null; then
    echo "❌ Terraform not found. Please run ./setup-tools.sh first"
    exit 1
fi

if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please run ./setup-tools.sh first"
    exit 1
fi

# Set AWS credentials if provided as arguments
if [ $# -eq 3 ]; then
    export AWS_ACCESS_KEY_ID=$1
    export AWS_SECRET_ACCESS_KEY=$2
    export AWS_DEFAULT_REGION=$3
    echo "✅ AWS credentials set from arguments"
elif [ $# -gt 0 ]; then
    echo "Usage: $0 [AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_REGION]"
    exit 1
fi

# Verify AWS credentials
echo ""
echo "Verifying AWS credentials..."
if aws sts get-caller-identity > /dev/null 2>&1; then
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    echo "✅ AWS Account ID: $ACCOUNT_ID"
    echo "✅ AWS Region: ${AWS_DEFAULT_REGION:-$(aws configure get region)}"
else
    echo "❌ AWS credentials not valid. Please check your credentials."
    exit 1
fi

# Store account ID for later use
export AWS_ACCOUNT_ID=$ACCOUNT_ID

# Phase 1: Bootstrap Terraform state
echo ""
echo "📦 Phase 1: Bootstrapping Terraform State Storage"
echo "================================================"
cd terraform/environments/bootstrap

echo "Initializing Terraform..."
terraform init

echo ""
echo "Planning bootstrap infrastructure..."
terraform plan -out=bootstrap.tfplan

echo ""
read -p "Deploy bootstrap infrastructure? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    terraform apply bootstrap.tfplan
    
    # Capture outputs
    STATE_BUCKET=$(terraform output -raw backend_config | grep 'bucket =' | awk '{print $3}' | tr -d '"')
    LOCK_TABLE=$(terraform output -raw backend_config | grep 'dynamodb_table =' | awk '{print $3}' | tr -d '"')
    
    echo ""
    echo "✅ Bootstrap complete!"
    echo "State bucket: $STATE_BUCKET"
    echo "Lock table: $LOCK_TABLE"
else
    echo "Bootstrap cancelled."
    exit 1
fi

# Phase 2: Deploy Development Environment
echo ""
echo "🏗️  Phase 2: Deploying Development Environment"
echo "============================================"
cd ../dev

# Update main.tf with backend configuration
echo "Updating backend configuration..."
TEMP_FILE=$(mktemp)
BACKEND_FOUND=false

while IFS= read -r line; do
    if [[ $line =~ "# backend \"s3\"" ]]; then
        BACKEND_FOUND=true
        # Write the uncommented backend configuration
        cat >> "$TEMP_FILE" << EOF
  backend "s3" {
    bucket         = "ghostline-terraform-state-${ACCOUNT_ID}"
    key            = "dev/terraform.tfstate"
    region         = "${AWS_DEFAULT_REGION}"
    dynamodb_table = "ghostline-terraform-locks"
    encrypt        = true
  }
EOF
        # Skip the next 7 lines (the commented backend block)
        for i in {1..7}; do
            read -r line
        done
    else
        echo "$line" >> "$TEMP_FILE"
    fi
done < main.tf

if [ "$BACKEND_FOUND" = true ]; then
    mv "$TEMP_FILE" main.tf
    echo "✅ Backend configuration updated"
else
    rm "$TEMP_FILE"
    echo "⚠️  Backend configuration not found, using local state"
fi

# Create terraform.tfvars if it doesn't exist
if [ ! -f terraform.tfvars ]; then
    echo ""
    echo "Creating terraform.tfvars..."
    read -p "Enter email for security alerts (or press Enter to skip): " SECURITY_EMAIL
    read -p "Enter email for budget alerts (or press Enter to skip): " BUDGET_EMAIL
    
    cat > terraform.tfvars << EOF
# Auto-generated terraform.tfvars
# Edit these values as needed

EOF
    
    if [ -n "$SECURITY_EMAIL" ]; then
        echo "security_alert_emails = [\"$SECURITY_EMAIL\"]" >> terraform.tfvars
    else
        echo "security_alert_emails = []" >> terraform.tfvars
    fi
    
    if [ -n "$BUDGET_EMAIL" ]; then
        echo "budget_alert_emails = [\"$BUDGET_EMAIL\"]" >> terraform.tfvars
    else
        echo "budget_alert_emails = []" >> terraform.tfvars
    fi
    
    # Update for us-west-2
    if [ "$AWS_DEFAULT_REGION" == "us-west-2" ]; then
        echo "availability_zones = [\"us-west-2a\", \"us-west-2b\"]" >> terraform.tfvars
    fi
    
    echo "✅ terraform.tfvars created"
fi

# Initialize with backend
echo ""
echo "Initializing Terraform with backend..."
terraform init -reconfigure

# Plan the deployment
echo ""
echo "Planning development infrastructure..."
terraform plan -out=dev.tfplan

# Apply the deployment
echo ""
read -p "Deploy development infrastructure? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    terraform apply dev.tfplan
    
    echo ""
    echo "✅ Development environment deployed!"
    echo ""
    echo "Important outputs:"
    terraform output
    
    echo ""
    echo "⚠️  IMPORTANT NEXT STEPS:"
    echo "1. Check your email for SNS subscription confirmations"
    echo "2. Click the confirmation links to receive alerts"
    echo "3. Save the Terraform outputs for use in later phases"
    echo ""
    echo "📊 View your infrastructure:"
    echo "   - VPC: https://console.aws.amazon.com/vpc"
    echo "   - S3: https://console.aws.amazon.com/s3"
    echo "   - Budgets: https://console.aws.amazon.com/billing/home#/budgets"
    echo "   - GuardDuty: https://console.aws.amazon.com/guardduty"
else
    echo "Deployment cancelled."
    terraform destroy -target=null_resource.none bootstrap.tfplan 2>/dev/null || true
fi

echo ""
echo "🎉 Deployment script complete!" 