.PHONY: up down logs ps rebuild shell-backend shell-frontend verify clean help

help:
	@echo "etf-momentum Docker Compose commands:"
	@echo "  make up              Start all services in background"
	@echo "  make down            Stop and remove containers (keep volumes)"
	@echo "  make logs            Tail logs from all services"
	@echo "  make ps              List running services"
	@echo "  make rebuild         Rebuild all images without cache"
	@echo "  make shell-backend   Open bash shell in backend container"
	@echo "  make shell-frontend  Open sh shell in frontend container"
	@echo "  make verify          Run docker-compose smoke verification"
	@echo "  make clean           Stop containers AND remove volumes (DATA LOSS)"

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

clean:
	docker compose down -v
