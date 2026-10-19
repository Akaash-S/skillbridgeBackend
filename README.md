# SkillBridge Suite - REST Backend 🚀

A production-ready REST API backend for the SkillBridge career development, skills gap analysis, and personalized learning platform. Built with Python 3.12, Flask 3.0, Google Cloud Firestore, and Google Gemini AI.

---

## ⚡ System Status & Deployment Note

> [!NOTE]
> **Deployment Status: Self-Hosted VM Architecture (Dormant / Archived to Conserve Cloud Costs)**
> The backend was previously provisioned and verified on a Google Cloud Compute Engine VM (`skillbridge-server.asolvitra.tech`) with Let's Encrypt SSL and Docker Compose. The remote VM is currently powered down to eliminate ongoing hosting costs. The service is production-ready and fully runnable locally or on any cloud container host via `scripts/deploy.sh`.

---

## 🛠️ Architecture & Verified Specifications

- **API Surface**: **133 Endpoints** registered across **19 Blueprints** (`auth`, `users`, `skills`, `roadmap`, `learning`, `jobs`, `activity`, `settings`, `assessment`, `courses`, `analytics`, `mentorship`, `career_compass`, `resume`, `progress`, `profile`, `gamification`, `projects`, `roles`).
- **Database**: **Google Cloud Firestore (Native Mode)** spanning **28 collections** (`users`, `user_state`, `skills`, `roadmaps`, `jobs`, `system_backups`, etc.).
- **Reliability Policy**: **Fail-Closed**. Production mode halts execution and returns `HTTP 503 DATABASE_UNAVAILABLE` if Firestore cannot be reached. In-memory mocking is strictly disabled unless `ALLOW_MOCK_DB=true` is set.
- **Worker Safety**: **APScheduler Multi-Worker Guard**. Daily automated backups run on exactly one Gunicorn worker via OS file locking (`fcntl.flock` on Unix, `msvcrt` on Windows).
- **Disaster Recovery**: Automated daily encrypted backups (AES-256 Fernet), chunked into 800KB documents to satisfy Firestore 1MB quotas, retaining 10 versions with dry-run restore validation (`scripts/backup-restore.sh`).
- **Rate Limiting**: Distributed rate limiting using **Flask-Limiter backed by Redis** (`1000/hr, 100/min` global; `5/min` auth) with resilient in-memory fallback.
- **CI/CD**: GitHub Actions workflow testing Flake8 linting, Pytest test suites, and Docker container build.

---

## 📁 Project Structure

```
backend/
├── app/
│   ├── __init__.py              # Application factory & blueprint registration
│   ├── main.py                  # Entry point for container runtime
│   ├── config.py                # Environment configuration & rate limits
│   ├── db/                      # Firestore data access layer
│   │   └── firestore.py         # Fail-closed Firestore service
│   ├── routes/                  # 19 Route Blueprints (133 endpoints)
│   ├── services/                # 21 Business logic service modules
│   │   ├── backup_service.py    # Encrypted backup & rollback engine
│   │   ├── firebase_service.py  # Auth token verification & cookie sessions
│   │   ├── roadmap_ai.py        # Gemini 2.0 Flash roadmap synthesis
│   │   └── skills_engine.py     # Skills scoring & gap analysis
│   └── utils/                   # Helpers, validators, and scheduler_guard
├── scripts/                     # Canonical operational scripts
│   ├── deploy.sh                # Consolidated deploy script (compose / GCP)
│   ├── setup-ssl.sh             # Consolidated Let's Encrypt / SSL script
│   ├── backup-restore.sh        # Encrypted backup, restore, and dry-run CLI
│   ├── backup_cli.py            # Python CLI bridge for BackupService
│   ├── benchmark_endpoints.py   # Latency measurement tool (p50 / p95)
│   ├── legacy/                  # Archived one-off deployment iterations
│   └── debug/                   # Standalone diagnostic tools
├── tests/                       # Pytest automated test suites
│   ├── test_auth.py             # Auth endpoints, cookie sessions & validation
│   ├── test_roadmap.py          # AI roadmap validation & template fallback
│   └── test_skills_engine.py    # Readiness scoring & skill gap logic
├── Dockerfile                   # Production Python 3.11-slim container
├── docker-compose.yml           # App + Nginx + Redis service stack
├── pytest.ini                   # Pytest configuration
├── requirements.txt             # Locked Python dependencies
└── run.py                       # Local development runner
```

---

## 🧪 Automated Testing

The backend includes a comprehensive test suite covering skills readiness scoring, JWT and HttpOnly cookie authentication, and AI roadmap input validation:

```bash
# Run all automated tests
pytest tests/

# Run with verbose output
pytest -v tests/
```

**Test Coverage Summary:**
- `tests/test_skills_engine.py` (6 passed): Validates readiness score calculation (0–100), full/partial/missing skills classification, and empty set edge cases.
- `tests/test_auth.py` (6 passed): Validates missing tokens (400), invalid Firebase tokens (401), HttpOnly `sb_session` cookie issuance, authenticated `/auth/me` profiles, and logout cookie expiration.
- `tests/test_roadmap.py` (6 passed): Validates missing `targetRole` (400), invalid `experienceLevel` (400), template fallbacks, roadmap item schemas (201), and unauthenticated access rejection (401).

---

## 🚀 Local Development Setup

### 1. Prerequisites
- Python 3.11 or 3.12
- Virtual environment tool (`venv`)
- (Optional) Redis server for local distributed rate limiting

### 2. Installation
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy the template and configure your keys:
```bash
cp .env.example .env
```

Key environment variables:
```ini
FLASK_ENV=development
SECRET_KEY=your-secure-random-secret-key
PORT=8000

# Firebase & Firestore
GOOGLE_APPLICATION_CREDENTIALS=credentials/firebase-service-account.json
# Or for local development without live GCP credentials:
ALLOW_MOCK_DB=true

# AI & Third-Party APIs
GEMINI_API_KEY=your-gemini-api-key
ADZUNA_APP_ID=your-adzuna-app-id
ADZUNA_APP_KEY=your-adzuna-app-key

# Redis (optional, falls back to in-memory)
REDIS_URL=redis://localhost:6379/0
```

### 4. Running the Server
```bash
python run.py
```
The server will boot at `http://localhost:8000`. Test the health probe:
```bash
curl http://localhost:8000/health
```

---

## 🚢 Deployment & Operations

All deployment tasks are consolidated into documented scripts in `scripts/`:

### Docker Compose Production Run
```bash
./scripts/deploy.sh compose
```
Builds the production container with clean cache, brings up Gunicorn and Nginx with rate limiting, and validates `/health`.

### SSL Certificates
```bash
# Automated Let's Encrypt acquisition & renewal cron
./scripts/setup-ssl.sh letsencrypt yourdomain.com admin@yourdomain.com

# Local self-signed certificate fallback
./scripts/setup-ssl.sh self-signed
```

### Encrypted Backup & Rollback CLI
```bash
# Trigger an on-demand encrypted backup
./scripts/backup-restore.sh backup

# List available Firestore snapshot versions
./scripts/backup-restore.sh list

# Validate snapshot decryption & document count without modifying data
./scripts/backup-restore.sh dry-run <SNAPSHOT_ID>

# Restore database from snapshot
./scripts/backup-restore.sh restore <SNAPSHOT_ID>
```

---

## 📈 Latency Benchmarks

Tested on local runtime (50 iterations per endpoint, `ALLOW_MOCK_DB=true`):
- `GET /health`: **p50 = 0.35 ms**, p95 = 0.62 ms
- `GET /skills/master`: **p50 = 0.65 ms**, p95 = 1.37 ms
- `GET /roles/categories`: **p50 = 0.43 ms**, p95 = 1.03 ms
- `GET /roadmap/templates`: **p50 = 1.29 ms**, p95 = 2.84 ms