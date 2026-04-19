.PHONY: lint format test test-all clean sync regen-example build publish version-sync check-version-sync update-skills

sync:
	uv sync --extra dev

build:
	rm -rf dist/ && uv run python -m build

publish: build
	uv run twine upload dist/*

version-sync:
	uv run scripts/sync_version.py

check-version-sync:
	uv run scripts/check_version_sync.py

regen-example:
	uv run research-buddy build src/research_buddy/starter.json --output starter-example/starter.html --no-versioning

lint: check-version-sync
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

update-skills:
	git subtree pull --prefix .claude/skills shared-skills main --squash
