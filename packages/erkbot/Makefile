ERK_LOCAL_PATH ?= $(HOME)/src/erk

.PHONY: dev erk-version prettier ruff ty

dev:
	@if [ -d "$(ERK_LOCAL_PATH)" ]; then \
		echo "Using local editable erk: $(ERK_LOCAL_PATH)"; \
		uv run --with-editable "$(ERK_LOCAL_PATH)" erkbot; \
	else \
		echo "Using PyPI erk dependency"; \
		uv run erkbot; \
	fi

erk-version:
	@if [ -d "$(ERK_LOCAL_PATH)" ]; then \
		echo "Using local editable erk: $(ERK_LOCAL_PATH)"; \
		uv run --with-editable "$(ERK_LOCAL_PATH)" erk --version; \
	else \
		echo "Using PyPI erk dependency"; \
		uv run erk --version; \
	fi

prettier:
	npx prettier --write "**/*.md"

ruff:
	uv run ruff format .

ty:
	uv run ty check .
