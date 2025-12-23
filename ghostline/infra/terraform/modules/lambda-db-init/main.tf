resource "aws_iam_role" "db_init_lambda" {
  name = "${var.project_name}-${var.environment}-db-init-lambda"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "db_init_lambda_basic" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
  role       = aws_iam_role.db_init_lambda.name
}

resource "aws_lambda_function" "db_init" {
  filename         = "${path.module}/lambda.zip"
  function_name    = "${var.project_name}-${var.environment}-db-init"
  role            = aws_iam_role.db_init_lambda.arn
  handler         = "index.lambda_handler"
  source_code_hash = filebase64sha256("${path.module}/lambda.zip")
  runtime         = "python3.11"
  timeout         = 60

  vpc_config {
    subnet_ids         = var.private_subnet_ids
    security_group_ids = [var.lambda_security_group_id]
  }

  environment {
    variables = {
      DB_HOST     = var.db_host
      DB_PORT     = var.db_port
      DB_NAME     = var.db_name
      DB_USER     = var.db_user
      DB_PASSWORD = var.db_password
    }
  }
}

# Create the Lambda deployment package
data "archive_file" "lambda_zip" {
  type        = "zip"
  output_path = "${path.module}/lambda.zip"
  
  source {
    content  = file("${path.module}/../../../lambda-db-init/index.py")
    filename = "index.py"
  }
} 