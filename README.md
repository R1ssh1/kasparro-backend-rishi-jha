# Kasparro Backend - Cryptocurrency ETL Pipeline

A production-ready, cloud-deployed ETL pipeline that ingests cryptocurrency data from multiple sources with advanced features including schema drift detection, failure recovery, rate limiting, and comprehensive observability.

## 🎯 Project Status

**All Requirements Complete: P0 + P1 + P2** ✅

- **61/61 tests passing** (100% pass rate)
- **83% code coverage**
- **3 data sources** operational (CoinGecko API, RSS feed, CSV)
- **Cloud deployed** on AWS ECS (ap-south-2)
- **CI/CD pipeline** active via GitHub Actions
- **Production API**: Get current IP with `terraform/get-api-ip.ps1`

---

## 📋 Requirements Checklist

### ✅ P0 — Foundation Layer (COMPLETE)

- **P0.1** ✅ Data Ingestion (CoinGecko API + CSV)
- **P0.2** ✅ Backend API Service (`/data`, `/health`)
- **P0.3** ✅ Dockerized System (`make up`, `make down`, `make test`)
- **P0.4** ✅ Minimal Test Suite

### ✅ P1 — Growth Layer (COMPLETE)

- **P1.1** ✅ Third Data Source (RSS feed)
- **P1.2** ✅ Improved Incremental Ingestion (checkpoints, resume-on-failure, idempotent)
- **P1.3** ✅ `/stats` Endpoint (ETL summaries)
- **P1.4** ✅ Comprehensive Test Coverage (61 tests)
- **P1.5** ✅ Clean Architecture (organized codebase)

### ✅ P2 — Differentiator Layer (COMPLETE)

- **P2.1** ✅ Schema Drift Detection (fuzzy matching, confidence scoring)
- **P2.2** ✅ Failure Injection + Strong Recovery
- **P2.3** ✅ Rate Limiting + Backoff (token bucket algorithm)
- **P2.4** ✅ Observability Layer (Prometheus `/metrics`, structured logs)
- **P2.5** ✅ DevOps Enhancements (GitHub Actions CI/CD, Docker publishing)
- **P2.6** ✅ Run Comparison / Anomaly Detection (`/runs`, `/compare-runs`)

### ✅ Final Evaluation Requirements (COMPLETE)

- **API Authentication** ✅ CoinGecko API key securely managed via environment variables
- **Docker Image** ✅ Available at `ghcr.io/r1ssh1/kasparro-backend-rishi-jha:latest`
- **Cloud Deployment** ✅ AWS ECS Fargate in ap-south-2 region
- **Scheduled ETL** ✅ EventBridge cron (hourly)
- **Automated Tests** ✅ 61 tests covering all scenarios
- **Smoke Test** ✅ End-to-end validation via CI/CD

---

## 🏗️ Architecture

```
┌─────────────────┐
│   CSV Files     │
└────────┬────────┘
         │
┌─────────────────┐      ┌──────────────┐
│  CoinGecko API  │─────▶│ ETL Worker   │──┐
└─────────────────┘      │ (Scheduler)  │  │
         │               └──────────────┘  │
┌─────────────────┐             │         │
│   RSS Feed      │─────────────┘         │
└─────────────────┘                       │
                                          ▼
                                   ┌──────────────┐
                                   │  PostgreSQL  │
                                   │   Database   │
                                   └──────┬───────┘
                                          │
                                          ▼
                                   ┌──────────────┐
                                   │  FastAPI     │◄──── /data
                                   │  Service     │◄──── /health
                                   │              │◄──── /stats
                                   │              │◄──── /metrics
                                   │              │◄──── /runs
                                   └──────────────┘
```

### Components

- **3 Data Sources**: CoinGecko API (100 cryptos), RSS feed (30 articles), CSV (10 records)
- **ETL Worker**: Scheduled service with hourly cron execution
- **FastAPI Service**: REST API with pagination, filtering, and observability
- **PostgreSQL Database**: Async SQLAlchemy 2.0 with Alembic migrations
- **Rate Limiting**: Token bucket algorithm with exponential backoff
- **Schema Drift Detection**: Fuzzy matching with confidence scoring
- **Failure Recovery**: Checkpoint-based resume with idempotent writes
- **Observability**: Prometheus metrics + structured JSON logs

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- CoinGecko API key: https://www.coingecko.com/en/api
- Admin API key for protected endpoints

### 1. Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials:
# COINGECKO_API_KEY=your_coingecko_key
# ADMIN_API_KEY=your_admin_key
# DATABASE_URL=postgresql+asyncpg://kasparro:kasparro@db:5432/kasparro
```

### 2. Start Services

```bash
# Start all services (API + Worker + Database)
make up

# Or using docker-compose
docker-compose up -d --build
```

**Service Endpoints:**
- API Base: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health
- Dashboard: http://localhost:8000/

### 3. Run Tests

```bash
# Run full test suite
make test

# Run with coverage
docker-compose run --rm api pytest --cov=. --cov-report=term-missing
```

### 4. View Logs

```bash
# All services
make logs

# API only
make logs-api

# Worker only
make logs-worker
```

### 5. Stop Services

```bash
make down
```

---

## 📡 API Endpoints

### Public Endpoints

#### `GET /`
Interactive dashboard with cryptocurrency data visualization.

#### `GET /health`
Health check with database connectivity and ETL status.

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "database_connected": true,
  "etl_status": {
    "coingecko": {"status": "success", "records_processed": 100},
    "csv": {"status": "success", "records_processed": 10},
    "rss_feed": {"status": "success", "records_processed": 30}
  },
  "timestamp": "2025-12-10T09:00:00Z"
}
```

#### `GET /data`
Retrieve cryptocurrency data with pagination and filtering.

**Parameters:**
- `source`: Filter by data source (`coingecko`, `csv`, `rss_feed`)
- `symbol`: Filter by symbol (e.g., `BTC`, `ETH`)
- `name`: Filter by name (e.g., `Bitcoin`)
- `limit`: Results per page (default: 10, max: 100)
- `offset`: Pagination offset (default: 0)

```bash
# Get top 10 cryptocurrencies
curl "http://localhost:8000/data?source=coingecko&limit=10"

# Filter by symbol
curl "http://localhost:8000/data?symbol=BTC"

# Get news articles
curl "http://localhost:8000/data?source=rss_feed"
```

**Response:**
```json
{
  "request_id": "abc-123",
  "api_latency_ms": 15.3,
  "data": [
    {
      "id": 1,
      "source": "coingecko",
      "symbol": "BTC",
      "name": "Bitcoin",
      "current_price": 43250.50,
      "market_cap": 845000000000,
      "volume_24h": 28500000000,
      "price_change_24h": 2.35,
      "last_updated": "2025-12-10T09:00:00Z"
    }
  ],
  "pagination": {
    "limit": 10,
    "offset": 0,
    "total_items": 140,
    "total_pages": 14
  }
}
```

#### `GET /metrics`
Prometheus-format metrics for monitoring.

```bash
curl http://localhost:8000/metrics
```

**Metrics Included:**
- `etl_runs_total` - Total ETL runs by source and status
- `etl_records_processed_total` - Records processed by source
- `etl_duration_seconds` - ETL execution duration
- `api_requests_total` - API request count by endpoint and status
- `api_request_duration_seconds` - API latency histogram
- `data_staleness_seconds` - Time since last ETL success

### Protected Endpoints (Require `X-API-Key` header)

#### `GET /stats`
ETL pipeline statistics and summaries.

**Parameters:**
- `source`: Filter by data source
- `limit`: Number of recent runs (default: 10, max: 100)

```bash
curl -H "X-API-Key: your_admin_key" \
  "http://localhost:8000/stats?limit=5"
```

**Response:**
```json
{
  "request_id": "xyz-789",
  "api_latency_ms": 8.2,
  "summary": {
    "coingecko": {
      "total_runs": 25,
      "successful_runs": 24,
      "failed_runs": 1,
      "total_records_processed": 2400,
      "average_duration_seconds": 3.5
    }
  },
  "recent_runs": [
    {
      "run_id": "abc-123",
      "source": "coingecko",
      "status": "success",
      "records_processed": 100,
      "duration_seconds": 3.2,
      "started_at": "2025-12-10T09:00:00Z",
      "completed_at": "2025-12-10T09:00:03Z"
    }
  ]
}
```

#### `GET /runs`
List ETL run history.

```bash
curl -H "X-API-Key: your_admin_key" \
  "http://localhost:8000/runs?limit=10"
```

#### `POST /compare-runs`
Compare two ETL runs for anomaly detection.

```bash
curl -X POST -H "X-API-Key: your_admin_key" \
  -H "Content-Type: application/json" \
  -d '{"run_id_1": "abc-123", "run_id_2": "def-456"}' \
  http://localhost:8000/compare-runs
```

**Detects:**
- Record count spikes (>50% change)
- Duration anomalies (>100% change)
- Success/failure transitions
- Data source changes
- Unexpected error patterns

---

## 🗂️ Project Structure

```
kasparro-backend/
├── api/                      # FastAPI application
│   ├── main.py              # App initialization
│   ├── auth.py              # API key authentication
│   └── routers/
│       └── crypto.py        # All API endpoints
├── core/                     # Core utilities
│   ├── config.py            # Settings management
│   ├── database.py          # DB connection & session
│   ├── models.py            # SQLAlchemy ORM models
│   ├── schema_drift.py      # Drift detection logic
│   ├── failure_injector.py  # Failure testing framework
│   └── prometheus.py        # Metrics collection
├── ingestion/               # ETL pipeline
│   ├── base.py              # Base ingestion class
│   ├── coingecko.py         # CoinGecko API ingestion
│   ├── csv_loader.py        # CSV file ingestion
│   ├── rss_feed.py          # RSS feed ingestion
│   └── rate_limiter.py      # Rate limiting logic
├── schemas/                 # Pydantic schemas
│   ├── crypto.py            # API response models
│   └── ingestion.py         # ETL data models
├── worker/                  # Background job scheduler
│   └── scheduler.py         # Cron-based ETL execution
├── tests/                   # Test suite (61 tests)
│   ├── test_api/            # API endpoint tests
│   ├── test_ingestion/      # ETL pipeline tests
│   ├── test_schemas/        # Schema validation tests
│   ├── test_failure_*.py    # Failure recovery tests
│   ├── test_schema_drift.py # Drift detection tests
│   ├── test_rate_limiting.py# Rate limiter tests
│   ├── test_p2_endpoints.py # P2 endpoint tests
│   └── smoke/               # End-to-end smoke tests
├── migrations/              # Alembic database migrations
├── static/                  # Dashboard HTML
├── terraform/               # AWS infrastructure code
├── .github/workflows/       # CI/CD pipeline
├── docker-compose.yml       # Local development
├── Dockerfile               # Production image
├── Makefile                 # Common commands
└── README.md               # This file
```

---

## ☁️ Cloud Deployment (AWS)

### Infrastructure

**Deployed on AWS (ap-south-2 - Hyderabad):**
- **Compute**: ECS Fargate (256 CPU, 512MB RAM)
- **Database**: RDS PostgreSQL 15.10 (db.t3.micro, 20GB)
- **Networking**: VPC with public subnets (cost-optimized, no ALB)
- **Scheduling**: EventBridge (hourly cron)
- **Secrets**: AWS Secrets Manager
- **Logging**: CloudWatch Logs (30-day retention)
- **Container Registry**: GitHub Container Registry (GHCR)

### Deployment Process

```bash
# 1. Deploy infrastructure
cd terraform
terraform init
terraform apply

# 2. Build and push Docker image (or use GitHub Actions)
docker build -t ghcr.io/r1ssh1/kasparro-backend-rishi-jha:latest .
docker push ghcr.io/r1ssh1/kasparro-backend-rishi-jha:latest

# 3. Update ECS service
aws ecs update-service \
  --cluster kasparro-cluster \
  --service kasparro-api-service \
  --force-new-deployment \
  --region ap-south-2

# 4. Get current API IP address
./get-api-ip.ps1
```

### Production API

**Get Current IP**: IP changes with each deployment. Run:

```bash
cd terraform
./get-api-ip.ps1
```

### Monitoring

**CloudWatch Logs:**
```bash
# API logs
aws logs tail /ecs/kasparro-api --follow --region ap-south-2

# Worker logs
aws logs tail /ecs/kasparro-worker --follow --region ap-south-2
```

**Metrics:**
- Access Prometheus metrics at: `http://<current-ip>:8000/metrics`
- View in CloudWatch Metrics Explorer

---

## 🧪 Testing

### Test Coverage

**61 tests, 83% code coverage:**

- **API Tests** (27 tests): Endpoints, authentication, pagination, filtering
- **Ingestion Tests** (18 tests): ETL logic, incremental processing, checkpointing
- **Schema Tests** (10 tests): Validation, type coercion, normalization
- **Failure Tests** (11 tests): Recovery, injection, resilience
- **Schema Drift Tests** (6 tests): Detection, fuzzy matching, confidence scoring
- **Rate Limiting Tests** (3 tests): Token bucket, backoff, throttling
- **P2 Endpoint Tests** (2 tests): Metrics, anomaly detection

### Run Tests

```bash
# Local (requires running services)
make test

# In Docker
docker-compose run --rm api pytest -v

# With coverage report
docker-compose run --rm api pytest --cov=. --cov-report=html

# Specific test file
docker-compose run --rm api pytest tests/test_api/test_endpoints.py -v

# Smoke test (end-to-end)
make smoke
```

### Test Configuration

Tests use isolated database with automatic cleanup:
- Separate test database created per session
- Fixtures in `tests/conftest.py`
- Async test support via `pytest-asyncio`
- Mocking via `pytest-mock`

---

## 🔒 Security

### API Key Management

**Environment Variables:**
```bash
# CoinGecko API authentication
COINGECKO_API_KEY=demo_key_xxxxx

# Admin API key for protected endpoints
ADMIN_API_KEY=your_secure_admin_key
```

**In Production:**
- Stored in AWS Secrets Manager
- Injected as environment variables in ECS task definitions
- Never committed to version control (.env in .gitignore)

### Authentication

Protected endpoints require `X-API-Key` header:

```bash
curl -H "X-API-Key: your_admin_key" http://localhost:8000/stats
```

Invalid keys return 401 Unauthorized.

---

## 📊 Observability

### Structured Logging

All logs output in JSON format with structured fields:

```json
{
  "timestamp": "2025-12-10T09:00:00Z",
  "level": "INFO",
  "event": "ETL run completed",
  "run_id": "abc-123",
  "source": "coingecko",
  "records_processed": 100,
  "duration_seconds": 3.2
}
```

### Prometheus Metrics

**Available at `/metrics`:**

```
# ETL metrics
etl_runs_total{source="coingecko",status="success"} 25
etl_records_processed_total{source="coingecko"} 2500
etl_duration_seconds{source="coingecko"} 3.2

# API metrics
api_requests_total{endpoint="/data",status="200"} 1523
api_request_duration_seconds_bucket{endpoint="/data",le="0.1"} 1200

# Data freshness
data_staleness_seconds{source="coingecko"} 120
```

### Schema Drift Monitoring

Drift events logged to `schema_drift_logs` table:

```sql
SELECT * FROM schema_drift_logs 
WHERE confidence < 0.8 
ORDER BY detected_at DESC;
```

---

## 🔄 CI/CD Pipeline

**GitHub Actions Workflow** (`.github/workflows/ci-cd.yml`):

### On Push to Main:

1. **Test** (Python 3.11)
   - Install dependencies
   - Run Alembic migrations
   - Execute 61 tests with coverage
   - Upload coverage to Codecov

2. **Lint** (Code Quality)
   - Black (formatting)
   - isort (import sorting)
   - flake8 (linting)
   - mypy (type checking)

3. **Build & Deploy**
   - Build Docker image
   - Tag with commit SHA
   - Push to GitHub Container Registry
   - Update ECS service (rolling deployment)
   - Wait for service stabilization

4. **Smoke Test**
   - Dynamically fetch ECS task IP
   - Run 10 end-to-end tests
   - Verify API functionality
   - Validate ETL status

**Pipeline Status**: ✅ All checks passing

---

## 🎯 Key Features

### P2 Differentiators

#### 1. Schema Drift Detection
- **Fuzzy matching** with 70% similarity threshold
- **Confidence scoring** for drift severity
- **Automatic logging** to database
- **Warning thresholds** for missing/extra fields

#### 2. Failure Recovery
- **Checkpoint-based resume** from last successful position
- **Idempotent writes** prevent duplicate records
- **Transactional guarantees** via async context managers
- **Detailed error tracking** with run metadata

#### 3. Rate Limiting
- **Token bucket algorithm** with configurable limits
- **Exponential backoff** (1s → 2s → 4s → 8s)
- **Per-source configuration** (CoinGecko: 10 req/s, RSS: 5 req/s)
- **Automatic retry** on 429 responses

#### 4. Observability
- **Prometheus metrics** (13 metric types)
- **Structured JSON logs** with request IDs
- **ETL metadata tracking** (duration, records, errors)
- **Data staleness monitoring**

#### 5. DevOps
- **GitHub Actions CI/CD** with automated deployment
- **Docker multi-stage builds** for optimization
- **Health checks** in containers
- **Automated testing** on every push

#### 6. Anomaly Detection
- **Run comparison** endpoint
- **5 anomaly types**: record spikes, duration changes, transitions, source changes, error patterns
- **Statistical thresholds**: >50% record change, >100% duration change

---

## 📖 Documentation

- **README.md**: This file (comprehensive guide)
- **docs/DEPLOYMENT.md**: Detailed cloud deployment instructions
- **docs/PRODUCTION_READINESS.md**: Production checklist and best practices
- **API Docs**: http://localhost:8000/docs (interactive Swagger UI)

---

## 🛠️ Development

### Local Development Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start API server (dev mode with reload)
uvicorn api.main:app --reload --port 8000

# Start worker (in separate terminal)
python -m worker.scheduler
```

### Database Migrations

```bash
# Create new migration
alembic revision -m "description"

# Apply migrations
alembic upgrade head

# Rollback one version
alembic downgrade -1
```

### Add New Data Source

1. Create ingestion class in `ingestion/` extending `BaseIngestion`
2. Implement `fetch_data()` and `normalize_record()` methods
3. Add source-specific schema in `schemas/ingestion.py`
4. Register in `worker/scheduler.py`
5. Add tests in `tests/test_ingestion/`

---

## 📝 Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:port/dbname

# API Keys
COINGECKO_API_KEY=your_coingecko_key
ADMIN_API_KEY=your_admin_key

# Optional: Rate Limiting
COINGECKO_RATE_LIMIT=10  # requests per second
RSS_RATE_LIMIT=5

# Optional: Failure Injection (testing only)
ENABLE_FAILURE_INJECTION=false
FAILURE_PROBABILITY=0.0
```

---

## 🎓 Technical Highlights

- **Async-first**: SQLAlchemy 2.0 async engine, FastAPI async handlers
- **Type-safe**: Pydantic v2 for validation, mypy for static typing
- **Transactional**: Atomic checkpoint updates with database transactions
- **Resilient**: Exponential backoff, circuit breaker patterns
- **Observable**: Structured logging, Prometheus metrics, request tracing
- **Tested**: 83% coverage, 61 tests, smoke tests in CI/CD
- **Cloud-native**: Docker, ECS Fargate, RDS, EventBridge, CloudWatch

---

## 👨‍💻 Author

Rishi Jha

**Contact:**
- GitHub: [@R1ssh1](https://github.com/R1ssh1)
- Repository: [kasparro-backend-rishi-jha](https://github.com/R1ssh1/kasparro-backend-rishi-jha)

---

**Last Updated**: December 10, 2025
