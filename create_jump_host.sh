#!/bin/bash

# Create a jump host for database access
echo "Creating GhostLine Jump Host for Database Access..."

# Create a key pair if it doesn't exist
if ! aws ec2 describe-key-pairs --key-names ghostline-jump-key --query 'KeyPairs[0].KeyName' --output text 2>/dev/null; then
    echo "Creating new key pair..."
    aws ec2 create-key-pair --key-name ghostline-jump-key --query 'KeyMaterial' --output text > ~/.ssh/ghostline-jump-key.pem
    chmod 600 ~/.ssh/ghostline-jump-key.pem
    echo "Key saved to ~/.ssh/ghostline-jump-key.pem"
else
    echo "Using existing key pair ghostline-jump-key"
fi

# Get the latest Amazon Linux 2 AMI
AMI_ID=$(aws ec2 describe-images \
    --owners amazon \
    --filters "Name=name,Values=amzn2-ami-hvm-*-x86_64-gp2" \
    --query 'Images | sort_by(@, &CreationDate) | [-1].ImageId' \
    --output text)

echo "Using AMI: $AMI_ID"

# Create the jump host
INSTANCE_ID=$(aws ec2 run-instances \
    --image-id $AMI_ID \
    --instance-type t3.micro \
    --key-name ghostline-jump-key \
    --subnet-id subnet-044c7900327079b34 \
    --security-group-ids sg-0a0ed33155ed7b1ea \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=ghostline-jump-host},{Key=Project,Value=ghostline},{Key=Purpose,Value=database-access}]' \
    --query 'Instances[0].InstanceId' \
    --output text)

echo "Created instance: $INSTANCE_ID"
echo "Waiting for instance to be running..."

# Wait for instance to be running
aws ec2 wait instance-running --instance-ids $INSTANCE_ID

# Get the public IP
PUBLIC_IP=$(aws ec2 describe-instances \
    --instance-ids $INSTANCE_ID \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text)

echo "Jump host is ready at: $PUBLIC_IP"

# Update SSH config
cat >> ~/.ssh/config << EOF

# GhostLine Jump Host for Database Access
Host ghostline-db
    HostName $PUBLIC_IP
    User ec2-user
    IdentityFile ~/.ssh/ghostline-jump-key.pem
    LocalForward 5432 ghostline-dev.cpygckmsmh2k.us-west-2.rds.amazonaws.com:5432
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
EOF

echo ""
echo "Jump host created successfully!"
echo ""
echo "To connect to the database:"
echo "1. In one terminal, run: ssh -N ghostline-db"
echo "2. In another terminal, run: psql -h localhost -p 5432 -U ghostlineadmin -d ghostline"
echo "   Password: YO,9~5]Vp}vrNGl"
echo ""
echo "Or use this connection string in your database client:"
echo "postgresql://ghostlineadmin:YO,9~5]Vp}vrNGl@localhost:5432/ghostline"
echo ""
echo "To terminate the jump host when done:"
echo "aws ec2 terminate-instances --instance-ids $INSTANCE_ID" 