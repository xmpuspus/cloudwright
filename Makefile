.PHONY: install test lint format build clean

install:
	pip install -e packages/core -e packages/cli -e packages/web
	pip install pytest pytest-timeout pytest-cov ruff

test:
	pytest packages/core/tests/ packages/web/tests/ packages/cli/tests/ -x -q

test-cov:
	pytest --cov=cloudwright --cov=cloudwright_cli --cov=backend --cov-report=term-missing

lint:
	ruff check packages/

format:
	ruff format packages/
	ruff check packages/ --fix

build:
	python -m build packages/core
	python -m build packages/cli
	python -m build packages/web

clean:
	rm -rf packages/core/dist packages/cli/dist packages/web/dist
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
