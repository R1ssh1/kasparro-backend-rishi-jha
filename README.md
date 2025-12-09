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

## 🔒 Security

- Environment-based secrets (never commit `.env`)
- API key authentication for protected endpoints (`X-API-Key` header)
- AWS Secrets Manager for production secrets
- Parameterized queries (SQL injection prevention)
- Rate limiting to respect API quotas
- Connection pooling with health checks
- VPC with private subnets for database isolation
