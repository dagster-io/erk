# Monorepo Structure

This repository contains two separate Python packages organized in the `packages/` directory:

## Package: `csbot`

**Location**: `packages/csbot/`

The core Compass bot system including:

- AI-powered data analysis bot
- Slack bot functionality
- Context store and engine
- CLI tools (`slackbot`, `ctx-admin`, `compass-dev`)

## Package: `compass-admin-panel`

**Location**: `packages/compass-admin-panel/`

Minimal web server for future admin functionality.

**Features**:

- Simple "Hello World" web interface
- Health check endpoint
- Built with aiohttp (lightweight and fast)

**Dependencies**:

- Minimal dependencies (only aiohttp)
- No dependency on csbot - fully standalone

## Development Workflow

### Quick Start (Recommended)

```bash
# From project root - sets up workspace with both packages
uv sync --group dev

# All CLI commands available immediately
uv run slackbot start
uv run ctx-admin --help
uv run compass-dev --help
uv run compass-admin --help
```

The root-level workspace automatically includes both csbot and compass-admin-panel as dependencies, so you can run all CLI commands directly from the project root without navigating to subdirectories.

### Package-Specific Development

Each package has its own:

- `pyproject.toml` with separate dependencies
- Development environment via `uv sync --group dev`
- Independent versioning and releases

```bash
# Work on specific packages
cd packages/csbot && uv sync --group dev
cd packages/compass-admin-panel && uv sync --group dev
```

### Running Admin Panel

**Local Development:**

```bash
# From root (after uv sync --group dev)
uv run compass-admin

# Or from package directory
cd packages/compass-admin-panel && uv run compass-admin
```

**Production Deployment:**

- **Staging**: Deployed as `compass-admin-panel-staging` private service on Render
- **Production**: Uses `compass-admin-panel-prod.Dockerfile` with production config
- **Docker**: Environment-specific Dockerfiles with csbot config mounting
- **Access**: Internal-only (pserv) - not exposed to public internet

## Repository Structure

```
dagster-compass/
├── pyproject.toml            # Root workspace configuration
├── uv.lock                   # Root workspace lock file
├── packages/           # All Python packages
│   ├── csbot/               # Main bot system
│   │   ├── pyproject.toml
│   │   ├── uv.lock
│   │   └── src/csbot/
│   └── compass-admin-panel/ # Admin web interface
│       ├── pyproject.toml
│       ├── uv.lock
│       └── src/compass_admin_panel/
├── data/                    # Sample data
├── tests/                   # Tests
└── docs/                    # Documentation
```

## Key Benefits

1. **Single Environment**: Root-level `uv sync` gives you access to all CLI tools immediately
2. **Separate Packages**: Each package maintains independent dependencies and versioning
3. **Clean Organization**: `packages/` separates Python packages from data, tests, and docs
4. **Consistent Framework**: Both packages use aiohttp for web functionality
