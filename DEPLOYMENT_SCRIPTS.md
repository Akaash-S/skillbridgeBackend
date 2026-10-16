# SkillBridge Deployment & Operations Scripts Documentation

This document defines the canonical operations and deployment toolset for SkillBridge, superseding legacy ad-hoc hotfix scripts created during rapid prototyping.

---

## Canonical Operational Scripts

All primary production and staging lifecycle operations are consolidated into `backend/scripts/`:

### 1. `scripts/deploy.sh`
Unified deployment orchestrator supporting both containerized Docker Compose stacks and Google Cloud Platform (Cloud Run / App Engine).

**Usage:**
```bash
# Production Docker Compose (Nginx + Gunicorn + Flask + Redis)
./scripts/deploy.sh compose

# Google Cloud Run
./scripts/deploy.sh cloud-run <GCP_PROJECT_ID>

# Google App Engine
./scripts/deploy.sh app-engine <GCP_PROJECT_ID>
```
**Responsibilities:**
- Validates environment file (`.env`).
- Ensures required filesystem directories exist (`logs/nginx`, `logs/app`, `nginx/ssl`).
- Invokes SSL bootstrap if certificates are not yet present.
- Builds containers with clean caches, boots services, and validates `/health`.

---

### 2. `scripts/setup-ssl.sh`
Consolidated SSL certificate generator and renewal manager.

**Usage:**
```bash
# Automated Let's Encrypt certificate acquisition & renewal crontab
./scripts/setup-ssl.sh letsencrypt skillbridge-server.asolvitra.tech admin@asolvitra.tech

# Local / development / staging self-signed fallback
./scripts/setup-ssl.sh self-signed
```
**Responsibilities:**
- Automates Certbot standalone verification.
- Copies certificate chains (`fullchain.pem`, `privkey.pem`) into Nginx mount directories with restricted permissions (`600`).
- Configures daily cron job (`0 12 * * *`) with Nginx reload hooks.

---

### 3. `scripts/backup-restore.sh`
Consolidated disaster recovery, encrypted backup, and point-in-time restore CLI.

**Usage:**
```bash
# 1. Trigger an on-demand encrypted backup
./scripts/backup-restore.sh backup

# 2. List all available backup snapshots in Firestore
./scripts/backup-restore.sh list

# 3. Dry-run validate snapshot integrity without modifying Firestore
./scripts/backup-restore.sh dry-run 20261016_110000

# 4. Perform actual database restore/rollback
./scripts/backup-restore.sh restore 20261016_110000
```
**Responsibilities:**
- Interacts with Python `BackupService` (`app/services/backup_service.py`).
- Handles Fernet AES encryption/decryption derived from server secrets.
- Chunks backup objects (800KB) to obey Firestore 1MB limits.
- Supports dry-run validation to test decryption and schema integrity safely before wiping or overwriting production collections.
- Dispatches email alerts to `ADMIN_EMAIL` on start, success, and failure.

---

## Legacy Script Inventory & Status

During initial GCE and domain deployment iterations, numerous one-off bash scripts were generated in the `backend/` root to address transient issues (port conflicts, Nginx HTTP/2 syntax deprecations, CORS headers, Docker versions). 

These scripts are retained for historical auditability but are **deprecated** in favor of the canonical scripts above:

| Legacy Script | Original Purpose | Replacement / Canonical Approach |
| :--- | :--- | :--- |
| `DEPLOY_NOW.sh`, `quick-redeploy.sh`, `simple-deploy.sh`, `clean-deploy.sh`, `final-deploy.sh` | One-click rebuilds during VM debugging | `scripts/deploy.sh compose` |
| `setup-ssl.sh`, `setup-letsencrypt-gcp.sh`, `fix-ssl-config.sh` | Let's Encrypt certbot experiments | `scripts/setup-ssl.sh letsencrypt` |
| `fix-port-conflict.sh`, `fix-port-and-deploy.sh` | Resolving 80/8000 conflicts on host | Managed via Docker Compose port mapping |
| `fix-nginx-config.sh`, `fix-nginx-http2-warning.sh`, `apply-final-nginx.sh` | Resolving Nginx syntax differences in Alpine | Canonical `nginx/conf.d/skillbridge.conf` |
| `disable-flask-cors.sh`, `update-cors.sh`, `fix-cors-headers.sh` | Resolving CORS duplicate header issues | Handled inside `app/__init__.py` and Nginx reverse proxy |
| `domain-setup.sh`, `domain-setup-fixed.sh`, `test-domain.sh` | DNS and propagation testing | Standalone standard tools (`dig`, `curl`) |
