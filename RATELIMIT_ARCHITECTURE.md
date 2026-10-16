# Rate Limiting Architecture Decision: In-Memory vs. Redis

## Context & Motivation
SkillBridge uses Flask-Limiter to throttle API usage (protecting AI generation, authentication, and proctored assessment endpoints from abuse and DoS).
In a multi-worker production server (Gunicorn with 2+ worker processes):
- `memory://` creates an isolated in-process bucket per worker process.
- Requests distributed round-robin or via least-connections across N workers effectively multiply the allowed limit by N (e.g., a "5 per minute" limit across 2 workers permits up to 10 requests).
- Worker restarts reset rate-limiting counters.

## Architecture Decision
1. **Dynamic Storage Support:**  
   `Config.RATELIMIT_STORAGE_URI` dynamically resolves:
   - `REDIS_URL` or derived connection string from `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD` (e.g. GCP Memorystore for Redis or cloud Redis).
   - Falls back to `memory://` when Redis is unconfigured, allowing standalone local development without requiring a running Redis daemon.

2. **Multi-Tier Defense:**
   - **Infrastructure Tier (Nginx):** Nginx on the host VM provides high-performance connection and request rate limiting (`limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s`, `burst=20 nodelay`).
   - **Application Tier (Flask-Limiter):** Provides granular route-level policies (e.g., `/auth/login` at 5/min, `/roadmap/generate` at 10/hr).

## Enabling Redis in Production
Set the following environment variable in `.env` or GCP Cloud Run / GCE instance settings:
```env
REDIS_URL=redis://:your_password@redis-host:6379/0
# Or using individual variables:
REDIS_HOST=10.0.0.3
REDIS_PORT=6379
REDIS_PASSWORD=secret
```
