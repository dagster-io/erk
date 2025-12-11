# Packages Directory

This directory contains independent Python packages that are part of the Compass ecosystem. Each package is designed to be self-contained with its own dependencies and CLI entry points.

## Package Structure Norms

All packages in this directory follow a consistent structure to maintain code organization and development workflow efficiency.

### Standard Directory Layout

```
packages/
├── {package-name}/
│   ├── pyproject.toml              # Package configuration and dependencies
│   ├── src/
│   │   └── {package_name}/         # Main package source (note: underscores)
│   │       ├── __init__.py         # Package initialization with __version__
│   │       ├── cli.py              # CLI entry point (if applicable)
│   │       └── ...                 # Additional modules
│   └── tests/                      # Test directory
│       ├── __init__.py
│       └── test_*.py               # Test modules
```

### Naming Conventions

- **Package directory**: Use kebab-case (e.g., `compass-admin-panel`)
- **Python package name**: Use underscores (e.g., `compass_admin_panel`)
- **PyPI project name**: Use kebab-case in `pyproject.toml` (e.g., `compass-admin-panel`)

### pyproject.toml Configuration

All packages must include:

#### Required Sections

```toml
[project]
name = "package-name"
version = "0.1.0"
description = "Brief package description"
authors = [
    {name = "Elementl", email = "info@elementl.com"}
]
requires-python = ">=3.13"
dependencies = [
    # List runtime dependencies
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/package_name"]
```

#### CLI Entry Points

For packages with CLI tools:

```toml
[project.scripts]
cli-command-name = "package_name.cli:cli"
```

#### Development Dependencies

```toml
[dependency-groups]
dev = [
    "pytest>=8.4.1",
    "pytest-asyncio>=0.23.0",
    "pyright>=1.1.389",
]
```

#### Code Quality Configuration

All packages must include the standard Ruff configuration for Python 3.13+ with modern typing enforcement:

```toml
[tool.ruff]
target-version = "py313"
line-length = 100

[tool.ruff.lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # pyflakes
    "I",      # isort
    "UP",     # pyupgrade (enforces modern Python syntax)
    "FA",     # flake8-future-annotations
    "TCH",    # flake8-type-checking
]

ignore = [
    "E501",   # line too long (temporarily disabled)
    "W291",   # trailing whitespace (temporarily disabled)
    "W293",   # blank line contains whitespace (temporarily disabled)
]

[tool.ruff.lint.pyupgrade]
keep-runtime-typing = false

[tool.ruff.lint.flake8-type-checking]
runtime-evaluated-base-classes = ["pydantic.BaseModel"]
strict = true

[tool.ruff.format]
quote-style = "double"
skip-magic-trailing-comma = false
```

### CLI Design Patterns

Packages providing CLI tools should:

- Use Click for command-line interfaces
- Provide helpful help text and examples
- Include version information via `@click.version_option()`
- Use command groups for multiple subcommands
- Follow the CLI entry point pattern: `cli-command-name = "package_name.cli:cli"`

### Testing Standards

- Use pytest for all testing
- Include basic CLI tests for packages with command-line interfaces
- Place tests in the `tests/` directory at package root
- Use descriptive test function names starting with `test_`

### Development Workflow Integration

- All packages work with `uv sync --group dev` for editable installation
- Changes to Python modules are immediately reflected (no re-sync needed)
- Re-sync only required when modifying `pyproject.toml`
- All packages must pass `make pyright` and `make ruff` checks

## Current Packages

### csbot

Core Compass Bot system providing context stores, Slack integration, and data analysis capabilities.

**CLI Commands**: `ctx-admin`, `slackbot`, `compass-dev`

### compass-admin-panel

Web administration interface for the Compass bot system.

**CLI Commands**: `compass-admin`

### csadmin

Compass System Administration CLI for managing system infrastructure and configuration.

**CLI Commands**: `csadmin`

## Adding New Packages

1. Create package directory using kebab-case naming
2. Set up the standard directory structure with `src/` layout
3. Create `pyproject.toml` following the standard configuration
4. Add package to workspace root `pyproject.toml`:
   - Add to `[tool.uv.workspace].members` list
   - Add to `[tool.uv.sources]` section: `package-name = { workspace = true }`
   - Add to `[project].dependencies` list
5. Implement CLI entry points if applicable
6. Add basic tests
7. Verify integration with `make pyright` and `make ruff`
