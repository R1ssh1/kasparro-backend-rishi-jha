# API Endpoint
output "api_endpoint" {
  description = "Public API endpoint URL"
  value       = "http://${aws_lb.main.dns_name}"
}

output "api_endpoint_https" {
  description = "HTTPS API endpoint (requires SSL certificate setup)"
  value       = "https://${aws_lb.main.dns_name}"
}

# Database
output "database_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = aws_db_instance.postgres.endpoint
  sensitive   = true
}

output "database_name" {
  description = "Database name"
  value       = aws_db_instance.postgres.db_name
}

# ECS Cluster
output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}

output "ecs_cluster_arn" {
  description = "ECS cluster ARN"
  value       = aws_ecs_cluster.main.arn
}

# ECS Services
output "api_service_name" {
  description = "API ECS service name"
  value       = aws_ecs_service.api.name
}

output "worker_task_definition" {
  description = "Worker task definition ARN"
  value       = aws_ecs_task_definition.worker.arn
}

# CloudWatch
output "cloudwatch_log_group" {
  description = "CloudWatch log group for ECS logs"
  value       = aws_cloudwatch_log_group.ecs.name
}

# EventBridge
output "etl_schedule_rule" {
  description = "EventBridge rule for ETL cron job"
  value       = aws_cloudwatch_event_rule.etl_schedule.name
}

# Secrets Manager
output "secrets_arn" {
  description = "AWS Secrets Manager ARN for app secrets"
  value       = aws_secretsmanager_secret.app_secrets.arn
  sensitive   = true
}

# Instructions
output "next_steps" {
  description = "Next steps after deployment"
  value       = <<-EOT
    
    🎉 Deployment Complete!
    
    API Endpoint: http://${aws_lb.main.dns_name}
    
    Next Steps:
    1. Test health endpoint: curl http://${aws_lb.main.dns_name}/health
    2. View logs: aws logs tail /ecs/kasparro-api --follow
    3. Check ECS tasks: aws ecs list-tasks --cluster ${aws_ecs_cluster.main.name}
    4. View metrics: AWS Console → CloudWatch → Log groups → /ecs/kasparro-api
    5. ETL runs hourly via EventBridge rule: ${aws_cloudwatch_event_rule.etl_schedule.name}
    
    To update the service:
    - Push new image to GHCR
    - Run: aws ecs update-service --cluster ${aws_ecs_cluster.main.name} --service ${aws_ecs_service.api.name} --force-new-deployment
  EOT
}
