---
title: Kit Artifact Dev Mode
read_when:
  - "adding new slash commands to a kit in dev mode"
  - "adding new agents or skills to erk kit"
  - "understanding kit:sync workflow"
---

# Kit Artifact Dev Mode

Add artifacts (commands, agents, skills) to kits during development without publishing.

## Dev Mode Detection

The system detects dev mode when:
1. `packages/dot-agent-kit` exists (dev mode)
2. Running from editable install (`pip install -e .`)

When in dev mode, kits are loaded from source directories, not installed packages.

## 5-Step Process

### Step 1: Create Artifact File

Create the file in the kit's source directory:

```bash
# Command
packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/commands/erk/my-command.md

# Agent
packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/agents/erk/my-agent.md

# Skill
packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/skills/erk/my-skill.md
```

### Step 2: Register in kit.yaml

Add artifact to the kit's `kit.yaml`:

```yaml
name: erk
version: 0.1.0

commands:
  - erk/my-command.md

agents:
  - erk/my-agent.md

skills:
  - erk/my-skill.md
```

### Step 3: Symlink to .claude/

Run `kit sync` to create symlinks:

```bash
cd packages/dot-agent-kit
kit sync

# Or with --force if version wasn't bumped
kit sync --force
```

**What it does**:
- Creates symlinks FROM `.claude/` TO kit source directories
- Example: `.claude/commands/erk/my-command.md` → `packages/.../commands/erk/my-command.md`

### Step 4: Update pyproject.toml

Add artifact to package data (for distribution):

```toml
[tool.poetry]
# ... existing fields ...

[tool.poetry.include]
{ path = "src/dot_agent_kit/data/kits/erk/commands/erk/my-command.md", format = ["sdist", "wheel"] }
```

### Step 5: Verify

Check symlink exists and points to correct location:

```bash
ls -la .claude/commands/erk/my-command.md
# Should show: my-command.md -> ../../../packages/.../commands/erk/my-command.md

# Test the command
/erk:my-command
```

## Common Pitfalls

### Forgetting kit sync

❌ **Symptom**: Artifact file exists but command not found

✅ **Fix**: Run `kit sync` to create symlinks

### Forgetting --force flag

❌ **Symptom**: `kit sync` says "Already up to date" but symlink missing

✅ **Fix**: Run `kit sync --force` (version wasn't bumped)

### Wrong symlink direction

❌ **WRONG**: Kit source → `.claude/` (breaks when kit is uninstalled)

✅ **CORRECT**: `.claude/` → Kit source (source of truth is kit)

### Symlinks in bundled kits

❌ **WRONG**: Committing symlinks in kit source directory

✅ **CORRECT**: Kit source contains real files. `kit install` creates symlinks in `.claude/`.

## Verification Steps

```bash
# 1. Check file exists in source
ls packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/commands/erk/my-command.md

# 2. Check registered in kit.yaml
grep "my-command.md" packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit.yaml

# 3. Check symlink exists
ls -la .claude/commands/erk/my-command.md

# 4. Check symlink points to source
readlink .claude/commands/erk/my-command.md

# 5. Test command works
/erk:my-command --help
```

## Related Documentation

- [Kit Shared Includes](../kit-shared-includes.md) - Sharing content between artifacts
- [Kit Artifact and Symlink Management](artifact-management.md) - Symlink lifecycle
