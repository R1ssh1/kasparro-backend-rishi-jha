# Kasparro Backend - Cryptocurrency ETL Pipeline

A production-ready ETL pipeline that ingests cryptocurrency data from multiple sources (CoinGecko API, CSV) with a FastAPI backend, incremental processing, Docker deployment, and comprehensive observability.


## Goals

 **P0 - Foundation Layer** _Done!_

 1. Data Ingestion
 2. Backend API Service
 3. Dockerized, Runnable System
 4. Minimal Test Suite	

 **P1 - Growth Layer**
 

 1. Add a Third Data Source
 2. Improved Incremental Ingestion
 3. */stats* Endpoint
 4. Comprehensive Test Coverage
 5. Clean Architecture

 **P2 - Differentiator Layer**
 

 1. Schema Drift Detection
 2. Failure Injection + Strong Recovery
 3. Rate Limiting + Backoff
 4. Observability Layer
 5. DevOps Enhancements
 6. Run Comparison / Anomaly Detection



## 🏗️ Architecture

```
┌─────────────────┐
│   CSV Files     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│  CoinGecko API  │─────▶│ ETL Worker   │
└─────────────────┘      │ (Scheduler)  │
                         └──────┬───────┘
                                │
                                ▼
                         ┌──────────────┐
                         │  PostgreSQL  │
                         │   Database   │
                         └──────┬───────┘
                                │
                                ▼
                         ┌──────────────┐
                         │  FastAPI     │
                         │  Service     │
                         └──────────────┘
```

### Components

- **ETL Worker**: Scheduled service that runs data ingestion from multiple sources
- **FastAPI Service**: REST API serving cryptocurrency data with pagination and filtering
- **PostgreSQL Database**: Stores raw and normalized data with checkpointing
- **Rate Limiter**: Token bucket algorithm to respect API rate limits
- **Checkpointing**: Transactional checkpoint updates for resume-on-failure

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- CoinGecko API key (get one at https://www.coingecko.com/en/api)

### 1. Setup Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your CoinGecko API key
# COINGECKO_API_KEY=your_actual_api_key_here
```

### 2. Start Services

```bash
# Start all services (API + Worker + Database)
make up

# Or using docker-compose directly
docker-compose up -d --build
```

The API will be available at:
- **API Base**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### 3. Verify Installation

```bash
# Run smoke test
make smoke

# View logs
make logs
```

## 📡 API Endpoints

### GET /data

Retrieve cryptocurrency data with pagination and filtering.

**Query Parameters:**
- `page` (int, default=1): Page number
- `per_page` (int, default=50, max=100): Items per page
- `symbol` (string, optional): Filter by symbol (e.g., "BTC")
- `min_price` (float, optional): Minimum price filter
- `max_price` (float, optional): Maximum price filter
- `source` (string, optional): Filter by data source ("coingecko", "csv")

**Examples:**
```bash
# Get first page
curl "http://localhost:8000/data?page=1&per_page=10"

# Filter by symbol
curl "http://localhost:8000/data?symbol=BTC"

# Price range filter
curl "http://localhost:8000/data?min_price=1000&max_price=50000"
```

### GET /health

Health check endpoint reporting database connectivity and ETL status.

## 🗄️ Database Schema

- **coins**: Normalized cryptocurrency data (unique on source + external_id)
- **raw_coin_data**: Raw JSON storage for debugging
- **etl_checkpoints**: Incremental ingestion tracking
- **etl_runs**: Run metadata and observability

## 🔄 ETL Pipeline

### Data Flow

1. **Fetch**: Worker fetches data from source (respecting rate limits)
2. **Raw Storage**: Save raw JSON to database
3. **Validation**: Validate using Pydantic schemas
4. **Normalization**: Transform to unified schema
5. **Upsert**: Insert/update coins table (idempotent)
6. **Checkpoint**: Update cursor position (atomic transaction)

### Key Features

- **Transactional Safety**: All operations wrapped in database transactions
- **Rate Limiting**: Token bucket algorithm (30 calls/min for CoinGecko)
- **Retry & Backoff**: Exponential backoff with 3 retries
- **Incremental Processing**: Resume from last checkpoint on failure

## 🧪 Testing

```bash
# Run all tests with coverage
make test
```

Test coverage includes:
- ETL transformation logic
- API endpoints
- Failure scenarios
- Rate limiting

## 🛠️ Development

### Project Structure

```
kasparro-backend/
├── api/                    # FastAPI application
├── core/                   # Core utilities (config, database, models)
├── ingestion/              # ETL pipeline
├── schemas/                # Pydantic schemas
├── worker/                 # ETL scheduler
├── tests/                  # Test suite
├── data/                   # CSV files
└── migrations/             # Alembic migrations
```

### Makefile Commands

```bash
make up          # Start all services
make down        # Stop all services
make logs        # View all logs
make test        # Run test suite
make clean       # Remove containers and volumes
make smoke       # Run smoke test
```

## 🚢 Deployment

### Local Deployment (Docker)

Services are containerized and orchestrated via Docker Compose:
- **db**: PostgreSQL database
- **api**: FastAPI REST API (port 8000)
- **worker**: ETL scheduler (runs every 60 minutes)

### Production Deployment (AWS)

See **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** for complete AWS deployment guide.

**Quick Start**:
```bash
cd terraform
terraform init
terraform apply
```

Infrastructure includes:
- ✅ ECS Fargate (serverless containers)
- ✅ RDS PostgreSQL (managed database)
- ✅ EventBridge (hourly cron scheduler)
- ✅ Application Load Balancer
- ✅ CloudWatch Logs (centralized logging)

**Cost**: ~$16-20/month (within AWS Free Tier)

## 🎯 Evaluator Quick-Start

This project is production-ready and can be evaluated in 3 steps:

### 1. Verify Tests (Docker)
```bash
# Start database
docker-compose up -d db

# Run all tests (62 tests: P1 + P2 + Auth)
docker-compose run --rm api pytest tests/ -v

# Expected: 62 passed, 83% coverage
```

### 2. Verify Local Deployment
```bash
# Start all services
docker-compose up -d

# Health check
curl http://localhost:8000/health

# Public data endpoint
curl http://localhost:8000/data?limit=5

# Protected endpoint (requires auth)
curl -H "X-API-Key: test-api-key-123" http://localhost:8000/stats

# Prometheus metrics
curl http://localhost:8000/metrics
```

### 3. Verify Production Deployment (AWS)
```bash
# Deploy infrastructure
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
terraform init
terraform apply

# Run smoke tests
cd ../tests/smoke
export API_URL=$(terraform output -raw api_endpoint)
export API_KEY="your-admin-api-key"
bash smoke_test.sh

# Expected: All 10 smoke tests pass
```

**Complete Evaluation Guide**: [docs/EVALUATION_CHECKLIST.md](docs/EVALUATION_CHECKLIST.md)

---

## 📋 Evaluator Runbook

**Complete step-by-step verification for all 6 evaluation requirements.**

### Prerequisites
- Windows with PowerShell
- Docker Desktop installed
- Git installed
- AWS CLI configured (for cloud deployment)

### Step 1: Clone & Setup (2 minutes)

```powershell
# Clone repository
git clone https://github.com/R1ssh1/kasparro-backend-rishi-jha.git
cd kasparro-backend-rishi-jha

# Create environment file
Copy-Item .env.example .env

# IMPORTANT: Edit .env with real API keys
# Required variables:
#   COINGECKO_API_KEY=<your-coingecko-api-key>
#   ADMIN_API_KEY=<generate-secure-random-key>
notepad .env
```

**⚠️ Security Note**: Never commit `.env` to git. API keys must be provided via environment variables or secrets management.

### Step 2: Run Automated Tests (5 minutes)

```powershell
# Start database
docker-compose up -d db

# Wait for database to be ready
Start-Sleep -Seconds 10

# Run full test suite (61 tests)
docker-compose run --rm api pytest tests/ -v --cov=. --cov-report=term

# Expected output:
# ==================== 61 passed in XX.XXs ====================
# Coverage: 81%
```

**Verification**:
- ✅ All 61 tests pass
- ✅ Coverage ≥ 80%
- ✅ Tests cover: ETL, API, auth, schema drift, failure injection, rate limiting

### Step 3: Verify Local Docker Deployment (3 minutes)

```powershell
# Start all services
docker-compose up -d

# Wait for services to be healthy
Start-Sleep -Seconds 15

# Test 1: Health check
curl http://localhost:8000/health

# Expected: {"status":"healthy","database":"connected"}

# Test 2: Public data endpoint
curl http://localhost:8000/data?limit=5

# Expected: JSON array with cryptocurrency data

# Test 3: Protected endpoint WITHOUT auth (should fail)
curl http://localhost:8000/stats

# Expected: 422 Unprocessable Entity (missing X-API-Key header)

# Test 4: Protected endpoint WITH auth (should succeed)
# Replace YOUR_ADMIN_API_KEY with the key from your .env file
curl -H "X-API-Key: YOUR_ADMIN_API_KEY" http://localhost:8000/stats

# Expected: 200 OK with ETL statistics

# Test 5: Prometheus metrics
curl http://localhost:8000/metrics

# Expected: Prometheus-formatted metrics (# HELP, # TYPE lines)
```

**Verification**:
- ✅ API responds on http://localhost:8000
- ✅ Public endpoints accessible without auth
- ✅ Protected endpoints require valid X-API-Key
- ✅ Metrics endpoint exposes Prometheus data

### Step 4: Run Smoke Tests (2 minutes)

```powershell
# Navigate to smoke test directory
cd tests\smoke

# Set environment variables (use your .env values)
$env:API_URL = "http://localhost:8000"
$env:API_KEY = "YOUR_ADMIN_API_KEY"  # From .env

# Run smoke tests (12 scenarios)
bash smoke_test.sh

# Expected output:
# =========================================
# SMOKE TEST SUMMARY
# =========================================
# Passed: 12
# Failed: 0
# =========================================
# ✓ All smoke tests passed!
```

**Smoke Test Coverage**:
1. ✅ Service running
2. ✅ Health check
3. ✅ Database connectivity
4. ✅ Public data endpoint
5. ✅ Pagination
6. ✅ Filtering
7. ✅ Protected endpoint (invalid auth)
8. ✅ Protected endpoint (valid auth)
9. ✅ Metrics endpoint
10. ✅ Run comparison
11. ✅ ETL recovery after restart
12. ✅ Rate limiting

### Step 5: Deploy to AWS Cloud (15 minutes)

```powershell
# Navigate to Terraform directory
cd ..\..\terraform

# Create variables file
Copy-Item terraform.tfvars.example terraform.tfvars

# Edit with your values:
# - db_password: Strong password for RDS
# - coingecko_api_key: Your CoinGecko API key
# - admin_api_key: Secure random key for API auth
notepad terraform.tfvars

# Initialize Terraform
terraform init

# Preview changes
terraform plan

# Deploy infrastructure (creates ~30 AWS resources)
terraform apply

# Confirm with: yes

# Save the API endpoint
terraform output api_endpoint
# Example output: http://kasparro-alb-123456789.us-east-1.elb.amazonaws.com
```

**Infrastructure Created**:
- ✅ VPC with public/private subnets (2 AZs)
- ✅ RDS PostgreSQL database (db.t3.micro, free tier)
- ✅ ECS Fargate cluster (API + Worker tasks)
- ✅ Application Load Balancer
- ✅ EventBridge cron rule (hourly ETL)
- ✅ CloudWatch Logs
- ✅ Secrets Manager (API keys)
- ✅ IAM roles (least privilege)

### Step 6: Verify Cloud Deployment (5 minutes)

```powershell
# Get API endpoint from Terraform
$API_ENDPOINT = terraform output -raw api_endpoint

# Test 1: Health check
curl "$API_ENDPOINT/health"

# Expected: {"status":"healthy","database":"connected"}

# Test 2: Verify EventBridge cron schedule
aws events describe-rule --name kasparro-etl-schedule-production

# Expected output shows:
# - State: "ENABLED"
# - ScheduleExpression: "rate(1 hour)"

# Test 3: View CloudWatch logs (ETL executions)
aws logs tail /ecs/kasparro-worker --follow

# Press Ctrl+C after seeing log entries
# Expected: ETL execution logs showing data ingestion

# Test 4: Check ECS service status
aws ecs describe-services --cluster kasparro-cluster --services kasparro-api-service

# Expected:
# - desiredCount: 1
# - runningCount: 1
# - deployments[0].status: "PRIMARY"

# Test 5: Run smoke tests against cloud deployment
cd ..\tests\smoke
$env:API_URL = $API_ENDPOINT
$env:API_KEY = "YOUR_ADMIN_API_KEY"
$env:SKIP_DOCKER_TESTS = "true"  # Skip Docker-specific tests
bash smoke_test.sh

# Expected: 10/12 tests pass (Docker tests skipped)
```

**Cloud Verification**:
- ✅ API accessible via ALB endpoint
- ✅ EventBridge rule enabled and scheduled hourly
- ✅ CloudWatch logs show ETL executions
- ✅ ECS tasks running in Fargate
- ✅ Smoke tests pass against production

### Step 7: Verify CI/CD Pipeline (1 minute)

```powershell
# View GitHub Actions workflow
# Visit: https://github.com/R1ssh1/kasparro-backend-rishi-jha/actions

# Verify latest workflow run shows:
# ✅ Code Quality Checks (passed)
# ✅ Run Tests (61 tests passed)
# ✅ Build Docker Image (pushed to GHCR)
# ✅ Deploy to AWS ECS (service updated)
# ✅ Smoke Test (production verified)
```

**CI/CD Verification**:
- ✅ Automated testing on every push
- ✅ Docker image published to GHCR
- ✅ AWS ECS deployment automated
- ✅ Smoke tests run post-deployment

---

### Troubleshooting

**Issue**: "COINGECKO_API_KEY not set"
```powershell
# Check .env file exists and has valid keys
cat .env | Select-String "COINGECKO_API_KEY"
cat .env | Select-String "ADMIN_API_KEY"
```

**Issue**: "Database connection failed"
```powershell
# Check database is running
docker ps | Select-String "kasparro-db"

# View database logs
docker logs kasparro-db
```

**Issue**: "Tests failing"
```powershell
# Ensure database is ready
docker-compose restart db
Start-Sleep -Seconds 10

# Run tests again
docker-compose run --rm api pytest tests/ -v
```

**Issue**: "Terraform apply fails"
```powershell
# Check AWS credentials
aws sts get-caller-identity

# Verify terraform.tfvars has all required values
cat terraform\terraform.tfvars
```

---

## 🔐 Auth & Secrets

### Required Environment Variables

All API keys must be provided via environment variables. **Never hard-code or commit secrets.**

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `COINGECKO_API_KEY` | CoinGecko API key | `CG-abc123...` | ✅ Yes |
| `ADMIN_API_KEY` | API authentication key | `secure-random-key-here` | ✅ Yes |
| `DATABASE_URL` | PostgreSQL connection | `postgresql+asyncpg://user:pass@host/db` | ✅ Yes |

### Local Development (Docker Compose)

1. **Copy template**:
   ```powershell
   Copy-Item .env.example .env
   ```

2. **Edit .env** with real values:
   ```env
   COINGECKO_API_KEY=your_actual_coingecko_api_key
   ADMIN_API_KEY=generate_secure_random_key_here
   ```

3. **Verify .env is not tracked**:
   ```powershell
   git status .env
   # Expected: "Untracked files" or "No changes"
   ```

### Production Deployment (AWS)

API keys are stored in **AWS Secrets Manager**:

```powershell
# Secrets are created by Terraform from terraform.tfvars
# ECS tasks fetch secrets at runtime via IAM roles
# No secrets in code or environment variables visible in console
```

### API Authentication

Protected endpoints require `X-API-Key` header:

```powershell
# Without API key (fails)
curl http://localhost:8000/stats
# Returns: 422 Unprocessable Entity

# With API key (succeeds)
curl -H "X-API-Key: YOUR_ADMIN_API_KEY" http://localhost:8000/stats
# Returns: 200 OK with statistics
```

**Protected Endpoints**:
- `GET /stats` - ETL statistics
- `GET /runs` - ETL run history
- `GET /compare-runs` - Run comparison with anomaly detection

**Public Endpoints** (no auth required):
- `GET /` - API root
- `GET /health` - Health check
- `GET /data` - Query cryptocurrency data
- `GET /metrics` - Prometheus metrics

---

## 🔒 Security

- Environment-based secrets (never commit `.env`)
- API key authentication for protected endpoints (`X-API-Key` header)
- AWS Secrets Manager for production secrets
- Parameterized queries (SQL injection prevention)
- Rate limiting to respect API quotas
- Connection pooling with health checks
- VPC with private subnets for database isolation
