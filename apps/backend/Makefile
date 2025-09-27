# Sequel Backend Makefile

.PHONY: help install install-dev dev dev-direct test lint format clean docker-build docker-up docker-down

help:
	@echo "🚀 Sequel Backend Commands:"
	@echo ""
	@echo "📦 Setup:"
	@echo "  install          - Install production dependencies"
	@echo "  install-dev      - Install development dependencies"
	@echo "  setup           - Complete development setup"
	@echo ""
	@echo "🔧 Development:"
	@echo "  dev             - Start development server (recommended)"
	@echo "  dev-direct      - Start server directly"
	@echo "  dev-module      - Start as Python module"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  test            - Run all tests"
	@echo "  test-cov        - Run tests with coverage"
	@echo "  test-api        - Run only API tests"
	@echo "  test-services   - Run only service tests"
	@echo ""
	@echo "🔍 Code Quality:"
	@echo "  lint            - Run linting"
	@echo "  format          - Format code"
	@echo "  clean           - Clean cache files"
	@echo ""
	@echo "🐳 Docker:"
	@echo "  docker-build    - Build Docker image"
	@echo "  docker-up       - Start Docker services"
	@echo "  docker-down     - Stop Docker services"
	@echo ""
	@echo "⚡ Celery:"
	@echo "  celery-worker   - Start Celery worker"
	@echo "  celery-beat     - Start Celery beat"
	@echo "  celery-flower   - Start Celery monitoring"

# === SETUP ===

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

setup: install-dev
	@echo "🔧 Setting up development environment..."
	@if [ ! -f .env ]; then echo "📋 Creating .env file..."; cp .env.example .env 2>/dev/null || echo "⚠️  Please create .env file manually"; fi
	@echo "✅ Development setup complete!"
	@echo ""
	@echo "🚀 To start the server, run: make dev"
	@echo "📚 API docs will be available at: http://localhost:8000/docs"

# === DEVELOPMENT ===

dev:
	@echo "🚀 Starting Sequel Backend Development Server..."
	python run.py

dev-direct:
	@echo "🚀 Starting server directly..."
	python app/main.py

dev-module:
	@echo "🚀 Starting as Python module..."
	python -m app.main

# === TESTING ===

test:
	@echo "🧪 Running all tests..."
	pytest app/tests/ -v

test-cov:
	@echo "🧪 Running tests with coverage..."
	pytest app/tests/ -v --cov=app --cov-report=term-missing --cov-report=html

test-api:
	@echo "🧪 Running API tests..."
	pytest app/tests/api/ -v

test-services:
	@echo "🧪 Running service tests..."
	pytest app/tests/services/ -v

test-integration:
	@echo "🧪 Running integration tests..."
	pytest app/tests/ -v -m integration

test-performance:
	@echo "🧪 Running performance tests..."
	pytest app/tests/ -v -m performance

# === CODE QUALITY ===

lint:
	@echo "🔍 Running linting..."
	flake8 app/
	mypy app/ --ignore-missing-imports

format:
	@echo "🎨 Formatting code..."
	black app/
	isort app/

clean:
	@echo "🧹 Cleaning cache files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .coverage htmlcov/ .pytest_cache/ .mypy_cache/

# === DOCKER ===

docker-build:
	@echo "🐳 Building Docker image..."
	docker-compose build

docker-up:
	@echo "🐳 Starting Docker services..."
	docker-compose up -d

docker-down:
	@echo "🐳 Stopping Docker services..."
	docker-compose down

docker-logs:
	@echo "📋 Showing Docker logs..."
	docker-compose logs -f

# === CELERY ===

celery-worker:
	@echo "⚡ Starting Celery worker..."
	celery -A app.tasks.celery_app worker --loglevel=info --queues=default,keybert,keybert_batch

celery-beat:
	@echo "⚡ Starting Celery beat scheduler..."
	celery -A app.tasks.celery_app beat --loglevel=info

celery-flower:
	@echo "🌸 Starting Celery Flower monitoring..."
	@echo "📊 Flower will be available at: http://localhost:5555"
	celery -A app.tasks.celery_app flower

# === UTILITIES ===

check-health:
	@echo "🏥 Checking service health..."
	@curl -s http://localhost:8000/health | python -m json.tool 2>/dev/null || echo "❌ Service not running"

check-keybert:
	@echo "🔤 Checking KeyBERT service..."
	@curl -s http://localhost:8000/api/v1/nlp/keybert/health | python -m json.tool 2>/dev/null || echo "❌ KeyBERT service not available"

demo:
	@echo "🎯 Running KeyBERT demo..."
	@curl -X POST "http://localhost:8000/api/v1/nlp/keybert/extract" \
		-H "Content-Type: application/json" \
		-d '{"text": "Die Bundesregierung plant neue Maßnahmen zur Bekämpfung des Klimawandels.", "language": "de"}' \
		| python -m json.tool 2>/dev/null || echo "❌ Demo failed - is the server running?"

# === QUICK START ===

quickstart: setup dev

# === INFO ===

info:
	@echo "📊 Sequel Backend Information:"
	@echo "  Python: $(shell python --version)"
	@echo "  FastAPI: $(shell pip show fastapi | grep Version | cut -d' ' -f2 2>/dev/null || echo 'Not installed')"
	@echo "  Current directory: $(shell pwd)"
	@echo "  Environment file: $(shell [ -f .env ] && echo '✅ .env exists' || echo '❌ .env missing')"