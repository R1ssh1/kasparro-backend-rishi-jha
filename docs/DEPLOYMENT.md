# Deployment Guide

This guide walks through deploying the Kasparro Backend to AWS using Terraform.

## Table of Contents
- [Prerequisites](#prerequisites)
- [AWS Setup](#aws-setup)
- [Terraform Deployment](#terraform-deployment)
- [Post-Deployment Verification](#post-deployment-verification)
- [GitHub Actions Setup](#github-actions-setup)
- [Troubleshooting](#troubleshooting)
- [Cost Estimate](#cost-estimate)

## Prerequisites

Before deploying, ensure you have:

1. **AWS Account** with free tier access
2. **Terraform** installed (version 1.0+)
   ```powershell
   terraform --version
   ```
3. **AWS CLI** installed and configured
   ```powershell
   aws --version
   aws configure  # Set up credentials
   ```
4. **Docker** installed (for local testing)
5. **GitHub Account** with repository access

## AWS Setup

### 1. Create AWS IAM User

Create an IAM user with the following permissions:
- ECS (Full Access)
- RDS (Full Access)
- VPC (Full Access)
- CloudWatch Logs (Full Access)
- Secrets Manager (Full Access)
- EventBridge (Full Access)
- IAM (Limited - for role creation)

Save the **Access Key ID** and **Secret Access Key**.

### 2. Configure AWS CLI

```powershell
aws configure
# AWS Access Key ID: <your-access-key>
# AWS Secret Access Key: <your-secret-key>
# Default region: us-east-1
# Default output format: json
```

Verify configuration:
```powershell
aws sts get-caller-identity
```

## Terraform Deployment

### 1. Navigate to Terraform Directory

```powershell
cd terraform
```

### 2. Create Terraform Variables File

Copy the example file:
```powershell
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with real values:
```hcl
aws_region         = "us-east-1"
environment        = "production"
db_password        = "YOUR_SECURE_DB_PASSWORD_HERE"  # Use strong password
coingecko_api_key  = "CG-chKdRQHPTHTked1weQVLEzUM"  # Your API key
admin_api_key      = "YOUR_ADMIN_API_KEY_HERE"       # Generate secure key
docker_image       = "ghcr.io/r1ssh1/kasparro-backend-rishi-jha:latest"
```

**Security Note**: Never commit `terraform.tfvars` to version control.

### 3. Initialize Terraform

```powershell
terraform init
```

This downloads required AWS provider plugins.

### 4. Preview Changes

```powershell
terraform plan
```

Review the resources that will be created:
- VPC with public/private subnets
- RDS PostgreSQL database
- ECS Fargate cluster
- Application Load Balancer
- EventBridge cron scheduler
- CloudWatch log groups
- IAM roles and security groups

### 5. Apply Infrastructure

```powershell
terraform apply
```

Type `yes` to confirm. Deployment takes ~10-15 minutes.

### 6. Save Outputs

After successful deployment, Terraform outputs important information:

```powershell
terraform output
```

Save these values:
- **api_endpoint**: Your API URL (e.g., `http://kasparro-alb-123456789.us-east-1.elb.amazonaws.com`)
- **ecs_cluster_name**: ECS cluster name
- **cloudwatch_log_group**: Log group path

## Post-Deployment Verification

### 1. Health Check

```powershell
$API_ENDPOINT = terraform output -raw api_endpoint
curl "$API_ENDPOINT/health"
```

Expected response:
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 2. View Logs

```powershell
aws logs tail /ecs/kasparro-api --follow
```

### 3. Check ECS Tasks

```powershell
aws ecs list-tasks --cluster kasparro-cluster
aws ecs describe-tasks --cluster kasparro-cluster --tasks <task-arn>
```

### 4. Verify EventBridge Rule

```powershell
aws events list-rules --name-prefix kasparro
```

### 5. Run Smoke Tests

```powershell
cd ../tests/smoke
$env:API_URL = terraform output -raw api_endpoint
$env:API_KEY = "YOUR_ADMIN_API_KEY"
bash smoke_test.sh
```

## GitHub Actions Setup

For automated deployment on push to `main`:

### 1. Add GitHub Secrets

Go to your repository → Settings → Secrets and variables → Actions

Add these secrets:
- `AWS_ACCESS_KEY_ID`: Your IAM user access key
- `AWS_SECRET_ACCESS_KEY`: Your IAM user secret key
- `AWS_REGION`: `us-east-1` (or your chosen region)

### 2. Push to Main Branch

```powershell
git add .
git commit -m "Deploy to production"
git push origin main
```

GitHub Actions will automatically:
1. Run tests
2. Build Docker image
3. Push to GitHub Container Registry
4. Deploy to AWS ECS

### 3. Monitor Deployment

Check the Actions tab in GitHub to see deployment progress.

## Troubleshooting

### Database Connection Issues

**Symptom**: Health check shows `database: "disconnected"`

**Solution**:
1. Check RDS instance status:
   ```powershell
   aws rds describe-db-instances --db-instance-identifier kasparro-db-production
   ```
2. Verify security group allows ECS task access (port 5432)
3. Check ECS task environment variables:
   ```powershell
   aws ecs describe-task-definition --task-definition kasparro-api-task
   ```

### ECS Task Not Starting

**Symptom**: ECS service shows 0 running tasks

**Solution**:
1. Check task stopped reason:
   ```powershell
   aws ecs describe-tasks --cluster kasparro-cluster --tasks <task-arn>
   ```
2. Common causes:
   - Image pull error: Verify Docker image exists in GHCR
   - Resource limits: Increase CPU/memory in `variables.tf`
   - Secrets error: Check Secrets Manager has correct values

### EventBridge Not Triggering

**Symptom**: Worker task doesn't run hourly

**Solution**:
1. Check EventBridge rule:
   ```powershell
   aws events describe-rule --name kasparro-etl-schedule-production
   ```
2. Verify rule is enabled and target is correct
3. Check CloudWatch logs for worker executions

### High Costs

**Symptom**: AWS bill higher than expected

**Solution**:
1. Check ALB data transfer (largest cost outside free tier)
2. Consider using Application Load Balancer only during testing
3. Stop environment when not in use:
   ```powershell
   aws ecs update-service --cluster kasparro-cluster --service kasparro-api-service --desired-count 0
   ```

## Cost Estimate

**Within AWS Free Tier (first 12 months):**
- **RDS db.t3.micro**: $0 (750 hours/month free)
- **ECS Fargate**: $0 (Fargate Spot eligible for free tier)
- **ALB**: ~$16/month (not free tier eligible)
- **Data Transfer**: $0 (1GB free)
- **CloudWatch Logs**: $0 (5GB free)

**Total Estimated Cost**: $16-20/month

**After Free Tier:**
- **RDS db.t3.micro**: ~$15-25/month
- **ECS Fargate**: ~$10-30/month (depends on uptime)
- **ALB**: ~$16/month
- **Total**: ~$41-71/month

**Cost Optimization Tips:**
1. Use Fargate Spot for non-critical workloads (70% discount)
2. Enable RDS auto-pause for development environments
3. Use CloudWatch Logs retention (30 days) to limit storage
4. Scale down during off-hours using EventBridge schedules

## Cleanup

To destroy all resources:

```powershell
cd terraform
terraform destroy
```

Type `yes` to confirm. This removes all AWS resources and stops billing.

**Warning**: This deletes the RDS database permanently. Export data first if needed.

## Next Steps

- [ ] Set up CloudWatch alarms for errors
- [ ] Configure Route 53 for custom domain
- [ ] Enable HTTPS with ACM certificate
- [ ] Set up RDS automated backups
- [ ] Implement blue-green deployment
- [ ] Add WAF for security
