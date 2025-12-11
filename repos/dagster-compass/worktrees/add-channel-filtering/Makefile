prettier:
	prettier --write '**/*.{md,yml,yaml,tsx}' --ignore-path .gitignore '!**/*.config.yaml'

prettier-check:
	prettier --check '**/*.{md,yml,yaml,tsx}' --ignore-path .gitignore '!**/*.config.yaml'

ruff:
	-uv run ruff check --fix .
	uv run ruff format .

ruff-check:
	uv run ruff check .
	uv run ruff format --check .

unsafe-ruff:
	-uv run ruff check --fix . --unsafe-fixes
	uv run ruff format .

pyright:
	cd packages/csbot && uv run pyright src tests

test:
	cd packages/csbot && uv run pytest -n auto tests/ --ignore=tests/integration/

test-integration:
	cd packages/csbot && uv run pytest -n auto tests/integration/

test-webapp:
	cd packages/csbot && uv run pytest -n auto tests/integration/webapp/

test-all:
	cd packages/csbot && uv run pytest -n auto tests/

# Frontend targets
dev-ui:
	cd packages/ui && yarn dev

build-ui:
	cd packages/ui && yarn build

lint-ui:
	cd packages/ui && yarn lint && npx prettier --check .

# Backend dev server
dev-backend:
	cd packages/csbot && uv run slackbot start --config ../../local.csbot.config.yaml

# Run backend (default for backwards compatibility)
dev: dev-backend

all-ci: prettier-check ruff-check pyright test-all

update-erk-tools:
	-uv pip uninstall dot-agent-kit erk
	uv cache clean dot-agent-kit
	uv cache clean erk
	uv lock --upgrade-package dot-agent-kit --upgrade-package erk
	uv sync --group dev

pipeline:
	@cat .buildkite/pipeline.dhall | dhall-to-yaml
