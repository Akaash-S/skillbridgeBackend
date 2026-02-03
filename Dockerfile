# Multi-stage production Dockerfile for GCP Compute Engine
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.main:app
ENV FLASK_ENV=production
ENV PORT=8000

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
        redis-server \
        openssl \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create application user
RUN addgroup --system --gid 1001 appgroup \
    && adduser --system --uid 1001 --gid 1001 --no-create-home appuser

# Set work directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt requirements-minimal.txt ./

# Install Python dependencies
RUN python -m pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn[gevent]==21.2.0

# Copy application code
COPY . .

# Create default configuration files
RUN mkdir -p /etc/nginx/conf.d /etc/supervisor/conf.d /app/logs \
    && if [ -f nginx/nginx.conf ]; then \
        cp nginx/nginx.conf /etc/nginx/nginx.conf; \
    else \
        cat > /etc/nginx/nginx.conf << 'NGINX_EOF'
user www-data;
worker_processes auto;
pid /run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    server_tokens off;
    
    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;
    
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
    
    upstream backend {
        server 127.0.0.1:8000;
    }
    
    server {
        listen 80 default_server;
        listen 443 ssl default_server;
        
        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        
        location /health {
            proxy_pass http://backend/health;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        location / {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
NGINX_EOF
    fi

# Create supervisor configuration
RUN if [ -f supervisord.conf ]; then \
        cp supervisord.conf /etc/supervisor/conf.d/supervisord.conf; \
    else \
        cat > /etc/supervisor/conf.d/supervisord.conf << 'SUPERVISOR_EOF'
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
command=/usr/local/bin/gunicorn --bind 127.0.0.1:8000 --workers 4 --worker-class gevent --timeout 30 --keep-alive 5 --max-requests 1000 --access-logfile /app/logs/gunicorn-access.log --error-logfile /app/logs/gunicorn-error.log --log-level info app.main:app
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
SUPERVISOR_EOF
    fi

# Set permissions
RUN chown -R appuser:appgroup /app \
    && chown -R www-data:www-data /var/log/nginx \
    && chown -R redis:redis /var/lib/redis \
    && chmod -R 755 /app \
    && chmod -R 777 /app/logs

# Generate self-signed SSL certificates
RUN mkdir -p /etc/nginx/ssl \
    && openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/nginx/ssl/privkey.pem \
        -out /etc/nginx/ssl/fullchain.pem \
        -subj "/C=US/ST=State/L=City/O=SkillBridge/CN=localhost" \
    && cp /etc/nginx/ssl/fullchain.pem /etc/nginx/ssl/chain.pem \
    && chmod 600 /etc/nginx/ssl/*.pem

# Expose ports
EXPOSE 80 443

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# Use supervisor to manage multiple processes
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]