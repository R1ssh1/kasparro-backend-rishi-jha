# Helper script to get ECS task public IP for API access
# Usage: .\get-api-ip.ps1

$ClusterName = "kasparro-cluster"
$ServiceName = "kasparro-api-service"

Write-Host "Getting ECS task for $ServiceName..." -ForegroundColor Cyan

# Get task ARN
$TaskArn = aws ecs list-tasks --cluster $ClusterName --service-name $ServiceName --query 'taskArns[0]' --output text

if (-not $TaskArn -or $TaskArn -eq "None") {
    Write-Host "No running tasks found. Service may still be starting..." -ForegroundColor Yellow
    exit 1
}

Write-Host "Task ARN: $TaskArn" -ForegroundColor Gray

# Get network interface ID from task
$NetworkInterfaceId = aws ecs describe-tasks --cluster $ClusterName --tasks $TaskArn --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' --output text

if (-not $NetworkInterfaceId) {
    Write-Host "Could not find network interface. Task may be starting..." -ForegroundColor Yellow
    exit 1
}

# Get public IP from network interface
$PublicIp = aws ec2 describe-network-interfaces --network-interface-ids $NetworkInterfaceId --query 'NetworkInterfaces[0].Association.PublicIp' --output text

if (-not $PublicIp -or $PublicIp -eq "None") {
    Write-Host "No public IP assigned yet. Wait a moment and try again..." -ForegroundColor Yellow
    exit 1
}

Write-Host "`n✅ API is accessible at:" -ForegroundColor Green
Write-Host "   http://$PublicIp:8000" -ForegroundColor White

Write-Host "`nQuick tests:" -ForegroundColor Cyan
Write-Host "  Health check:  curl http://$PublicIp:8000/health" -ForegroundColor Gray
Write-Host "  Get data:      curl http://$PublicIp:8000/data?limit=5" -ForegroundColor Gray
Write-Host "  Metrics:       curl http://$PublicIp:8000/metrics" -ForegroundColor Gray

# Save to environment variable for convenience
Write-Host "`nTo save to environment variable:" -ForegroundColor Cyan
Write-Host "  `$env:API_URL = `"http://$PublicIp:8000`"" -ForegroundColor Gray
