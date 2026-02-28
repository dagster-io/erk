---
title: Upgrade Workflow
read_when:
  - "modifying erk init --upgrade behavior"
  - "adding new entries to REQUIRED_GITIGNORE_ENTRIES"
  - "working with the erk doctor --check-hooks flag"
  - "understanding how erk upgrades existing repositories"
tripwires:
  - action: "adding a new required gitignore entry"
    warning: "Add to REQUIRED_GITIGNORE_ENTRIES in src/erk/core/init_utils.py:8. The upgrade path in init/main.py automatically syncs these entries."
    score: 4
---

# Upgrade Workflow

`erk init --upgrade` updates an already-initialized repository without rewriting its config.toml. This is the recommended way to update erk artifacts, capabilities, and gitignore entries after upgrading the erk tool.

## Upgrade Path

<!-- Source: src/erk/cli/commands/init/main.py:541-592 -->

The upgrade path executes five steps in sequence:

### 1. Artifact Sync (force=True)

Syncs all erk artifacts (hooks, commands, skills) to the repository with `force=True`, ensuring all files are updated regardless of local modifications.

### 2. Capability Re-installation

Re-installs all required capabilities (e.g., hooks) for the configured backend. Each capability reports success or failure independently.

### 3. Gitignore Entry Sync

<!-- Source: src/erk/core/init_utils.py:8, REQUIRED_GITIGNORE_ENTRIES -->

Checks for missing entries from `REQUIRED_GITIGNORE_ENTRIES` (3 entries):

```python
REQUIRED_GITIGNORE_ENTRIES: list[str] = [".erk/scratch/", ".erk/config.local.toml", ".erk/bin/"]
```

In interactive mode, prompts the user before adding missing entries. In non-interactive mode, adds them automatically.

### 4. Version File Update

Writes the current erk version to `.erk/required-erk-uv-tool-version`, enabling version mismatch detection.

### 5. Completion

Prints "Upgrade complete!" and returns without running the full init flow.

## Doctor --check-hooks

<!-- Source: src/erk/cli/commands/doctor.py:110 -->

The `erk doctor` command has an opt-in `--check-hooks` flag that includes hook execution health checks in its diagnostic output. This is separate from the upgrade workflow but related to ensuring hooks are functioning correctly after an upgrade.

## Related Documentation

- [Erk Architecture Patterns](../architecture/erk-architecture.md) — Core architecture principles
