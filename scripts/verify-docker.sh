#!/usr/bin/env bash
# etf-momentum Docker Compose 冒烟验证脚本
# 验证：compose 配置合法 + 三个端点可访问
set -euo pipefail

COMPOSE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$COMPOSE_DIR"

echo "[verify-docker] docker compose config --quiet"
docker compose config --quiet && echo "  ✓ config valid"
echo ""

echo "[verify-docker] docker compose up -d --build"
docker compose up -d --build

echo ""
echo "[verify-docker] waiting for backend /health (max 60s)..."
ready=0
for i in $(seq 1 60); do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo "  ✓ backend ready after ${i}s"
        ready=1
        break
    fi
    sleep 1
done
if [ "$ready" -ne 1 ]; then
    echo "  ✗ backend /health not reachable after 60s"
    docker compose logs --tail=50 backend
    exit 1
fi

echo ""
echo "[verify-docker] backend endpoints:"
echo "  GET /health:"
curl -s http://localhost:8000/health
echo ""
echo "  GET /api/v1/etfs/count:"
curl -s http://localhost:8000/api/v1/etfs/count
echo ""

echo "[verify-docker] frontend root:"
code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/)
echo "  HTTP $code"
if [ "$code" != "200" ]; then
    echo "  ✗ frontend not reachable"
    docker compose logs --tail=30 frontend
    exit 1
fi

echo ""
echo "[verify-docker] ✓ all smoke checks passed"
echo "  Next steps:"
echo "    docker compose exec backend uv run alembic upgrade head   # initialize DB"
echo "    docker compose exec backend uv run python -m app.data.sync etfs   # sync ETF list"
