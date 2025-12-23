resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-${var.environment}-main"
  subnet_ids = var.private_subnet_ids

  tags = {
    Name = "${var.project_name}-${var.environment}-rds-subnet-group"
  }
}

# Security group is already created by VPC module, so we'll use the existing one

resource "random_password" "db_password" {
  length  = 16
  special = true
  override_special = "!#$%&'()*+,-./:;<=>?@[]^_`{|}~"
}

resource "aws_secretsmanager_secret" "db_credentials" {
  name        = "${var.project_name}/${var.environment}/database"
  description = "Database credentials for ${var.project_name} ${var.environment}"
  kms_key_id  = var.kms_key_id
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    username = "ghostlineadmin"
    password = random_password.db_password.result
  })
}

resource "aws_db_instance" "main" {
  identifier = "${var.project_name}-${var.environment}"
  
  engine               = "postgres"
  engine_version       = "15.12"
  instance_class       = var.instance_class
  allocated_storage    = var.allocated_storage
  storage_type         = "gp3"
  storage_encrypted    = true
  kms_key_id          = var.kms_key_id
  
  db_name  = var.project_name
  username = "ghostlineadmin"
  password = random_password.db_password.result
  
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [var.rds_security_group_id]
  
  # Enhanced backup settings
  backup_retention_period = 30  # Keep backups for 30 days
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  # Enable automated backups
  skip_final_snapshot = var.environment != "prod"
  final_snapshot_identifier = var.environment == "prod" ? "${var.project_name}-${var.environment}-final-${formatdate("YYYY-MM-DD-hhmm", timestamp())}" : null
  
  # Enable deletion protection in production
  deletion_protection = var.environment == "prod"
  
  # Copy tags to snapshots for better organization
  copy_tags_to_snapshot = true
  
  tags = {
    Name = "${var.project_name}-${var.environment}-rds"
  }
} 