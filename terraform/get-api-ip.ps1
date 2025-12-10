# Helper script to get ECS task public IP for API access
# Usage: .\get-api-ip.ps1

$ClusterName = "kasparro-cluster"
$ServiceName = "kasparro-api-service"
$Region = "ap-south-2"

Write-Host "Getting ECS task for $ServiceName..." -ForegroundColor Cyan

# Get task ARN
$TaskArn = (aws ecs list-tasks --cluster $ClusterName --service-name $ServiceName --region $Region --query 'taskArns[0]' --output text).Trim()

if (-not $TaskArn -or $TaskArn -eq "None" -or $TaskArn -eq "") {
    Write-Host "❌ No running tasks found. Service may still be starting..." -ForegroundColor Yellow
    exit 1
}

Write-Host "Task ARN: $TaskArn" -ForegroundColor Gray

# Get network interface ID from task
$NetworkInterfaceId = (aws ecs describe-tasks --cluster $ClusterName --tasks $TaskArn --region $Region --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' --output text).Trim()

if (-not $NetworkInterfaceId -or $NetworkInterfaceId -eq "") {
    Write-Host "❌ Could not find network interface. Task may be starting..." -ForegroundColor Yellow
    exit 1
}

Write-Host "Network Interface: $NetworkInterfaceId" -ForegroundColor Gray

# Get public IP from network interface
$PublicIp = (aws ec2 describe-network-interfaces --network-interface-ids $NetworkInterfaceId --region $Region --query 'NetworkInterfaces[0].Association.PublicIp' --output text).Trim()

if (-not $PublicIp -or $PublicIp -eq "None" -or $PublicIp -eq "") {
    Write-Host "❌ No public IP assigned yet. Wait a moment and try again..." -ForegroundColor Yellow
    exit 1
}

Write-Host "Public IP: $PublicIp" -ForegroundColor Gray

Write-Host "`n✅ API is accessible at:" -ForegroundColor Green
Write-Host "   http://${PublicIp}:8000" -ForegroundColor White

Write-Host "`nQuick tests:" -ForegroundColor Cyan
Write-Host "  Health check:  curl http://${PublicIp}:8000/health" -ForegroundColor Gray
Write-Host "  Get data:      curl http://${PublicIp}:8000/data?limit=5" -ForegroundColor Gray
Write-Host "  Metrics:       curl http://${PublicIp}:8000/metrics" -ForegroundColor Gray

# Save to environment variable for convenience
Write-Host "`nTo save to environment variable:" -ForegroundColor Cyan
Write-Host "  `$env:API_URL = `"http://${PublicIp}:8000`"" -ForegroundColor Gray
