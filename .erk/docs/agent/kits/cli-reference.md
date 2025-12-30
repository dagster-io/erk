---
title: Kit CLI Reference
read_when:
  - using kit CLI commands
  - installing kits
  - updating kits
  - removing kits
  - searching for kits
---

# Kit CLI Reference

Quick reference for `erk kit` commands.

## Commands

### erk kit install

Install a kit or update it if already installed.

```bash
# Install or update a kit
erk kit install devrun

# Force reinstall even if version numbers do not indicate a reinstall is necessary
erk kit install devrun --force
```

**Idempotent Behavior**: Running `install` on an already-installed kit checks for updates and applies them. This is the only command needed for both installation and updates.

**Options**:

- `-f, --force`: Force reinstall even if version numbers do not indicate a reinstall is necessary

### erk kit list

List all installed kits in the current project.

```bash
# List installed kits
erk kit list

# Show artifact-level detail
erk kit list --artifacts
```

**Alias**: `erk kit ls`

**Options**:

- `-a, --artifacts`: Show artifact-level detail view

### erk kit check

Validate installed artifacts and check bundled kit sync status.

```bash
# Basic validation
erk kit check

# Verbose output
erk kit check --verbose
```

**Options**:

- `-v, --verbose`: Show detailed validation information

### erk kit show

Show detailed information about a kit (installed or available).

```bash
erk kit show gt
erk kit show dignified-python
```

Displays:

- Metadata (name, version, description, license, homepage)
- Artifacts grouped by type (skills, commands, agents, hooks)
- Hook definitions with trigger events
- Installation status (installed vs available version)

### erk kit remove

Remove an installed kit and all its artifacts.

```bash
erk kit remove github-workflows
```

**Alias**: `erk kit rm`

### erk kit search

Search for kits or list all available bundled kits.

```bash
# List all available kits
erk kit search

# Search by name or description
erk kit search github
erk kit search "workflow"
```

### erk kit exec

Execute scripts from bundled kits.

```bash
# Execute a kit script
erk exec impl-init --json
```

## Common Workflows

### Initial Setup

```bash
# Install commonly used kits
erk kit install devrun
erk kit install dignified-python
erk kit install gt
```

### Keeping Kits Updated

```bash
# Update a specific kit
erk kit install devrun

# Force reinstall to fix corruption
erk kit install devrun --force
```

### Checking Installation Health

```bash
# Verify artifacts are properly installed
erk kit check --verbose

# See what's installed
erk kit list --artifacts
```

## Error Scenarios

| Error                     | Meaning                                                |
| ------------------------- | ------------------------------------------------------ |
| `Kit not found`           | Kit ID doesn't exist in any source                     |
| `Kit no longer available` | Was installed from a source that no longer provides it |
| `Source access failed`    | Network or filesystem error accessing kit source       |
| `Resolution error`        | General resolution failure                             |

## See Also

- [Kit Architecture](install-architecture.md) - Internal architecture for maintainers
