# erk Installation Testing

Docker-based environment for manually testing erk installation and upgrade scenarios.

## Purpose

Test scenarios that are hard to catch with automated tests:

1. **Fresh install**: User installs erk on a repo that already has `.erk/` config
2. **Upgrade**: User upgrades erk (via `uv tool upgrade`) with older config formats

## Quick Start

```bash
# Build the test image (one-time, or when Dockerfile changes)
make install-test-image

# Get an interactive shell for exploration
make install-test-shell

# Inside the container:
# 1. Install erk from mounted source
uv tool install -e /home/testuser/erk-source

# 2. Create a test repo with existing config
setup_test_repo

# 3. Test erk commands
cd /home/testuser/test-repo
erk status
erk wt list
```

## Test Scenarios

### Fresh Install Test

Tests installing erk on a repo that already has `.erk/` configuration.

```bash
make install-test-fresh
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
make install-test-upgrade
```

Note: Until erk is published to PyPI, this behaves the same as fresh install.
Future: Install old version from PyPI first, then upgrade to source version.

### Interactive Shell

For free-form exploration and custom test scenarios:

```bash
make install-test-shell
```

Available helper functions:

- `install_erk` - Install erk from mounted source
- `setup_test_repo` - Create test repo with existing .erk config

## Architecture

```
dev/install-test/
├── Dockerfile              # Full toolchain image
├── entrypoint.sh           # Test scenario runner
├── fixtures/
│   └── configs/
│       └── current/        # Current config format
│           └── .erk/
│               └── config.toml
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

To test older config formats or migration scenarios:

1. Create a new directory under `fixtures/configs/` (e.g., `v0.3/`)
2. Add the old config files
3. Update `entrypoint.sh` to use the fixture for upgrade testing
