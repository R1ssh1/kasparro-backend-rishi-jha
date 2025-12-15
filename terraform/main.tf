# Kasparro Backend - AWS Infrastructure
# Deploys FastAPI app on ECS Fargate with RDS PostgreSQL and EventBridge cron

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  # Backend for state storage (update with your S3 bucket)
  # backend "s3" {
  #   bucket = "kasparro-terraform-state"
  #   key    = "kasparro/terraform.tfstate"
  #   region = "us-east-1"
  # }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "Kasparro"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

# VPC and Networking
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "kasparro-vpc"
  }
}

resource "aws_subnet" "public" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index + 1}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]
  
  map_public_ip_on_launch = true

  tags = {
    Name = "kasparro-public-${count.index + 1}"
  }
}

resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index + 10}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "kasparro-private-${count.index + 1}"
  }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "kasparro-igw"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "kasparro-public-rt"
  }
}

resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# Security Groups
resource "aws_security_group" "ecs_tasks" {
  name_prefix = "kasparro-ecs-tasks-"
  description = "Security group for ECS tasks"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow HTTP from anywhere"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound"
  }

  tags = {
    Name = "kasparro-ecs-tasks-sg"
  }
}

resource "aws_security_group" "rds" {
  name_prefix = "kasparro-rds-"
  description = "Security group for RDS PostgreSQL"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
    description     = "PostgreSQL from ECS tasks"
  }

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.main.cidr_block]
    description = "PostgreSQL from VPC"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "kasparro-rds-sg"
  }
}

# RDS PostgreSQL
resource "aws_db_subnet_group" "main" {
  name       = "kasparro-db-subnet-group"
  subnet_ids = concat(aws_subnet.public[*].id, aws_subnet.private[*].id)  # Include both for flexibility

  tags = {
    Name = "kasparro-db-subnet-group"
  }
}

resource "aws_db_instance" "postgres" {
  identifier        = "kasparro-postgres"
  engine            = "postgres"
  engine_version    = "15.10"
  instance_class    = var.db_instance_class
  allocated_storage = 20
  storage_type      = "gp3"
  
  db_name  = var.db_name
  username = var.db_username
  password = var.db_password
  
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = true  # Enable for ECS task connectivity
  
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "mon:04:00-mon:05:00"
  
  skip_final_snapshot       = var.environment == "development"
  final_snapshot_identifier = var.environment == "development" ? null : "kasparro-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"
  
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  
  tags = {
    Name = "kasparro-postgres"
  }
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "kasparro-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name = "kasparro-cluster"
  }
}

# ECS Task Execution Role
resource "aws_iam_role" "ecs_task_execution" {
  name = "kasparro-ecs-task-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ECS Task Role (for application permissions)
resource "aws_iam_role" "ecs_task" {
  name = "kasparro-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/kasparro-api"
  retention_in_days = 30

  tags = {
    Name = "kasparro-ecs-logs"
  }
}

resource "aws_cloudwatch_log_group" "worker" {
  name              = "/ecs/kasparro-worker"
  retention_in_days = 30

  tags = {
    Name = "kasparro-worker-logs"
  }
}

# Secrets Manager for sensitive data
resource "aws_secretsmanager_secret" "app_secrets" {
  name        = "kasparro/app-secrets"
  description = "Application secrets for Kasparro ETL"
}

resource "aws_secretsmanager_secret_version" "app_secrets" {
  secret_id = aws_secretsmanager_secret.app_secrets.id
  secret_string = jsonencode({
    COINGECKO_API_KEY = var.coingecko_api_key
    ADMIN_API_KEY     = var.admin_api_key
  })
}

# IAM policy for accessing secrets
resource "aws_iam_role_policy" "ecs_task_secrets" {
  name = "kasparro-ecs-task-secrets-policy"
  role = aws_iam_role.ecs_task_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "secretsmanager:GetSecretValue"
      ]
      Resource = [
        aws_secretsmanager_secret.app_secrets.arn
      ]
    }]
  })
}

# ECS Task Definition
resource "aws_ecs_task_definition" "api" {
  family                   = "kasparro-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.api_cpu
  memory                   = var.api_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name  = "api"
    image = var.docker_image
    
    essential = true
    
    portMappings = [{
      containerPort = 8000
      protocol      = "tcp"
    }]
    
    environment = [
      {
        name  = "APP_ENV"
        value = var.environment
      },
      {
        name  = "LOG_LEVEL"
        value = "INFO"
      },
      {
        name  = "DATABASE_URL"
        value = "postgresql+asyncpg://${var.db_username}:${var.db_password}@${aws_db_instance.postgres.endpoint}/${var.db_name}"
      },
      {
        name  = "DATABASE_URL_SYNC"
        value = "postgresql://${var.db_username}:${var.db_password}@${aws_db_instance.postgres.endpoint}/${var.db_name}"
      },
      {
        name  = "DATABASE_HOST"
        value = split(":", aws_db_instance.postgres.endpoint)[0]
      },
      {
        name  = "DATABASE_USER"
        value = var.db_username
      },
      {
        name  = "DATABASE_PASSWORD"
        value = var.db_password
      },
      {
        name  = "DATABASE_NAME"
        value = var.db_name
      },
      {
        name  = "COINGECKO_RATE_LIMIT"
        value = "30"
      }
    ]
    
    secrets = [
      {
        name      = "COINGECKO_API_KEY"
        valueFrom = "${aws_secretsmanager_secret.app_secrets.arn}:COINGECKO_API_KEY::"
      },
      {
        name      = "ADMIN_API_KEY"
        valueFrom = "${aws_secretsmanager_secret.app_secrets.arn}:ADMIN_API_KEY::"
      }
    ]
    
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "api"
      }
    }
    
    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }
  }])

  tags = {
    Name = "kasparro-api-task"
  }
}

# ECS Service
resource "aws_ecs_service" "api" {
  name            = "kasparro-api-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.api_task_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = true
  }

  depends_on = [
    aws_iam_role_policy_attachment.ecs_task_execution
  ]

  tags = {
    Name = "kasparro-api-service"
  }
}

# ECS Task Definition for Worker (ETL)
resource "aws_ecs_task_definition" "worker" {
  family                   = "kasparro-worker"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.worker_cpu
  memory                   = var.worker_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name  = "worker"
    image = var.docker_image
    
    entryPoint = ["/app/docker-entrypoint-worker.sh"]
    command = ["python", "-m", "worker.scheduler"]
    
    essential = true
    
    environment = [
      {
        name  = "APP_ENV"
        value = var.environment
      },
      {
        name  = "LOG_LEVEL"
        value = "INFO"
      },
      {
        name  = "DATABASE_URL"
        value = "postgresql+asyncpg://${var.db_username}:${var.db_password}@${aws_db_instance.postgres.endpoint}/${var.db_name}"
      },
      {
        name  = "DATABASE_URL_SYNC"
        value = "postgresql://${var.db_username}:${var.db_password}@${aws_db_instance.postgres.endpoint}/${var.db_name}"
      },
      {
        name  = "DATABASE_HOST"
        value = split(":", aws_db_instance.postgres.endpoint)[0]
      },
      {
        name  = "DATABASE_USER"
        value = var.db_username
      },
      {
        name  = "DATABASE_PASSWORD"
        value = var.db_password
      },
      {
        name  = "DATABASE_NAME"
        value = var.db_name
      },
      {
        name  = "ETL_SCHEDULE_MINUTES"
        value = "60"
      },
      {
        name  = "COINGECKO_RATE_LIMIT"
        value = "30"
      }
    ]
    
    secrets = [
      {
        name      = "COINGECKO_API_KEY"
        valueFrom = "${aws_secretsmanager_secret.app_secrets.arn}:COINGECKO_API_KEY::"
      },
      {
        name      = "ADMIN_API_KEY"
        valueFrom = "${aws_secretsmanager_secret.app_secrets.arn}:ADMIN_API_KEY::"
      }
    ]
    
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.worker.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "worker"
      }
    }
  }])

  tags = {
    Name = "kasparro-worker-task"
  }
}

# EventBridge Rule for ETL Cron Job
resource "aws_cloudwatch_event_rule" "etl_schedule" {
  name                = "kasparro-etl-hourly"
  description         = "Trigger Kasparro ETL every hour"
  schedule_expression = "rate(1 hour)"

  tags = {
    Name = "kasparro-etl-schedule"
  }
}

# IAM role for EventBridge to run ECS tasks
resource "aws_iam_role" "eventbridge_ecs" {
  name = "kasparro-eventbridge-ecs-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "events.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "eventbridge_ecs" {
  name = "kasparro-eventbridge-ecs-policy"
  role = aws_iam_role.eventbridge_ecs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "ecs:RunTask"
      ]
      Resource = [
        aws_ecs_task_definition.worker.arn
      ]
    },
    {
      Effect = "Allow"
      Action = [
        "iam:PassRole"
      ]
      Resource = [
        aws_iam_role.ecs_task_execution.arn,
        aws_iam_role.ecs_task.arn
      ]
    }]
  })
}

# EventBridge Target - Run ECS Task
resource "aws_cloudwatch_event_target" "etl_worker" {
  rule      = aws_cloudwatch_event_rule.etl_schedule.name
  target_id = "kasparro-etl-worker"
  arn       = aws_ecs_cluster.main.arn
  role_arn  = aws_iam_role.eventbridge_ecs.arn

  ecs_target {
    task_count          = 1
    task_definition_arn = aws_ecs_task_definition.worker.arn
    launch_type         = "FARGATE"
    
    network_configuration {
      subnets          = aws_subnet.public[*].id
      security_groups  = [aws_security_group.ecs_tasks.id]
      assign_public_ip = true
    }
  }
}
