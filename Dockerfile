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

# Copy application code
COPY . .

# Copy configuration files
COPY nginx/nginx.conf /etc/nginx/nginx.conf
COPY nginx/conf.d/security.conf /etc/nginx/conf.d/security.conf
COPY gunicorn.conf.py /app/gunicorn.conf.py
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Create necessary directories and set permissions
RUN mkdir -p /app/logs /var/log/nginx /var/log/supervisor /run/nginx /var/lib/redis \
    && chown -R appuser:appgroup /app \
    && chown -R www-data:www-data /var/log/nginx \
    && chown -R redis:redis /var/lib/redis \
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