# API Access Instructions
output "api_access_instructions" {
  description = "How to access the API after deployment"
  value       = <<-EOT
    The API is deployed without a load balancer to minimize costs.
    To access the API, get the ECS task's public IP:
    
    1. List tasks:
       aws ecs list-tasks --cluster ${aws_ecs_cluster.main.name} --service-name ${aws_ecs_service.api.name}
    
    2. Get task details:
       aws ecs describe-tasks --cluster ${aws_ecs_cluster.main.name} --tasks <TASK_ARN>
    
    3. Extract public IP from task network interface
    
    4. Access API at: http://<PUBLIC_IP>:8000/health
  EOT
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
    
    ⚠️  Note: Deployed without ALB to save costs (~$16/month)
    
    Get API Public IP:
    1. aws ecs list-tasks --cluster ${aws_ecs_cluster.main.name} --service-name ${aws_ecs_service.api.name}
    2. aws ecs describe-tasks --cluster ${aws_ecs_cluster.main.name} --tasks <TASK_ARN>
    3. Find public IP in network interface details
    
    Next Steps:
    1. Test health endpoint: curl http://<PUBLIC_IP>:8000/health
    2. View logs: aws logs tail /ecs/kasparro-api --follow
    3. Check ECS tasks: aws ecs list-tasks --cluster ${aws_ecs_cluster.main.name}
    4. View metrics: AWS Console → CloudWatch → Log groups → /ecs/kasparro-api
    5. ETL runs hourly via EventBridge rule: ${aws_cloudwatch_event_rule.etl_schedule.name}
    
    To update the service:
    - Push new image to GHCR
    - Run: aws ecs update-service --cluster ${aws_ecs_cluster.main.name} --service ${aws_ecs_service.api.name} --force-new-deployment
  EOT
}
