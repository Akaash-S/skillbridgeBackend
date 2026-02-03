# Simplified Production Dockerfile for SkillBridge Backend
# Direct Gunicorn deployment without Nginx
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.main:app
ENV FLASK_ENV=production
ENV PORT=8000

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    git \
    ca-certificates \
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

# Create logs directory
RUN mkdir -p /app/logs

# Set permissions
RUN chown -R appuser:appgroup /app && \
    chmod -R 755 /app && \
    chmod -R 777 /app/logs

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start Gunicorn directly
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--worker-class", "sync", "--timeout", "30", "--keep-alive", "5", "--max-requests", "1000", "--access-logfile", "/app/logs/gunicorn-access.log", "--error-logfile", "/app/logs/gunicorn-error.log", "--log-level", "info", "app.main:app"]