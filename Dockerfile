# Production Dockerfile for SkillBridge Backend
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.main:app
ENV FLASK_ENV=production
ENV PORT=8000

# Install system dependencies (removed redis-server)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    git \
    ca-certificates \
    nginx \
    supervisor \
    openssl \
    && rm -rf /var/lib/apt/lists/*

# Create application user
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

# Set work directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt requirements-minimal.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn==21.2.0

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled /etc/nginx/ssl /app/logs /var/log/supervisor

# Remove default nginx site
RUN rm -f /etc/nginx/sites-enabled/default

# Create nginx main configuration
RUN echo "user www-data;" > /etc/nginx/nginx.conf && \
    echo "worker_processes auto;" >> /etc/nginx/nginx.conf && \
    echo "pid /run/nginx.pid;" >> /etc/nginx/nginx.conf && \
    echo "" >> /etc/nginx/nginx.conf && \
    echo "events {" >> /etc/nginx/nginx.conf && \
    echo "    worker_connections 1024;" >> /etc/nginx/nginx.conf && \
    echo "}" >> /etc/nginx/nginx.conf && \
    echo "" >> /etc/nginx/nginx.conf && \
    echo "http {" >> /etc/nginx/nginx.conf && \
    echo "    include /etc/nginx/mime.types;" >> /etc/nginx/nginx.conf && \
    echo "    default_type application/octet-stream;" >> /etc/nginx/nginx.conf && \
    echo "    sendfile on;" >> /etc/nginx/nginx.conf && \
    echo "    tcp_nopush on;" >> /etc/nginx/nginx.conf && \
    echo "    tcp_nodelay on;" >> /etc/nginx/nginx.conf && \
    echo "    keepalive_timeout 65;" >> /etc/nginx/nginx.conf && \
    echo "    server_tokens off;" >> /etc/nginx/nginx.conf && \
    echo "    access_log /var/log/nginx/access.log;" >> /etc/nginx/nginx.conf && \
    echo "    error_log /var/log/nginx/error.log;" >> /etc/nginx/nginx.conf && \
    echo "    gzip on;" >> /etc/nginx/nginx.conf && \
    echo "    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;" >> /etc/nginx/nginx.conf && \
    echo "    include /etc/nginx/sites-enabled/*;" >> /etc/nginx/nginx.conf && \
    echo "}" >> /etc/nginx/nginx.conf

# Create nginx site configuration
RUN echo "server {" > /etc/nginx/sites-available/skillbridge && \
    echo "    listen 80 default_server;" >> /etc/nginx/sites-available/skillbridge && \
    echo "    listen 443 ssl default_server;" >> /etc/nginx/sites-available/skillbridge && \
    echo "    ssl_certificate /etc/nginx/ssl/fullchain.pem;" >> /etc/nginx/sites-available/skillbridge && \
    echo "    ssl_certificate_key /etc/nginx/ssl/privkey.pem;" >> /etc/nginx/sites-available/skillbridge && \
    echo "    location /health {" >> /etc/nginx/sites-available/skillbridge && \
    echo "        proxy_pass http://127.0.0.1:8000/health;" >> /etc/nginx/sites-available/skillbridge && \
    echo "        proxy_set_header Host \$host;" >> /etc/nginx/sites-available/skillbridge && \
    echo "        proxy_set_header X-Real-IP \$remote_addr;" >> /etc/nginx/sites-available/skillbridge && \
    echo "        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;" >> /etc/nginx/sites-available/skillbridge && \
    echo "        proxy_set_header X-Forwarded-Proto \$scheme;" >> /etc/nginx/sites-available/skillbridge && \
    echo "    }" >> /etc/nginx/sites-available/skillbridge && \
    echo "    location / {" >> /etc/nginx/sites-available/skillbridge && \
    echo "        proxy_pass http://127.0.0.1:8000;" >> /etc/nginx/sites-available/skillbridge && \
    echo "        proxy_set_header Host \$host;" >> /etc/nginx/sites-available/skillbridge && \
    echo "        proxy_set_header X-Real-IP \$remote_addr;" >> /etc/nginx/sites-available/skillbridge && \
    echo "        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;" >> /etc/nginx/sites-available/skillbridge && \
    echo "        proxy_set_header X-Forwarded-Proto \$scheme;" >> /etc/nginx/sites-available/skillbridge && \
    echo "    }" >> /etc/nginx/sites-available/skillbridge && \
    echo "}" >> /etc/nginx/sites-available/skillbridge

# Enable the site
RUN ln -sf /etc/nginx/sites-available/skillbridge /etc/nginx/sites-enabled/

# Test nginx configuration
RUN nginx -t

# Generate self-signed SSL certificates
RUN openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/privkey.pem \
    -out /etc/nginx/ssl/fullchain.pem \
    -subj "/C=US/ST=State/L=City/O=SkillBridge/CN=localhost" && \
    chmod 600 /etc/nginx/ssl/*.pem

# Create supervisor configuration (without Redis)
RUN echo "[supervisord]" > /etc/supervisor/conf.d/supervisord.conf && \
    echo "nodaemon=true" >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "user=root" >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "logfile=/var/log/supervisor/supervisord.log" >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "pidfile=/var/run/supervisord.pid" >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "" >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "[program:nginx]" >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "command=/usr/sbin/nginx -g \"daemon off;\"" >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "autostart=true" >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "autorestart=true" >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "user=root" >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "stdout_logfile=/var/log/supervisor/nginx.log" >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "stderr_logfile=/var/log/supervisor/nginx.log" >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "" >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "[program:gunicorn]" >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "command=/usr/local/bin/gunicorn --bind 127.0.0.1:8000 --workers 2 --worker-class sync --timeout 30 --keep-alive 5 --max-requests 1000 --access-logfile /app/logs/gunicorn-access.log --error-logfile /app/logs/gunicorn-error.log --log-level info app.main:app" >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "directory=/app" >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "autostart=true" >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "autorestart=true" >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "user=appuser" >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "stdout_logfile=/var/log/supervisor/gunicorn.log" >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "stderr_logfile=/var/log/supervisor/gunicorn.log" >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "environment=PATH=\"/usr/local/bin:%(ENV_PATH)s\"" >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "" >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "[unix_http_server]" >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "file=/var/run/supervisor.sock" >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "chmod=0700" >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "" >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "[supervisorctl]" >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "serverurl=unix:///var/run/supervisor.sock" >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "" >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "[rpcinterface:supervisor]" >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface" >> /etc/supervisor/conf.d/supervisord.conf

# Set permissions
RUN chown -R appuser:appgroup /app && \
    chown -R www-data:www-data /var/log/nginx && \
    chmod -R 755 /app && \
    chmod -R 777 /app/logs

# Expose ports
EXPOSE 80 443

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# Start supervisor
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]