# erk Installation Testing

Docker-based environment for manually testing erk installation and upgrade scenarios.

## Purpose

Test scenarios that are hard to catch with automated tests:

1. **Fresh install**: User installs erk on a repo that already has `.erk/` config
2. **Upgrade**: User upgrades erk (via `uv tool upgrade`) with older config formats
3. **Repo-specific**: Test with configs that mimic real repositories (e.g., dagster-compass)

## Quick Start

```bash
# Build the test image (one-time, or when Dockerfile changes)
erk-dev install-test build

# Get an interactive shell for exploration
erk-dev install-test shell

# Inside the container:
# 1. Install erk from mounted source
uv tool install -e /home/testuser/erk-source

# 2. Create a test repo with existing config
setup_test_repo

# 3. Test erk commands
cd /home/testuser/test-repo
erk doctor
erk wt list
```

## Test Scenarios

### Fresh Install Test

Tests installing erk on a repo that already has `.erk/` configuration.

```bash
erk-dev install-test fresh
```

This will:

1. Create a test git repository
2. Copy current config fixtures to `.erk/`
3. Install erk from your mounted source
4. Run basic erk commands
5. Drop to shell for manual exploration

### Upgrade Test

Tests upgrading from an older erk version.

```bash
erk-dev install-test upgrade
```

Note: Until erk is published to PyPI, this behaves the same as fresh install.
Future: Install old version from PyPI first, then upgrade to source version.

### Repo-Specific Tests

Test with configurations that mimic real repositories:

```bash
# List available repo fixtures
erk-dev install-test list-repos

# Test with dagster-compass configuration
erk-dev install-test repo dagster-compass
```

This creates a test repo with:

- `.erk/` config matching the real repo
- `.claude/` settings including hooks and permissions
- Version requirements file

### Interactive Shell

For free-form exploration and custom test scenarios:

```bash
erk-dev install-test shell
```

Available helper functions:

- `install_erk` - Install erk from mounted source
- `setup_test_repo [name]` - Create test repo (default: current config)
- `setup_repo_fixture <name>` - Create test repo from repo fixture
- `list_repo_fixtures` - List available repo fixtures
- `run_erk_tests` - Run standard erk command tests

## Architecture

```
dev/install-test/
├── Dockerfile              # Full toolchain image
├── entrypoint.sh           # Test scenario runner
├── fixtures/
│   ├── configs/
│   │   └── current/        # Current config format
│   │       └── .erk/
│   │           └── config.toml
│   └── repos/
│       └── dagster-compass/  # dagster-compass fixture
│           ├── .erk/
│           │   ├── config.toml
│           │   ├── required-erk-uv-tool-version
│           │   └── prompt-hooks/
│           └── .claude/
│               ├── settings.json
│               ├── agents/
│               ├── commands/
│               └── skills/
└── README.md               # This file
```

### Container Contents

- Python 3.11
- git
- uv (package manager)
- gh (GitHub CLI)
- gt (Graphite CLI)
- claude (Claude CLI)

### Source Mounting

Your local erk source is mounted read-only at `/home/testuser/erk-source`.
This means:

- No Docker rebuild needed when you change code
- Fast iteration: edit code, re-run `uv tool install -e ...`
- Source files can't be accidentally modified

## Adding Test Fixtures

### Generic Config Fixtures

To test older config formats or migration scenarios:

1. Create a new directory under `fixtures/configs/` (e.g., `v0.3/`)
2. Add the `.erk/` config files
3. Use `setup_test_repo v0.3` in the shell

### Repo-Specific Fixtures

To add a new repository fixture:

1. Create a directory under `fixtures/repos/<repo-name>/`
2. Add `.erk/` directory with:
   - `config.toml` - erk configuration
   - `required-erk-uv-tool-version` (optional) - version constraint
   - `prompt-hooks/` (optional) - any prompt hooks
3. Add `.claude/` directory with:
   - `settings.json` - Claude Code settings with hooks
   - `agents/`, `commands/`, `skills/` as needed
4. Rebuild the Docker image: `erk-dev install-test build`
5. Test with: `erk-dev install-test repo <repo-name>`
