.PHONY: help dev setup test

help:
	@echo "Available commands:"
	@echo "  make setup    - Initial setup"
	@echo "  make dev      - Start all services"
	@echo "  make test     - Run all tests"

setup:
	cd apps/flutter && flutter pub get
	cd apps/backend && pip install -r requirements.txt
	docker-compose up -d postgres redis

dev:
	docker-compose up -d postgres redis
	@tmux new-session -d -s dev
	@tmux send-keys -t dev "cd apps/backend && uvicorn app.main:app --reload" C-m
	@tmux split-window -h -t dev
	@tmux send-keys -t dev "cd apps/flutter && flutter run -d chrome" C-m
	@tmux attach -t dev

test:
	cd apps/flutter && flutter test
	cd apps/backend && pytest

generate-api:
	# Generate OpenAPI spec from FastAPI
	cd apps/backend && python -c "import json; from app.main import app; \
		from fastapi.openapi.utils import get_openapi; \
		print(json.dumps(get_openapi(title=app.title, version=app.version, routes=app.routes)))" \
		> ../packages/api-client/openapi.json
	# Generate Dart client from OpenAPI
	cd apps/flutter && dart run build_runner build