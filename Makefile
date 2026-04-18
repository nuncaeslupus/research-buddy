.PHONY: lint format test test-all clean sync regen-example build

sync:
	uv sync --extra dev

build:
	rm -rf dist/ && python -m build

regen-example:
	uv run research-buddy build src/research_buddy/starter.json --output $(CURDIR)/starter-example/starter.html

lint:
	uv run ruff check . && uv run mypy . --explicit-package-bases

format:
	uv run ruff check --fix --unsafe-fixes . && uv run ruff format .

test:
	uv run pytest tests/ -v

test-all:
	uv run pytest tests/ -v --run-slow

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .mypy_cache .ruff_cache .pytest_cache dist/
