---
title: CodespaceRegistry Gateway
read_when:
  - "working with GitHub Codespaces"
  - "implementing codespace registration"
  - "managing remote execution environments"
tripwires:
  - action: "reading from or writing to ~/.erk/codespaces.toml directly"
    warning: "Use CodespaceRegistry gateway instead. All codespace configuration should go through this gateway for testability."
---

# CodespaceRegistry Gateway

Gateway for managing registered GitHub Codespaces used for remote Claude Code execution.

## Overview

**Location:** `packages/erk-shared/src/erk_shared/gateway/codespace_registry/`

**Purpose:** Abstracts codespace registration and lookup operations. Provides read-only interface with standalone mutation functions.

**Storage:** Configuration is persisted to `~/.erk/codespaces.toml`

## Architecture

The gateway follows the standard 3-file pattern:

- `abc.py` - Abstract interface with `RegisteredCodespace` type
- `real.py` - Production implementation using TOML file
- `fake.py` - In-memory test implementation

## Domain Type

### RegisteredCodespace

```python
@dataclass(frozen=True)
class RegisteredCodespace:
    name: str           # Friendly name for the codespace (used as key)
    gh_name: str        # GitHub codespace name (e.g., "user-codespace-abc123")
    created_at: datetime  # When the codespace was registered
```

Frozen dataclass representing a registered GitHub Codespace for remote execution.

## Read-Only Interface (ABC Methods)

The ABC provides read-only methods:

### list_codespaces() -> list[RegisteredCodespace]

List all registered codespaces.

**Returns:** List of registered codespaces, may be empty.

### get(name: str) -> RegisteredCodespace | None

Get a codespace by its friendly name.

**Args:**

- `name`: Friendly name of the codespace

**Returns:** `RegisteredCodespace` if found, `None` otherwise.

### get_default() -> RegisteredCodespace | None

Get the default codespace.

**Returns:** The default codespace if one is set and exists, `None` otherwise.

### get_default_name() -> str | None

Get the name of the default codespace.

**Returns:** The default codespace name if set, `None` otherwise.

## Mutation Functions (Standalone)

Mutation operations are **standalone functions** in `real.py`, not on the ABC:

### register_codespace(name: str, gh_name: str) -> None

Register a new codespace.

**Args:**

- `name`: Friendly name for the codespace
- `gh_name`: GitHub codespace name

**Raises:** Error if codespace with that name already exists.

### unregister_codespace(name: str) -> None

Remove a codespace registration.

**Args:**

- `name`: Friendly name of the codespace to remove

**Raises:** Error if codespace doesn't exist.

### set_default_codespace(name: str | None) -> None

Set the default codespace.

**Args:**

- `name`: Friendly name of the codespace, or `None` to clear default

**Raises:** Error if name is provided but codespace doesn't exist.

## Why Standalone Mutations?

The CodespaceRegistry pattern uses standalone mutation functions instead of ABC methods because:

1. **Mutations are rare** - registering/unregistering happens infrequently (setup/teardown)
2. **Reads dominate** - most code just needs to look up registered codespaces
3. **Simpler fakes** - test fakes don't need mutation tracking properties
4. **Clear separation** - mutations are clearly CLI-only operations

This pattern is similar to `ErkInstallation` gateway.

## Usage Patterns

### Reading Codespaces

```python
def select_codespace(ctx: ErkContext, name: str | None) -> RegisteredCodespace:
    registry = ctx.codespace_registry

    if name:
        codespace = registry.get(name)
        if codespace is None:
            raise ValueError(f"Codespace '{name}' not found")
        return codespace

    # Use default
    codespace = registry.get_default()
    if codespace is None:
        raise ValueError("No default codespace set")

    return codespace
```

### Registering Codespaces

```python
from erk_shared.gateway.codespace_registry.real import register_codespace

def register_command(name: str, gh_name: str) -> None:
    """CLI command to register a codespace."""
    register_codespace(name, gh_name)
    print(f"Registered codespace '{name}' -> {gh_name}")
```

## Fake Features

`FakeCodespaceRegistry` provides:

- **In-memory codespace storage** - configurable test data
- **Configurable default** - tests can set/clear default
- **No filesystem I/O** - tests run without touching `~/.erk/`

## Configuration File Format

`~/.erk/codespaces.toml`:

```toml
# Default codespace name (optional)
default = "dev"

# Registered codespaces
[codespaces.dev]
gh_name = "user-codespace-abc123"
created_at = "2024-01-15T10:30:00Z"

[codespaces.staging]
gh_name = "user-codespace-xyz789"
created_at = "2024-01-20T14:00:00Z"
```

## When to Use

Use `ctx.codespace_registry` when:

- Looking up registered codespaces
- Getting the default codespace for remote execution
- Listing available codespaces for selection

Use standalone mutation functions when:

- Implementing CLI registration commands
- Setting up/tearing down codespace configurations

Don't use for:

- SSH operations (use `Codespace` gateway instead)
- Detecting active codespaces (not in scope)

## Related Topics

- [Codespace Gateway](../architecture/gateway-inventory.md#codespace-gatewaycodespace) - SSH operations
- [Gateway Inventory](../architecture/gateway-inventory.md) - All available gateways
- [Codespaces TOML Configuration](../config/codespaces-toml.md) - File format details
- [ErkInstallation Gateway](../architecture/gateway-inventory.md#erkinstallation-gatewayerk_installation) - Similar pattern
