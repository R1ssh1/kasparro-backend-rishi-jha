# AWS Region
variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

# Environment
variable "environment" {
  description = "Environment (development, staging, production)"
  type        = string
  default     = "development"
}

# Database Configuration
variable "db_name" {
  description = "PostgreSQL database name"
  type        = string
  default     = "kasparro"
}

variable "db_username" {
  description = "PostgreSQL master username"
  type        = string
  default     = "kasparro_admin"
}

variable "db_password" {
  description = "PostgreSQL master password"
  type        = string
  sensitive   = true
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"  # Free tier eligible
}

# Application Secrets
variable "coingecko_api_key" {
  description = "CoinGecko API key"
  type        = string
  sensitive   = true
}

variable "admin_api_key" {
  description = "Admin API key for protected endpoints"
  type        = string
  sensitive   = true
}

# Docker Image
variable "docker_image" {
  description = "Docker image for ECS tasks"
  type        = string
  default     = "ghcr.io/r1ssh1/kasparro-backend-rishi-jha:latest"
}

# ECS API Service Configuration
variable "api_cpu" {
  description = "CPU units for API task (256 = 0.25 vCPU)"
  type        = number
  default     = 256
}

variable "api_memory" {
  description = "Memory for API task in MB"
  type        = number
  default     = 512
}

variable "api_task_count" {
  description = "Number of API tasks to run"
  type        = number
  default     = 1
}

# ECS Worker Configuration
variable "worker_cpu" {
  description = "CPU units for worker task"
  type        = number
  default     = 256
}

variable "worker_memory" {
  description = "Memory for worker task in MB"
  type        = number
  default     = 512
}
