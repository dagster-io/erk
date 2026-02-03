---
title: Bundled Artifacts (.codex/ Directory)
read_when:
  - understanding what gets bundled with erk releases
  - working with .codex/ directory structure
  - evaluating agent portability
tripwires:
  - action: "adding skills to .codex/ without verifying they work outside Claude Code"
    warning: "Codex portability: Verify skills don't use Claude-only features (hooks, system prompts, TodoWrite). See bundled-artifacts.md for portable vs Claude-only classification."
  - action: "modifying skills in .codex/ that are also in .claude/"
    warning: "TOML duplicate key constraint: A skill can only be defined once. Either in .codex/ (portable) OR .claude/ (Claude-only), never both. See single-canonical-destination pattern in toml-handling.md."
---

# Bundled Artifacts (.codex/ Directory)

The `.codex/` directory contains agent artifacts (skills, commands, agents) that ship with erk releases for portability across different AI coding agents.

## What Gets Bundled

When users run `erk init`, artifacts from `.codex/` are copied to their agent-specific directory:

```bash
# User has Claude Code
erk init  # Copies .codex/* → .claude/*

# User has OpenAI Codex (future)
erk init --agent codex  # Copies .codex/* → .codex/* (no copy needed)

# User has GitHub Copilot (future)
erk init --agent copilot  # Copies .codex/* → .github/agents/*
```

**Key insight**: The same artifact works across agents because it avoids agent-specific features.

## Codex Portability Classification

Not all erk skills are portable. Classification based on feature dependencies:

### Portable Skills (12 total)

These skills use only standard features available across agents:

**Commands & Planning**:

- `command-creator` - Command authoring patterns
- `erk-planning` - Plan creation and structure
- `objective` - Objective workflow

**Code Quality**:

- `dignified-python` - Python coding standards
- `dignified-code-simplifier` - Code simplification patterns
- `fake-driven-testing` - Test architecture

**Documentation & Review**:

- `learned-docs` - Documentation best practices
- `pr-feedback-classifier` - PR review comment classification
- `pr-operations` - PR thread operations

**Integrations**:

- `gh` - GitHub CLI usage
- `session-inspector` - Session analysis
- `erk-diff-analysis` - Commit message generation

**Portability characteristics**:

- No hooks (all instructions in SKILL.md)
- No Claude-specific tools (TodoWrite, EnterPlanMode, AskUserQuestion)
- No system prompt overrides
- Work with standard tool set (Read, Write, Edit, Bash, Grep, Glob)

### Claude-Only Skills (4 total)

These skills depend on Claude Code exclusive features:

**Features requiring hooks**:

- `erk-exec` - Uses PreToolUse hook for dignified-python injection
- `ci-iteration` - Requires iterative failure handling with hooks

**Features requiring Claude tools**:

- (Currently none - all tool-dependent skills have been refactored)

**Features requiring system prompts**:

- (Currently none - system prompts moved to SKILL.md bodies)

**Why Claude-only**: Hooks and extended context management aren't in OpenCode/Codex spec.

## TOML Duplicate Key Constraint

**Critical rule**: A skill can only exist in ONE location.

### The Problem

TOML doesn't allow duplicate keys. If a skill is defined in both `.codex/` and `.claude/`, `erk init` fails:

```toml
# This is invalid TOML
[skills.my-skill]
source = ".codex/skills/my-skill"

[skills.my-skill]  # ERROR: duplicate key
source = ".claude/skills/my-skill"
```

### The Pattern: Single Canonical Destination

**Rule**: Choose ONE canonical location:

- **Portable skills** → `.codex/` only (gets copied to agent-specific dir on init)
- **Claude-only skills** → `.claude/` only (never copied)

**Never both.**

### Example: dignified-python

```toml
# .codex/skills/dignified-python/SKILL.md
# This is portable - no hooks, no Claude-only features
# Lives in .codex/ and gets copied to .claude/ on init

# NOT in .claude/skills/dignified-python/ - would create duplicate
```

### Example: erk-exec

```toml
# .claude/skills/erk-exec/SKILL.md
# This requires hooks - Claude-only
# Lives in .claude/ only, never copied

# NOT in .codex/ - would fail on other agents
```

## Planned: get_bundled_codex_dir() Function

**Purpose**: Programmatic access to bundled artifacts for init commands.

**Location**: `src/erk/bundled/` (planned)

**Interface** (proposed):

```python
def get_bundled_codex_dir() -> Path:
    """Return path to .codex/ directory in erk installation.

    Returns absolute path to bundled .codex/ directory for copying
    to user's agent-specific config.
    """
    ...
```

**Usage** (planned):

```python
# In erk init command
bundled_dir = get_bundled_codex_dir()
target_dir = Path.home() / ".claude"

# Copy portable skills to user's config
shutil.copytree(bundled_dir / "skills", target_dir / "skills")
```

**Status**: Not yet implemented. When implemented, update this doc with actual module path.

## Migration Strategy

When making a skill portable:

### Step 1: Remove Claude-Only Dependencies

- Remove hook references
- Replace TodoWrite with plain markdown logging
- Replace EnterPlanMode with explicit plan file reads
- Replace AskUserQuestion with clear prompts to user

### Step 2: Test Without Hooks

Verify skill works with hooks disabled:

```bash
# Temporarily rename hooks
mv .claude/hooks .claude/hooks.disabled

# Test skill
/my-skill [args]

# Re-enable
mv .claude/hooks.disabled .claude/hooks
```

### Step 3: Move to .codex/

```bash
# Move from Claude-specific to portable
git mv .claude/skills/my-skill .codex/skills/my-skill

# Update .codex/config.toml to reference new location
```

### Step 4: Document Portability

Update frontmatter:

```yaml
---
description: ... (no mention of Claude-specific features)
portability: portable # or: claude-only
---
```

## Related Documentation

- [multi-agent-portability.md](multi-agent-portability.md) - Agent comparison and session abstraction
- `docs/learned/reference/toml-handling.md` - TOML duplicate key pattern
- `docs/learned/commands/command-portability.md` - Command-level portability patterns
