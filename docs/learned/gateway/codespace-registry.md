---
title: CodespaceRegistry Gateway — Read-Only ABC with Standalone Mutations
last_audited: "2026-02-17 00:00 PT"
audit_result: clean
read_when:
  - "working with GitHub Codespace registration or lookup"
  - "adding a gateway that separates read-only ABC from mutation functions"
  - "choosing between ABC methods vs standalone functions for gateway operations"
tripwires:
  - action: "reading from or writing to ~/.erk/codespaces.toml directly"
    warning: "Use CodespaceRegistry gateway instead. All codespace configuration should go through this gateway for testability."
  - action: "adding a mutation method to the CodespaceRegistry ABC"
    warning: "Mutations are standalone functions in real.py, not ABC methods. This is intentional — see the design rationale below."
---

# CodespaceRegistry Gateway

## Why a Separate Read/Write Split?

Most gateways put all operations on the ABC. CodespaceRegistry deliberately keeps mutations as standalone functions outside the ABC. The reasoning:

1. **Reads dominate at runtime** — CLI commands, resolution helpers, and remote execution flows all just look up codespaces. The ABC contract reflects this actual usage pattern.
2. **Mutations are CLI-only setup operations** — registering, unregistering, and setting defaults happen during `erk codespace setup` / `erk codespace remove` / `erk codespace set-default`. They never appear in pipeline or agent code.
3. **Simpler fakes** — the fake only needs to implement the read interface for ABC conformance. It provides mutation helpers for test setup convenience, but these aren't forced by the ABC contract.
4. **Immutable real implementation** — `RealCodespaceRegistry` receives fully-loaded data at construction time. Standalone mutation functions save to disk and return a _new_ registry instance, preserving immutability.

This pattern is shared with `ErkInstallation` gateway, which similarly separates read-heavy ABC operations from infrequent filesystem mutations.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/codespace_registry/abc.py, CodespaceRegistry -->

See `CodespaceRegistry` ABC in `packages/erk-shared/src/erk_shared/gateway/codespace_registry/abc.py` for the read-only interface.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/codespace_registry/real.py, register_codespace -->

See standalone mutation functions (`register_codespace`, `unregister_codespace`, `set_default_codespace`) in `packages/erk-shared/src/erk_shared/gateway/codespace_registry/real.py`.

## Codespace Resolution Pattern

A shared resolution helper (`resolve_codespace`) encapsulates the lookup-by-name-or-default pattern used by both `connect` and `run` commands. This prevents each CLI command from reimplementing the same fallback logic and error messaging.

<!-- Source: src/erk/cli/commands/codespace/resolve.py, resolve_codespace -->

See `resolve_codespace()` in `src/erk/cli/commands/codespace/resolve.py`.

## Configuration File Format

Storage uses `~/.erk/codespaces.toml`. The path is obtained from `ErkInstallation.get_codespaces_config_path()`, never hardcoded — this keeps filesystem access testable.

```toml
schema_version = 1
default_codespace = "dev"

[codespaces.dev]
gh_name = "user-codespace-abc123"
created_at = "2024-01-15T10:30:00+00:00"

[codespaces.staging]
gh_name = "user-codespace-xyz789"
created_at = "2024-01-20T14:00:00+00:00"
```

## When to Use Which Gateway

| Need                                             | Gateway                                              | Why                                    |
| ------------------------------------------------ | ---------------------------------------------------- | -------------------------------------- |
| Look up registered codespaces by name or default | `CodespaceRegistry` (this gateway)                   | Registration data, read-only           |
| Register/unregister/set-default codespace        | Standalone functions in `codespace_registry/real.py` | CLI-only mutations                     |
| Execute SSH commands in a codespace              | `Codespace` gateway                                  | SSH operations are a different concern |
| Get the config file path                         | `ErkInstallation` gateway                            | Owns all `~/.erk/` path resolution     |

## Related Topics

- [Codespaces TOML Configuration](../config/codespaces-toml.md) — file format details
- [Gateway Inventory](../architecture/gateway-inventory.md) — all available gateways
