# Plan: Consolidate dot-agent-kit into erk

## Summary

Merge `dot-agent` CLI functionality into `erk` using a facade-first approach. Consolidate configuration from `.agent/` into `.erk/`. Rename `kit_cli_commands` to `scripts` with new invocation `erk kit exec`.

## Key Decisions

| Decision              | Choice                                            |
| --------------------- | ------------------------------------------------- |
| Unified CLI name      | `erk`                                             |
| Config directory      | `.erk/` only (deprecate `.agent/`)                |
| Kit commands location | Top-level (`erk kit`, `erk artifact`, `erk hook`) |
| Migration approach    | Facade first, then gradual inlining               |
| Package fate          | Decide later (start with facade)                  |
| `dot-agent` CLI       | Remove directly (no deprecation needed)           |
| Kit script invocation | `erk kit exec <kit> <script>`                     |
| Script directory      | `scripts/` (rename from `kit_cli_commands/`)      |

## Terminology Clarification

| Old Term                | New Term       | Location                        |
| ----------------------- | -------------- | ------------------------------- |
| kit_cli_commands        | scripts        | `<kit>/scripts/`                |
| `dot-agent kit-command` | `erk kit exec` | CLI invocation                  |
| slash commands          | commands       | `.claude/commands/` (unchanged) |

## Phase 1: Facade Layer (First PR)

### Goal

Expose dot-agent commands via erk CLI without moving code.

### New Command Groups

```
erk kit install/list/remove/sync/show/exec
erk artifact list/show
erk hook install/remove/list
erk docs extract/sync
erk objective ...  (already exists as top-level)
```

Note: `objective` is already a top-level command group in erk.

### Files to Create

**`src/erk/cli/commands/kit/__init__.py`**

```python
"""Kit management commands - facade over dot-agent-kit."""
from dot_agent_kit.commands.kit.group import kit_group
```

**`src/erk/cli/commands/artifact/__init__.py`**

```python
"""Artifact management - facade over dot-agent-kit."""
from dot_agent_kit.commands.artifact.group import artifact_group
```

**`src/erk/cli/commands/hook/__init__.py`**

```python
"""Hook management - facade over dot-agent-kit."""
from dot_agent_kit.commands.hook.group import hook_group
```

### Files to Modify

**`src/erk/cli/cli.py`**

- Import and register new command groups
- Add `kit_exec_group` under `kit` (for `erk kit exec`)

**`src/erk/cli/help_formatter.py`**

- Add kit, artifact, hook to command_groups for organized help

**`packages/dot-agent-kit/pyproject.toml`**

- Remove `dot-agent` entry point (no deprecation period needed)

## Phase 2: Rename kit_cli_commands to scripts

### Goal

Rename the confusing `kit_cli_commands` terminology to `scripts`.

### Changes

**kit.yaml schema change:**

```yaml
# Before
kit_cli_commands:
  - name: pr-submit
    path: kit_cli_commands/gt/pr_submit.py

# After
scripts:
  - name: pr-submit
    path: scripts/gt/pr_submit.py
```

**Directory rename in each bundled kit:**

```
kit_cli_commands/ -> scripts/
```

**CLI invocation change:**

```bash
# Before
dot-agent kit-command gt pr-submit

# After
erk kit exec gt pr-submit
```

### Files to Modify

- `packages/dot-agent-kit/src/dot_agent_kit/commands/kit_command/group.py` - Rename to `kit_exec/`
- `packages/dot-agent-kit/src/dot_agent_kit/models/kit.py` - Schema for `scripts:`
- `packages/dot-agent-kit/src/dot_agent_kit/data/kits/*/kit.yaml` - All bundled kits
- `packages/dot-agent-kit/src/dot_agent_kit/data/kits/*/kit_cli_commands/` - Rename to `scripts/`
- `packages/dot-agent-kit/src/dot_agent_kit/hooks/installer.py` - Hook invocations

## Phase 3: Config Directory Migration

### Goal

Move all config from `.agent/` and `dot-agent.toml` into `.erk/`.

### Before/After Structure

```
# Before
.agent/
  kits/
    kit-registry.md
    <kit-id>/registry-entry.md
dot-agent.toml

# After
.erk/
  installed.toml              # renamed from dot-agent.toml
  kits/
    kit-registry.md
    <kit-id>/registry-entry.md
  project.toml           # unchanged
  scratch/               # unchanged
```

### Files to Modify

**`packages/dot-agent-kit/src/dot_agent_kit/io/state.py`**

- `_find_config_path()` → look for `.erk/installed.toml`
- `save_project_config()` → write to `.erk/installed.toml`

**`packages/dot-agent-kit/src/dot_agent_kit/io/registry.py`**

- All `.agent/kits/` paths → `.erk/kits/`

**`packages/dot-agent-kit/src/dot_agent_kit/commands/init.py`**

- Create `.erk/installed.toml` instead of `.agent/dot-agent.toml`

**`AGENTS.md`**

- Update `@.agent/kits/kit-registry.md` → `@.erk/kits/kit-registry.md`

### Migration Command

Add `erk kit migrate` command that:

1. Moves `dot-agent.toml` to `.erk/installed.toml`
2. Moves `.agent/kits/` to `.erk/kits/`
3. Updates @-include paths in `kit-registry.md`
4. Removes empty `.agent/` directory

## Phase 4: Hook Invocation Updates

### Goal

Update all hook invocations from `dot-agent kit-command` to `erk kit exec`.

### Files to Update

**`packages/dot-agent-kit/src/dot_agent_kit/hooks/installer.py`**

- Generate `erk kit exec` invocations instead of `dot-agent kit-command`

**All `kit.yaml` files:**

```yaml
# Before
hooks:
  - invocation: dot-agent kit-command erk session-id-injector-hook

# After
hooks:
  - invocation: erk kit exec erk session-id-injector-hook
```

**`.claude/settings.json`** (in erk repo)

- Update any hardcoded hook invocations

## Future Phases (Not in Initial Scope)

### Package Consolidation (If Decided)

If full absorption into erk is chosen later:

1. Move `packages/dot-agent-kit/src/dot_agent_kit/` to `src/erk/core/kit/`
2. Move bundled kits to `src/erk/data/kits/`
3. Merge `DotAgentContext` fields into `ErkContext`
4. Remove `packages/dot-agent-kit/` entirely
5. Evaluate if `erk_shared` is still needed

## Critical Files Reference

### Facade Implementation

- `src/erk/cli/cli.py` - Register new command groups
- `src/erk/cli/help_formatter.py` - Help organization
- `packages/dot-agent-kit/src/dot_agent_kit/cli/__init__.py` - Add deprecation

### Script Rename

- `packages/dot-agent-kit/src/dot_agent_kit/commands/kit_command/group.py` - Dynamic loading
- `packages/dot-agent-kit/src/dot_agent_kit/models/kit.py` - Kit manifest schema
- `packages/dot-agent-kit/src/dot_agent_kit/data/kits/*/kit.yaml` - All kit manifests

### Config Migration

- `packages/dot-agent-kit/src/dot_agent_kit/io/state.py` - Config path resolution
- `packages/dot-agent-kit/src/dot_agent_kit/io/registry.py` - Registry paths
- `AGENTS.md` - Kit registry reference

### Hook Updates

- `packages/dot-agent-kit/src/dot_agent_kit/hooks/installer.py` - Hook invocation generation
- `packages/dot-agent-kit/src/dot_agent_kit/data/kits/*/kit.yaml` - Hook definitions

## Skills to Load

Before implementing:

- `dignified-python-313` - Python code standards
- `fake-driven-testing` - Testing patterns

## PR Sequence

1. ✅ **PR #2809: Facade layer + config migration** - Add `erk kit/artifact/hook/docs` facade commands, migrate config to `.erk/` (MERGED)
2. ✅ **PR #2787: Rename to scripts** - `kit_cli_commands` → `scripts`, updated CLI structure (MERGED)
3. ✅ **PR #2803: Replace invocations** - Replace `dot-agent kit-command` with `erk kit exec` in all kit commands (MERGED)
4. ✅ **PR #2810: Rename env vars** - Rename `DOT_AGENT_*` environment variables to `ERK_*` prefix (MERGED)
5. ✅ **PR #?: Documentation updates** - Update docs to use `erk kit` instead of `dot-agent` (this branch)

## Progress Notes

- Phases 1-3 were consolidated into fewer PRs than originally planned
- The facade, scripts rename, and config migration shipped together in #2809
- Hook invocations updated in #2803
- Environment variables renamed from `DOT_AGENT_*` to `ERK_*` in #2810
- Documentation updated: `.claude/settings.json` permissions, user-facing docs, skills, and commands now use `erk` commands
