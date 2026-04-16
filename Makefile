.PHONY: run dev test lint format check db-stats load-catalogs seed clean

# ── Servidor ──────────────────────────────────────────────────────────────────

run:
	uvicorn app.main:app --host 0.0.0.0 --port 8000

dev:
	uvicorn app.main:app --reload --port 8000

# ── Testes ────────────────────────────────────────────────────────────────────

test:
	python3 -m pytest tests/ -v --tb=short

test-q:
	python3 -m pytest tests/ -q

# ── Qualidade ─────────────────────────────────────────────────────────────────

lint:
	python3 -m ruff check app/ tests/ 2>/dev/null || echo "ruff not installed — pip install ruff"

format:
	python3 -m ruff format app/ tests/ 2>/dev/null || echo "ruff not installed — pip install ruff"

typecheck:
	python3 -m mypy app/ --ignore-missing-imports 2>/dev/null || echo "mypy not installed — pip install mypy"

check: lint test

# ── Banco de dados ────────────────────────────────────────────────────────────

db-stats:
	python3 -c "from app.core.constitution import get_stats; import json; print(json.dumps(get_stats(), indent=2))"

db-reset:
	rm -f data/constitution.db data/constitution.db-shm data/constitution.db-wal
	python3 -c "from app.core.constitution import init_db; from app.core.constitution_seed import seed; init_db(); seed()"
	@echo "DB recriado e populado."

load-catalogs:
	python3 -m tools.catalog_loader --stats

load-hela:
	python3 -m tools.catalog_loader --fabricante HE

load-al:
	python3 -m tools.catalog_loader --fabricante AL

# ── Deploy ────────────────────────────────────────────────────────────────────

docker-build:
	docker build -t vdx-glass-engine:latest .

docker-run:
	docker run -p 8000:8000 --env-file .env vdx-glass-engine:latest

# ── Limpeza ───────────────────────────────────────────────────────────────────

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -f data/outputs/*.png data/outputs/*.pdf 2>/dev/null || true
	@echo "Limpeza concluída."
