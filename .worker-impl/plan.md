# Plan: Consolidate erk-exec-reference into Workflow-Oriented erk-exec Skill

## Summary

Restructure the auto-generated `erk-exec-reference` skill into a new `erk-exec` skill that combines:
- **Curated SKILL.md** - Workflow-oriented guidance organized by task
- **Auto-generated reference.md** - Complete command syntax reference

## Files to Modify

| File | Action |
|------|--------|
| `.claude/skills/erk-exec-reference/` | Rename folder to `erk-exec/` |
| `.claude/skills/erk-exec/SKILL.md` | Create new curated workflow guide |
| `.claude/skills/erk-exec/reference.md` | Move current content here (auto-generated) |
| `packages/erk-dev/src/erk_dev/exec_reference/generate.py` | Update frontmatter (remove name/description) |
| `packages/erk-dev/src/erk_dev/commands/gen_exec_reference_docs/command.py` | Update output path (line 50) |
| `docs/learned/cli/erk-exec-commands.md` | Create with tripwire |

## Implementation Steps

### Step 1: Rename skill folder and file

```bash
git mv .claude/skills/erk-exec-reference .claude/skills/erk-exec
git mv .claude/skills/erk-exec/SKILL.md .claude/skills/erk-exec/reference.md
```

### Step 2: Update generator - generate.py

**File:** `packages/erk-dev/src/erk_dev/exec_reference/generate.py`

Replace lines 166-173 (SKILL_FRONTMATTER constant):

```python
SKILL_FRONTMATTER = """\
---
name: erk-exec-reference
description: >
  Reference for all `erk exec` subcommands with flags and usage.
  Use when looking up erk exec command syntax, flags, or options.
---
"""
```

With (no name/description since it's not the main skill file):

```python
REFERENCE_HEADER = """\
<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Run 'erk-dev gen-exec-reference-docs' to regenerate. -->
"""
```

Update `generate_exec_reference()` (line 176+) to use `REFERENCE_HEADER` and remove the duplicate auto-generated comment that's already in lines 185-186.

### Step 3: Update generator - command.py

**File:** `packages/erk-dev/src/erk_dev/commands/gen_exec_reference_docs/command.py`

Change line 50:
```python
output_path = repo_root / ".claude" / "skills" / "erk-exec-reference" / "SKILL.md"
```
To:
```python
output_path = repo_root / ".claude" / "skills" / "erk-exec" / "reference.md"
```

Update docstring (line 41) to reflect new path.

### Step 4: Create new curated SKILL.md

**File:** `.claude/skills/erk-exec/SKILL.md`

```markdown
---
name: erk-exec
description: >
  Guide for erk exec subcommands. Use when running erk exec commands
  to understand syntax, find the right command for a task, or learn
  common workflows. Always check syntax with -h or load this skill
  before running erk exec commands.
---

# erk exec Guide

## Quick Start

Before running any `erk exec` command, check syntax with `-h`:

```bash
erk exec <command> -h
```

## Commands by Workflow

### PR Review Operations

When addressing PR review comments or resolving threads:

| Command | Purpose |
|---------|---------|
| `get-pr-review-comments` | Fetch review comments (use `--pr N`) |
| `resolve-review-thread` | Resolve a thread (use `--thread-id ID`) |
| `reply-to-discussion-comment` | Reply to discussion comment |
| `get-pr-discussion-comments` | Fetch discussion comments |

**Typical workflow:**
1. `erk exec get-pr-review-comments --pr 123`
2. Make code changes
3. `erk exec resolve-review-thread --thread-id PRRT_xxx`

### Plan Operations

When working with erk-plan issues:

| Command | Purpose |
|---------|---------|
| `plan-save-to-issue` | Save plan to GitHub issue |
| `get-plan-metadata` | Get metadata from plan issue |
| `setup-impl-from-issue` | Set up .impl/ from issue |
| `get-issue-body` | Fetch issue body (REST API) |
| `update-issue-body` | Update issue body (REST API) |

### Session Operations

When working with Claude Code sessions:

| Command | Purpose |
|---------|---------|
| `list-sessions` | List sessions for current project |
| `preprocess-session` | Compress session for analysis |
| `upload-session` | Upload session to gist |
| `download-remote-session` | Download session from gist |

### Marker Operations

For inter-process communication:

| Command | Purpose |
|---------|---------|
| `marker create` | Create marker file |
| `marker exists` | Check if marker exists |
| `marker read` | Read marker content |
| `marker delete` | Delete marker file |

All marker commands require `--session-id`.

## Full Reference

For complete syntax details on all 65+ commands:

@reference.md
```

### Step 5: Create tripwire document

**File:** `docs/learned/cli/erk-exec-commands.md`

```markdown
---
title: erk exec Commands
read_when:
  - "running erk exec subcommands"
  - "looking up erk exec syntax"
tripwires:
  - action: "running any erk exec subcommand"
    warning: "Check syntax with `erk exec <command> -h` first, or load erk-exec skill for workflow guidance."
---

# erk exec Commands

The `erk exec` command group contains utility scripts for automation and agent workflows.

## Usage Pattern

All erk exec commands use named options (not positional arguments for most parameters):

```bash
# Correct
erk exec get-pr-review-comments --pr 123

# Wrong - positional arguments don't work
erk exec get-pr-review-comments 123
```

## Key Commands by Category

See the `erk-exec` skill for complete workflow guidance and the full command reference.

### PR Operations
- `get-pr-review-comments` - Fetch PR review threads
- `resolve-review-thread` - Resolve a review thread
- `reply-to-discussion-comment` - Reply to PR discussion

### Plan Operations
- `plan-save-to-issue` - Save plan to GitHub
- `get-plan-metadata` - Read plan issue metadata
- `setup-impl-from-issue` - Prepare .impl/ folder

### Session Operations
- `list-sessions` - List Claude Code sessions
- `preprocess-session` - Compress session for analysis
```

### Step 6: Regenerate and sync

```bash
erk docs sync                          # Regenerates tripwires.md
erk-dev gen-exec-reference-docs        # Regenerates reference.md
```

### Step 7: Search and update stale references

Search for "erk-exec-reference" in:
- AGENTS.md / CLAUDE.md
- Other skills that might reference it
- Any documentation

## Verification

1. **Run CI:** `make fast-ci` - confirms generator check works with new path
2. **Skill loads:** Test that `erk-exec` skill loads in Claude Code
3. **Reference accurate:** `erk-dev gen-exec-reference-docs --check` passes
4. **Tripwire appears:** Check tripwires.md includes new entry after `erk docs sync`