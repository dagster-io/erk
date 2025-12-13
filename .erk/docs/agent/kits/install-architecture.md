---
title: Kit Install Architecture
read_when:
  - modifying kit install/update logic
  - debugging kit installation
  - understanding kit resolution
tripwires:
  - action: "modifying kit install/update logic"
    warning: "Understand the idempotent design and atomic hook updates. The install command handles both fresh installs and updates with rollback on failure."
---

# Kit Install Architecture

Internal architecture documentation for the consolidated `erk kit install` command.

## Idempotent Design

The install command is fully idempotent:

- **Kit not installed** → Fresh install workflow
- **Kit installed, version differs** → Update workflow (sync)
- **Kit installed, version matches** → No-op (reports "already up to date")
- **Kit installed + `--force`** → Reinstall regardless of version

This eliminates the need for separate `install` vs `update` vs `sync` commands.

## Workflow Routing

```
install(kit_id)
    │
    ├── kit_id in config.kits?
    │       │
    │       ├── Yes → _handle_update_workflow()
    │       │           │
    │       │           ├── check_for_updates()
    │       │           ├── sync_kit()
    │       │           └── _process_update_result()
    │       │
    │       └── No → _handle_fresh_install()
    │                   │
    │                   ├── resolver.resolve()
    │                   └── install_kit_to_project()
```

## Multi-Source Resolution

The resolver chains multiple kit sources (bundled kits, standalone packages) and iterates them in order, returning the first match. See `src/erk/kits/sources/resolver.py` for implementation.

## Hook Installation

Hooks are installed by **directly editing `.claude/settings.json`** in place. This is somewhat counterintuitive and carries risk, but is the only way to register hooks with Claude Code since there's no API for dynamic hook registration.

**How it works:**

1. Kit manifest declares hooks with trigger events and script paths
2. During installation, hook entries are added to the `hooks` section in `settings.json`
3. Hook scripts are copied to `.claude/hooks/<kit-id>/`
4. Settings file is updated to reference these scripts

**Atomic updates with rollback:**

Because editing `settings.json` is risky, the install command implements atomic updates:

- Backs up current `settings.json` and hooks directory before changes
- On failure, restores the backup to prevent partial state

**Debugging features:**

Many kits include hooks that provide debugging and development conveniences (e.g., session ID injection, tripwire reminders). These hooks may be referenced in other documentation. Use `erk kit show <kit-id>` to see what hooks a kit provides.

## Exception Handling

Kit resolution errors inherit from `DotAgentNonIdealStateException` for clean CLI error display without stack traces. See `src/erk/kits/sources/exceptions.py` for the complete exception hierarchy.

## Key Implementation Details

### Version Comparison

Currently uses simple string comparison (`!=`). Version format is not enforced, but semantic versioning is recommended.

### Config Persistence

- Project config stored in `.claude/kits.json`
- Settings stored in `.claude/settings.json`
- Both updated atomically per operation

### Registry Updates

After installation, the registry is updated (non-blocking):

1. Generate registry entry content
2. Create kit-specific registry file
3. Add kit to main registry (fresh install only)

Registry failures are warnings, not errors.

## See Also

- [CLI Reference](cli-reference.md) - User-facing command documentation
- [Code Architecture](code-architecture.md) - General kit code structure
