.PHONY: up down logs ps rebuild shell-backend shell-frontend verify clean seed-demo seed-demo-local help

help:
	@echo "etf-momentum Docker Compose commands:"
	@echo "  make up                Start all services in background"
	@echo "  make down              Stop and remove containers (keep volumes)"
	@echo "  make logs              Tail logs from all services"
	@echo "  make ps                List running services"
	@echo "  make rebuild           Rebuild all images without cache"
	@echo "  make shell-backend     Open bash shell in backend container"
	@echo "  make shell-frontend    Open sh shell in frontend container"
	@echo "  make verify            Run docker-compose smoke verification"
	@echo "  make seed-demo         Load bundled demo data into running backend container"
	@echo "  make seed-demo-local   Load bundled demo data (local dev, no Docker)"
	@echo "  make clean             Stop containers AND remove volumes (DATA LOSS)"

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

ps:
	docker compose ps

rebuild:
	docker compose build --no-cache

shell-backend:
	docker compose exec backend bash

shell-frontend:
	docker compose exec frontend sh

verify:
	./scripts/verify-docker.sh

seed-demo:
	docker compose exec backend uv run python -m app.data.seed_demo

seed-demo-local:
	cd backend && uv run python -m app.data.seed_demo

clean:
	docker compose down -v