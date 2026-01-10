# Plan: Write Install-Test Guide

## Task
Create a guide documenting how to use `erk-dev install-test` for testing installation processes.

## Location
`docs/learned/testing/install-test.md`

## Content

```markdown
---
title: "Install-Test Guide"
read_when:
  - "testing erk installation"
  - "testing upgrade scenarios"
  - "adding install-test fixtures"
  - "debugging installation issues"
---

# Install-Test Guide

Docker-based testing environment for validating erk installation and upgrade scenarios.

## Why Install-Test?

Catches real-world issues that automated tests miss:
- Installing erk on repos with existing `.erk/` configuration
- Upgrade paths from older versions
- Repository-specific configuration edge cases

## Quick Start

```bash
# Build image (one-time)
erk-dev install-test build

# Fresh install test
erk-dev install-test fresh

# Interactive exploration
erk-dev install-test shell
```

## Commands

| Command | Purpose |
|---------|---------|
| `build` | Build Docker image (required first) |
| `shell` | Interactive bash with helper functions |
| `fresh` | Test fresh install scenario |
| `upgrade` | Test upgrade scenario |
| `repo <name>` | Test with repo-specific fixture |
| `ready <scenario>` | Setup scenario, drop to shell (no auto-tests) |
| `list-repos` | List available repo fixtures |

## Shell Helper Functions

Inside the container, these functions are available:

```bash
install_erk_from_source  # Install from mounted source
setup_test_repo          # Create test repo with current config
setup_repo_fixture <name>  # Create test repo from fixture
list_repo_fixtures       # List available fixtures
run_erk_tests           # Run standard command tests
```

## Workflows

### Testing Fresh Install

```bash
erk-dev install-test fresh
# Runs: install_erk, setup_test_repo, run_erk_tests
# Drops to shell for exploration
```

### Testing Specific Repository

```bash
erk-dev install-test repo dagster-compass
# Uses fixtures/repos/dagster-compass/ config
```

### Free-Form Exploration

```bash
erk-dev install-test ready blank
# Sets up blank scenario, drops to shell
# Run any erk commands you want
```

## Adding Fixtures

### Config Fixtures (`fixtures/configs/`)

For testing configuration migrations:

```
fixtures/configs/
├── current/     # Current config format
│   └── .erk/
│       └── config.toml
└── v0.3/        # Add older versions as needed
```

### Repo Fixtures (`fixtures/repos/`)

Real repository snapshots:

```
fixtures/repos/
├── blank/              # Fresh project (no config)
├── dagster-compass/    # Real repo snapshot
│   ├── .erk/
│   │   ├── config.toml
│   │   └── required-erk-uv-tool-version
│   └── .claude/
│       └── settings.json
```

To add a new repo fixture:
1. Create `fixtures/repos/<name>/`
2. Copy `.erk/` and `.claude/` directories from real repo
3. Rebuild: `erk-dev install-test build`

## Key Design Points

- **Source mounted read-only**: No rebuild needed when code changes
- **Isolated environment**: Docker container prevents system pollution
- **Extensible fixtures**: Add configs and repos as needed
- **Helper functions**: Automate common testing tasks

## Files

- **Command**: `packages/erk-dev/src/erk_dev/commands/install_test/command.py`
- **Docker**: `dev/install-test/Dockerfile`
- **Entrypoint**: `dev/install-test/entrypoint.sh`
- **Fixtures**: `dev/install-test/fixtures/`
```

## Verification

1. Run `erk docs validate` to check frontmatter
2. Run `erk docs sync` to regenerate index
3. Verify the document appears in `docs/learned/index.md`