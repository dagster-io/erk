# Kit Development Workflow

Guide for erk repository developers editing bundled kits.

## Overview

This document describes the workflow for editing kit files that are bundled with dot-agent-kit. This workflow is **only relevant for developers working in the erk repository** who are modifying the kits in `packages/dot-agent-kit/src/dot_agent_kit/data/kits/`.

For creating new kits from scratch, see [README.md](README.md).

## Quick Reference

| Step | Action                                          | Notes                             |
| ---- | ----------------------------------------------- | --------------------------------- |
| 1    | Enable dev_mode in pyproject.toml               | One-time setup                    |
| 2    | Install kits (creates symlinks)                 | `erk kit install --all`           |
| 3    | Edit `.claude/` files directly in your worktree | Changes immediately affect source |
| 4    | Test and iterate on changes                     | No sync needed - changes are live |
| 5    | Commit your changes                             | `git add . && git commit`         |

✅ **No more sync-back needed!** Edits to `.claude/` immediately affect the source files via symlinks.

## The Development Workflow

When editing bundled kits in the erk repository, follow this symlink-based workflow:

### 1. Enable Dev Mode (One-Time Setup)

Add the following to your `pyproject.toml` in the erk repository root:

```toml
[tool.dot-agent]
dev_mode = true
```

This enables symlink-based kit installation for development.

### 2. Install Kits with Symlinks

Run the kit install command to create symlinks:

```bash
erk kit install --all --overwrite
```

With `dev_mode = true`, this creates symlinks from `.claude/` to the kit source files in `packages/dot-agent-kit/src/dot_agent_kit/data/kits/`. You'll see output like:

```
  Using symlinks (dev_mode enabled)
  Installed skill: gt-graphite -> source
  Installed agent: devrun -> source
```

### 3. Edit .claude Files Directly

Edit the kit files in `.claude/` within your worktree. **Because these are symlinks, your edits immediately affect the source files:**

```bash
# Example: Edit a skill file
vim .claude/skills/gt-graphite/SKILL.md

# This actually edits:
# packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/skills/gt-graphite/SKILL.md
```

### 4. Test and Iterate

Use the artifacts normally to test your changes. Claude Code reads from `.claude/`, and since these are symlinks, your edits take effect immediately in both locations.

### 5. Commit Your Changes

Commit the source files (not `.claude/`, which should be in .gitignore):

```bash
git add packages/dot-agent-kit/src/dot_agent_kit/data/kits/
git commit -m "Update gt-graphite skill with new examples"
```

**Important**: The `.claude/` directory should be in your `.gitignore`. Only commit the actual source files in `packages/`.

## How Symlinks Work

When `dev_mode` is enabled:

```
.claude/skills/gt-graphite/SKILL.md  →  packages/dot-agent-kit/src/.../kits/gt/skills/gt-graphite/SKILL.md
   (symlink in working directory)           (actual source file)
```

Editing either path affects the same file. This eliminates the need for sync-back operations.

## The Three-Step Synchronization Principle

**Critical understanding**: While symlinks sync file **contents** automatically, they do NOT eliminate the need for manifest updates when **renaming, moving, or deleting** artifacts.

When working with bundled kits, changes must be synchronized across three locations:

1. **Source file** - The actual file in `packages/dot-agent-kit/src/dot_agent_kit/data/kits/`
2. **Manifest** - The `kit.yaml` file declaring which artifacts belong to the kit
3. **Installed artifact** - The symlink in `.claude/` pointing to the source

### What Works Automatically (No Manual Sync)

✅ **Editing file contents**: Changes to `.claude/` files sync immediately via symlinks
✅ **Adding new content**: Writing new sections, updating documentation, fixing bugs
✅ **Testing changes**: Claude Code sees changes immediately

### What Requires Manual Steps

❌ **Renaming artifacts**: Update kit.yaml + recreate symlink + update cross-references
❌ **Moving artifacts**: Update kit.yaml paths + reinstall kit
❌ **Deleting artifacts**: Remove from kit.yaml + reinstall to clean up symlinks
❌ **Adding artifacts**: Add to kit.yaml + reinstall to create symlinks

### Kit Modification Checklist

Use this checklist when making structural changes to kits (rename/move/delete/add):

```markdown
## Before Committing Kit Changes

- [ ] Updated kit.yaml manifest with new paths/entries
- [ ] Updated cross-references in other artifacts (search for old names)
- [ ] Force-reinstalled kit: `erk kit install bundled:{kit-name} --force`
- [ ] Verified installation: `erk check` shows ✅
- [ ] Tested artifact invocation works correctly
- [ ] Committed source files (in packages/, not .claude/)
```

### Common Mistake: Renaming Without Manifest Update

**Scenario**: You split `create-planned-wt.md` into `persist-plan.md` and `create-planned-wt.md` (rewritten)

**What happens without proper steps:**

1. ✅ File renamed in source directory
2. ❌ kit.yaml still references old filename
3. ❌ Symlink points to non-existent file
4. ❌ `erk check` reports "Missing artifact"

**Correct procedure:**

1. Rename source file: `git mv old-name.md new-name.md`
2. Update kit.yaml: Change artifact path to new filename
3. Update cross-references: Search for old command name in other files
4. Force-reinstall: `erk kit install bundled:{kit-name} --force`
5. Verify: `erk check` should show ✅

**See**: [docs/ARTIFACT_LIFECYCLE.md](docs/ARTIFACT_LIFECYCLE.md) for detailed procedures on renaming, moving, and deleting artifacts.

## Symlink Protection

The system automatically protects symlinks:

- **During sync**: `erk kit sync` skips symlinked artifacts and reports:

  ```
  Skipping symlinked artifacts in dev mode:
    .claude/skills/gt-graphite
  ```

- **During install**: Installing with `--overwrite` preserves the symlink behavior

## Fallback Behavior

If symlink creation fails (e.g., on Windows without administrator privileges, or unsupported filesystems), the system automatically falls back to copying files:

```
  Warning: Could not create symlink for gt-graphite (Operation not supported)
  Falling back to file copy
```

In this case, you would need to manually sync changes between `.claude/` and the source.

## Disabling Dev Mode

To switch back to copy-based installation:

1. Remove or set `dev_mode = false` in pyproject.toml:

   ```toml
   [tool.dot-agent]
   dev_mode = false
   ```

2. Reinstall kits:
   ```bash
   erk kit install --all --overwrite
   ```

This reverts to copying files instead of creating symlinks.

## When This Workflow Matters

This workflow is **only necessary for erk repository developers** editing bundled kits.

**You need this workflow if:**

- You're working in the erk repository
- You're editing kits in `packages/dot-agent-kit/src/dot_agent_kit/data/kits/`
- You're modifying bundled skills, agents, or commands

**You don't need this workflow if:**

- You're a user installing kits from packages
- You're creating new kits from scratch (see [README.md](README.md))
- You're editing project-local `.claude/` files that aren't from kits

## Working with Kit CLI Commands

**Kit CLI commands** are Python scripts that handle mechanical git/gh/gt operations in isolated subprocess contexts, outputting structured JSON results. They exist as a **performance and cost-optimization pattern** for Claude Code interactions.

### Why Kit CLI Commands?

Kit CLI commands move mechanical operations out of Claude's main context:

- **Performance**: Deterministic Python code is much faster than LLM-based orchestration
- **Cost savings**: All git/gh/gt operations run in isolated subprocesses, dramatically reducing token usage
- **Determinism**: Known workflows execute reliably without AI overhead
- **JSON output**: Only final structured results enter main Claude context

### When to Use

Create a kit CLI command when:

- Multiple git/gh/gt commands would pollute main context
- Workflow is repeatable and structured
- JSON output makes parsing and decision-making cleaner

### Patterns

Two distinct patterns exist:

- **Single-phase**: Straightforward workflows (example: `update_pr.py`)
- **Two-phase**: Complex workflows with AI analysis between mechanical steps (example: `submit_branch.py`)

### Relationship to Slash Commands

Slash commands invoke kit CLI commands and parse their JSON responses:

1. User runs: `/gt:pr-update`
2. Slash command invokes: `erk kit exec gt update-pr`
3. Kit CLI command executes operations, outputs JSON
4. Slash command parses JSON and reports to user

### Full Documentation

See [docs/KIT_CLI_COMMANDS.md](docs/KIT_CLI_COMMANDS.md) for:

- Complete architecture patterns
- Code structure and conventions
- Step-by-step workflow
- Testing patterns
- Best practices

## Related Documentation

- [README.md](README.md) - Kit structure and creation guide
- [docs/HOOKS.md](docs/HOOKS.md) - Hook development and configuration guide
- [docs/KIT_CLI_COMMANDS.md](docs/KIT_CLI_COMMANDS.md) - Kit CLI command development guide
- [../../docs/WORKSTACK_DEV.md](../../docs/WORKSTACK_DEV.md) - erk-dev CLI architecture
