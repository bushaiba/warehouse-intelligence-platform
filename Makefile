.PHONY: install test lint typecheck quality demo api docker-up docker-down clean

install:
	python -m pip install -e ".[dev]"

test:
	pytest --cov=warehouse_intelligence --cov-report=term-missing --cov-fail-under=80

lint:
	ruff check src tests

typecheck:
	mypy src

quality: lint typecheck test

demo:
	python -m warehouse_intelligence.cli demo

api:
	uvicorn warehouse_intelligence.api.main:app --reload --port 8000

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down -v

clean:
	rm -rf runtime .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
