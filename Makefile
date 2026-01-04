# SkillBridge Suite Backend Makefile
# Common development and deployment tasks

.PHONY: help install install-dev run test lint format clean docker-build docker-run docker-stop seed-db

# Default target
help:
	@echo "SkillBridge Suite Backend - Available Commands:"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  install          Install production dependencies"
	@echo "  install-dev      Install development dependencies"
	@echo "  setup            Run full setup (virtual env + dependencies)"
	@echo ""
	@echo "Development:"
	@echo "  run              Run development server"
	@echo "  test             Run tests"
	@echo "  lint             Run code linting"
	@echo "  format           Format code with black"
	@echo "  clean            Clean temporary files"
	@echo ""
	@echo "Database:"
	@echo "  seed-db          Seed database with initial data"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build     Build Docker image"
	@echo "  docker-run       Run with Docker Compose"
	@echo "  docker-stop      Stop Docker containers"
	@echo "  docker-logs      View Docker logs"
	@echo ""
	@echo "Deployment:"
	@echo "  deploy           Deploy to production"
	@echo "  test-api         Test API endpoints"

# Installation targets
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

setup:
	python setup.py

# Development targets
run:
	python app/main.py

test:
	pytest tests/ -v --cov=app

lint:
	flake8 app/
	mypy app/

format:
	black app/
	isort app/

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache/
	rm -rf .coverage

# Database targets
seed-db:
	python seed_data.py

# Docker targets
docker-build:
	docker-compose build

docker-run:
	docker-compose up -d

docker-stop:
	docker-compose down

docker-logs:
	docker-compose logs -f

# Deployment targets
deploy:
	./deploy.sh

test-api:
	python test_api.py

# Development workflow
dev-setup: setup install-dev
	@echo "Development environment ready!"

dev-start: format lint run

# Production workflow
prod-setup: setup install
	@echo "Production environment ready!"

prod-deploy: docker-build docker-run
	@echo "Production deployment complete!"

# Update dependencies
update-deps:
	pip-compile requirements.in
	pip-compile requirements-dev.in

# Security check
security-check:
	pip-audit
	bandit -r app/

# Generate API documentation
docs:
	@echo "Generating API documentation..."
	@echo "Visit http://localhost:8000/docs after starting the server"