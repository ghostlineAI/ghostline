#!/bin/bash
# Setup script for GhostLine infrastructure deployment tools

echo "GhostLine Infrastructure Tools Setup"
echo "===================================="
echo ""

# Detect OS
OS=$(uname -s)
ARCH=$(uname -m)

if [[ "$OS" == "Darwin" ]]; then
    echo "Detected macOS"
    
    # Check if Homebrew is installed
    if ! command -v brew &> /dev/null; then
        echo "Homebrew not found. Please install Homebrew first:"
        echo "/bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        exit 1
    fi
    
    echo "Installing AWS CLI v2..."
    if ! command -v aws &> /dev/null; then
        brew install awscli
    else
        echo "AWS CLI already installed"
    fi
    
    echo "Installing Terraform..."
    if ! command -v terraform &> /dev/null; then
        brew tap hashicorp/tap
        brew install hashicorp/tap/terraform
    else
        echo "Terraform already installed"
    fi
    
elif [[ "$OS" == "Linux" ]]; then
    echo "Detected Linux"
    
    echo "Installing AWS CLI v2..."
    if ! command -v aws &> /dev/null; then
        curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
        unzip awscliv2.zip
        sudo ./aws/install
        rm -rf awscliv2.zip aws/
    else
        echo "AWS CLI already installed"
    fi
    
    echo "Installing Terraform..."
    if ! command -v terraform &> /dev/null; then
        wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
        echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
        sudo apt update && sudo apt install terraform
    else
        echo "Terraform already installed"
    fi
else
    echo "Unsupported OS: $OS"
    exit 1
fi

echo ""
echo "Verifying installations..."
echo "=========================="

# Verify AWS CLI
if command -v aws &> /dev/null; then
    echo "✅ AWS CLI version: $(aws --version)"
else
    echo "❌ AWS CLI installation failed"
fi

# Verify Terraform
if command -v terraform &> /dev/null; then
    echo "✅ Terraform version: $(terraform version -json | grep '"terraform_version"' | cut -d'"' -f4)"
else
    echo "❌ Terraform installation failed"
fi

echo ""
echo "Setup complete! You can now run the deployment." 