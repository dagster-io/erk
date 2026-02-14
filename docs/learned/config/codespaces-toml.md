---
title: Codespaces TOML Configuration
read_when:
  - "modifying codespace configuration or TOML schema"
  - "debugging codespace registration or lookup failures"
  - "adding fields to codespaces.toml"
tripwires:
  - action: "reading from or writing to ~/.erk/codespaces.toml directly"
    warning: "Use CodespaceRegistry gateway instead. All codespace config access should go through the gateway for testability."
  - action: "using the field name 'default' in codespaces.toml"
    warning: "The actual field name is 'default_codespace', not 'default'. Check RealCodespaceRegistry in real.py for the schema."
content_type: third_party_reference
last_audited: "2026-02-08 13:55 PT"
audit_result: edited
---

# Codespaces TOML Configuration

## Purpose

`~/.erk/codespaces.toml` is a **name-mapping file** — it maps friendly names to GitHub Codespace identifiers. It does not create, delete, or manage codespace lifecycle (that's `gh codespace create/delete`). Erk only uses it to resolve which remote environment to target for execution.

## File Format

The TOML schema is defined in `RealCodespaceRegistry` and its helper functions.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/codespace_registry/real.py, _save_toml_data -->

```toml
schema_version = 1
default_codespace = "dev"

[codespaces.dev]
gh_name = "user-codespace-abc123"
created_at = "2024-01-15T10:30:00Z"
```

Key details:

- **`schema_version`** (required): Always `1`. Set by `SCHEMA_VERSION` constant in `real.py`.
- **`default_codespace`** (optional): Friendly name of the default codespace. Omitted (not set to empty string) when no default exists.
- **`[codespaces.<name>]`**: Each entry requires `gh_name` (GitHub identifier from `gh codespace list`) and `created_at` (ISO 8601 timestamp of registration time).

## CLI Usage

The CLI commands operate through the `erk codespace` group. The actual subcommands are `setup`, `connect`, `list`, `remove`, `set-default`, and `run`.

```bash
# Create and register a new codespace (also opens SSH for Claude login)
erk codespace setup dev

# Set the default codespace
erk codespace set-default dev

# List all registered codespaces
erk codespace list

# Remove a codespace from the registry (does not delete the GitHub Codespace)
erk codespace remove dev

# Connect to a codespace
erk codespace connect dev
```

See `src/erk/cli/commands/codespace/` for the full command implementations.

## Design Decisions

### Why a Separate File from config.toml

Codespace registration is a distinct concern from global erk configuration. The `ErkInstallation` gateway provides `get_codespaces_config_path()` to resolve the file location, keeping the path derivation centralized while the schema ownership lives in `CodespaceRegistry`.

### Read-Only ABC, Standalone Mutations

The `CodespaceRegistry` ABC is read-only. Mutation functions (`register_codespace`, `unregister_codespace`, `set_default_codespace`) are standalone functions in `real.py` that save to disk and return a **new** registry instance. This works because:

1. Reads dominate — most code only looks up codespaces
2. Mutations are rare CLI-only operations (setup/teardown)
3. Fakes stay simpler without needing to implement mutation tracking on the ABC

See `RealCodespaceRegistry` in `packages/erk-shared/src/erk_shared/gateway/codespace_registry/real.py` for the full implementation.

### Dual TOML Libraries

The implementation uses `tomllib` (stdlib, read-only) for loading and `tomlkit` (third-party, format-preserving) for saving. This ensures user comments and formatting survive round-trips through mutation operations.

## Validation

The CodespaceRegistry gateway validates:

- **TOML syntax** — File must be valid TOML (via `tomllib.loads`)
- **Required fields** — Each codespace must have `gh_name` and `created_at` (enforced by key access in `_codespace_from_dict`)
- **Unique names** — `register_codespace` raises `ValueError` if a name already exists
- **Default resolution** — If `default_codespace` names a codespace that doesn't exist, `get_default()` returns `None` (soft failure, not a validation error)

## Anti-Patterns

**WRONG: Accessing the file path directly**

The config path comes from `ErkInstallation.get_codespaces_config_path()`, not by constructing `Path.home() / ".erk" / "codespaces.toml"`. Hardcoding `Path.home()` breaks test isolation.

**WRONG: Adding the `default` field**

The field is `default_codespace`, not `default`. The existing doc and the sister `codespace-registry.md` gateway doc historically used `default`, but the actual implementation has always used `default_codespace`.

## Relationship to Other Gateways

| Gateway             | Responsibility                              |
| ------------------- | ------------------------------------------- |
| `CodespaceRegistry` | Name-to-identifier mapping (this file)      |
| `Codespace`         | SSH operations against a resolved codespace |
| `ErkInstallation`   | Provides the config file path               |

## Related Topics

- [CodespaceRegistry Gateway](../gateway/codespace-registry.md) — programmatic access patterns
