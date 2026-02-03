# Multi-stage production Dockerfile for GCP Compute Engine
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.main:app
ENV FLASK_ENV=production
ENV PORT=8080

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        curl \
        git \
        ca-certificates \
        nginx \
        supervisor \
        cron \
        redis-server \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create application user
RUN addgroup --system --gid 1001 appgroup \
    && adduser --system --uid 1001 --gid 1001 --no-create-home appuser \
    && usermod -aG redis appuser

# Set work directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt requirements-minimal.txt ./

# Install Python dependencies
RUN python -m pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn[gevent]==21.2.0

# Create default gunicorn config if it doesn't exist
RUN if [ ! -f gunicorn.conf.py ]; then \
        echo "Creating default gunicorn.conf.py..."; \
        cat > gunicorn.conf.py << 'EOF'
import multiprocessing
import os

bind = f"0.0.0.0:{os.environ.get('PORT', 8080)}"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gevent"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 30
keepalive = 5
preload_app = True
accesslog = "/app/logs/gunicorn-access.log"
errorlog = "/app/logs/gunicorn-error.log"
loglevel = "info"
capture_output = True
EOF
    fi

# Copy application code
COPY . .

# Create configuration files if they don't exist, then copy them
RUN mkdir -p /etc/nginx/conf.d /etc/supervisor/conf.d \
    && if [ -f nginx/nginx.conf ]; then \
        cp nginx/nginx.conf /etc/nginx/nginx.conf; \
    else \
        echo "Creating default nginx.conf..."; \
        cat > /etc/nginx/nginx.conf << 'EOF'
user www-data;
worker_processes auto;
pid /run/nginx.pid;
include /etc/nginx/modules-enabled/*.conf;

events {
    worker_connections 768;
}

http {
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    server_tokens off;

    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;

    gzip on;

    upstream backend {
        server 127.0.0.1:8080;
    }

    server {
        listen 80 default_server;
        listen 443 ssl default_server;
        
        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        
        location / {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
EOF
    fi \
    && if [ -f nginx/conf.d/security.conf ]; then \
        cp nginx/conf.d/security.conf /etc/nginx/conf.d/security.conf; \
    fi \
    && if [ -f supervisord.conf ]; then \
        cp supervisord.conf /etc/supervisor/conf.d/supervisord.conf; \
    else \
        echo "Creating default supervisord.conf..."; \
        cat > /etc/supervisor/conf.d/supervisord.conf << 'EOF'
[supervisord]
nodaemon=true
user=root
logfile=/var/log/supervisor/supervisord.log
pidfile=/var/run/supervisord.pid

[program:nginx]
command=/usr/sbin/nginx -g "daemon off;"
autostart=true
autorestart=true
user=root
stdout_logfile=/var/log/supervisor/nginx.log
stderr_logfile=/var/log/supervisor/nginx.log

[program:gunicorn]
command=/usr/local/bin/gunicorn --config /app/gunicorn.conf.py app.main:app
directory=/app
autostart=true
autorestart=true
user=appuser
stdout_logfile=/var/log/supervisor/gunicorn.log
stderr_logfile=/var/log/supervisor/gunicorn.log
environment=PATH="/usr/local/bin:%(ENV_PATH)s"

[program:redis]
command=/usr/bin/redis-server --bind 127.0.0.1 --port 6379 --daemonize no
autostart=true
autorestart=true
user=redis
stdout_logfile=/var/log/supervisor/redis.log
stderr_logfile=/var/log/supervisor/redis.log

[unix_http_server]
file=/var/run/supervisor.sock
chmod=0700

[supervisorctl]
serverurl=unix:///var/run/supervisor.sock

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface
EOF
    fi

# Create necessary directories and set permissions
RUN mkdir -p /app/logs /var/log/nginx /var/log/supervisor /var/log/redis /run/nginx /var/lib/redis /etc/nginx/conf.d /etc/supervisor/conf.d \
    && chown -R appuser:appgroup /app \
    && chown -R www-data:www-data /var/log/nginx \
    && chown -R redis:redis /var/lib/redis /var/log/redis \
    && chmod -R 755 /app \
    && chmod -R 777 /app/logs

# Generate self-signed SSL certificates for initial setup
RUN mkdir -p /etc/nginx/ssl \
    && openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/nginx/ssl/privkey.pem \
        -out /etc/nginx/ssl/fullchain.pem \
        -subj "/C=US/ST=State/L=City/O=SkillBridge/CN=localhost" \
    && cp /etc/nginx/ssl/fullchain.pem /etc/nginx/ssl/chain.pem \
    && openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/nginx/ssl/default.key \
        -out /etc/nginx/ssl/default.crt \
        -subj "/C=US/ST=State/L=City/O=Default/CN=default" \
    && chmod 600 /etc/nginx/ssl/*.pem /etc/nginx/ssl/*.key \
    && chmod 644 /etc/nginx/ssl/*.crt

# Expose ports
EXPOSE 80 443

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# Use supervisor to manage multiple processes
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]