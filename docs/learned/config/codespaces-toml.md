---
title: Codespaces TOML Configuration
read_when:
  - "working with codespace configuration"
  - "understanding ~/.erk/codespaces.toml format"
  - "troubleshooting codespace registration"
---

# Codespaces TOML Configuration

Configuration file format for registered GitHub Codespaces used for remote Claude Code execution.

## File Location

`~/.erk/codespaces.toml`

## Format

```toml
# Optional: Default codespace name
default = "dev"

# Registered codespaces
[codespaces.<name>]
gh_name = "<github-codespace-name>"
created_at = "<iso8601-timestamp>"
```

## Fields

### default (optional)

The friendly name of the default codespace. If set, this codespace will be used when no explicit codespace is specified.

**Type:** String
**Example:** `"dev"`

### codespaces.<name>

Each registered codespace is stored as a TOML table. The `<name>` is the friendly name used for lookup.

#### gh_name (required)

The GitHub Codespace name returned by `gh codespace list`.

**Type:** String
**Format:** Usually `<user>-<repo>-<random>`
**Example:** `"schrockn-myproject-abc123xyz"`

#### created_at (required)

ISO 8601 timestamp of when the codespace was registered.

**Type:** String
**Format:** ISO 8601 with timezone
**Example:** `"2024-01-15T10:30:00Z"`

## Example Configuration

```toml
# Set 'dev' as the default codespace
default = "dev"

# Development codespace
[codespaces.dev]
gh_name = "schrockn-erk-abc123"
created_at = "2024-01-15T10:30:00Z"

# Staging environment codespace
[codespaces.staging]
gh_name = "schrockn-erk-staging-xyz789"
created_at = "2024-01-20T14:00:00Z"

# Production testing codespace
[codespaces.prod-test]
gh_name = "schrockn-erk-prod-def456"
created_at = "2024-01-25T09:15:00Z"
```

## Usage

### Registering a Codespace

```bash
# Register a new codespace
erk codespace register dev "schrockn-erk-abc123"

# Set it as the default
erk codespace set-default dev
```

### Looking Up Codespaces

```bash
# List all registered codespaces
erk codespace list

# Get details of a specific codespace
erk codespace get dev

# Get the default codespace
erk codespace get-default
```

## Management

The file is automatically created when the first codespace is registered. Codespaces can be managed through:

1. **CLI commands** - `erk codespace` commands (preferred)
2. **Direct editing** - Manual TOML file editing (not recommended)

### Removing a Codespace

```bash
erk codespace unregister dev
```

### Clearing the Default

```bash
erk codespace set-default --clear
```

## Validation

The CodespaceRegistry gateway validates:

- **TOML syntax** - File must be valid TOML
- **Required fields** - Each codespace must have `gh_name` and `created_at`
- **Default exists** - If `default` is set, that codespace must exist
- **Unique names** - Codespace names must be unique

## Relationship to GitHub

**Important:** This file stores the **mapping** between friendly names and GitHub codespace names. It does NOT:

- Create codespaces (use `gh codespace create`)
- Delete codespaces (use `gh codespace delete`)
- Manage codespace lifecycle

It only tracks which codespaces erk should use for remote execution.

## Related Topics

- [CodespaceRegistry Gateway](../gateway/codespace-registry.md) - Programmatic access
- [Codespace Gateway](../architecture/gateway-inventory.md#codespace-gatewaycodespace) - SSH operations
- [Remote Execution](../erk/remote-execution.md) - Using codespaces for implementation
