.PHONY: lint format test test-all clean sync regen-example

sync:
	uv sync --extra dev

regen-example:
	rm -rf examples/starter
	uv run research-buddy init examples/starter --title "Research Buddy Project" --subtitle "Master Class Research"
	uv run research-buddy build examples/starter

lint:
	uv run ruff check . && uv run mypy . --explicit-package-bases

format:
	uv run ruff check --fix --unsafe-fixes . && uv run ruff format .

test: regen-example
	uv run pytest tests/ -v

test-all:
	uv run pytest tests/ -v --run-slow

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .mypy_cache .ruff_cache .pytest_cache
