.PHONY: lint format test test-all clean sync regen-example regen-md-example regen-examples build publish publish-force version-sync check-version-sync update-skills

sync:
	uv sync --extra dev

build:
	rm -rf dist/ && uv run python -m build

# Refuse to upload when the corresponding v* tag already exists on origin —
# .github/workflows/release.yml is the canonical publish path (trusted
# publishing via OIDC) and a local upload would race it and fail with a
# PyPI 400 "File already exists". Use 'make publish-force' to bypass when
# the workflow is unavailable (e.g., GitHub Actions outage, broken
# OIDC config, re-publishing after the workflow failed past the build job).
publish:
	@VER=$$(uv run python -c "import tomllib, pathlib; print(tomllib.loads(pathlib.Path('pyproject.toml').read_text())['project']['version'])"); \
	TAG="v$$VER"; \
	if git ls-remote --tags origin "$$TAG" 2>/dev/null | grep -q "refs/tags/$$TAG"; then \
		echo "ERROR: tag $$TAG already exists on origin."; \
		echo "       .github/workflows/release.yml handles PyPI publishing on tag push."; \
		echo "       Running 'twine upload' here would race the workflow and fail."; \
		echo ""; \
		echo "       If you genuinely need to bypass (workflow broken / re-publishing"; \
		echo "       after a build-job pass + publish-job fail), run:"; \
		echo "           make publish-force"; \
		echo ""; \
		echo "       See RELEASE.md for the canonical tag/push flow."; \
		exit 1; \
	fi; \
	$(MAKE) publish-force

publish-force: build
	uv run twine upload dist/*

version-sync:
	uv run scripts/sync_version.py

check-version-sync:
	uv run scripts/check_version_sync.py

regen-example:
	uv run research-buddy build src/research_buddy/starter.json --output starter-example/starter.html --no-versioning

regen-md-example:
	uv run research-buddy build src/research_buddy/starter.md --output starter-example/starter-md.html --no-versioning

regen-examples: regen-example regen-md-example

lint: check-version-sync
	uv run ruff check . && uv run ruff format --check . && uv run mypy . --explicit-package-bases

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
	git subtree pull --prefix .claude/skills https://github.com/nuncaeslupus/my-skills.git main --squash
