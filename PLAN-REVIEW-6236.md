# Plan: Compress docs/learned/index.md for Agent Consumption

## Context

Vercel's evals showed a compressed docs index (40KB → 8KB) in AGENTS.md achieved 100% agent pass rate. The key: agents need to know WHAT EXISTS and WHERE TO FIND IT, not read human-oriented prose.

Erk's `docs/learned/index.md` is embedded in AGENTS.md via `@` include (~3.2KB ambient context). It currently contains:

- Human-contributor instructions ("Add docs here for...") irrelevant to agents
- 13 of 25 categories with NO description (zero matching signal)
- A preamble that duplicates AGENTS.md's "Documentation-First Discovery" section
- Two separate dicts (`CATEGORY_DESCRIPTIONS` + `CATEGORY_ROUTING_HINTS`) with overlapping purpose

## Approach: Unified Keyword-Based Category Descriptions

Merge `CATEGORY_DESCRIPTIONS` and `CATEGORY_ROUTING_HINTS` into a single `CATEGORY_KEYWORDS` dict. Strip all prose. Add keywords for every category. Remove the redundant preamble.

## Changes

### 1. Replace two dicts with `CATEGORY_KEYWORDS` in operations.py

**File:** `src/erk/agent_docs/operations.py` (lines 28-96)

Delete `CATEGORY_DESCRIPTIONS` (lines 31-78) and `CATEGORY_ROUTING_HINTS` (lines 83-96). Replace with:

```python
# Category keywords for index generation and routing.
# Terse keyword phrases for agent pattern-matching.
# Used in both root index.md and tripwires-index.md.
CATEGORY_KEYWORDS: dict[str, str] = {
    "architecture": "core patterns, dry-run, gateways, subprocess, shell integration",
    "capabilities": "Claude Code capabilities, tool use",
    "checklists": "step-by-step checklists, implementation guides",
    "ci": "GitHub Actions, `.github/workflows/`, `.github/actions/`",
    "claude-code": "Claude Code configuration, settings",
    "cli": "CLI commands, Click, output formatting, `src/erk/cli/`",
    "commands": "slash commands, `.claude/commands/`",
    "config": "project configuration, settings files",
    "configuration": "erk configuration, YAML config",
    "documentation": "doc structure, documentation methodology, agent docs",
    "erk": "erk workflows, worktrees, PR sync, Graphite",
    "erk-dev": "erk development, internal tooling",
    "gateway": "gateway implementations, `gateway/` code",
    "hooks": "Claude hooks, `.claude/hooks/`",
    "integrations": "external integrations, third-party tools",
    "objectives": "objectives, goal tracking",
    "planning": "plans, `.impl/`, `.worker-impl/`, agent delegation",
    "pr-operations": "pull requests, PR workflows",
    "refactoring": "refactoring patterns, code restructuring",
    "reference": "API specs, format specifications",
    "sessions": "session logs, `~/.claude/projects/`, parallel sessions",
    "testing": "tests, test infrastructure, `tests/`",
    "textual": "Textual framework",
    "tui": "TUI application, `src/erk/tui/`",
    "workflows": "workflow patterns, automation",
}
```

### 2. Update `generate_root_index()` in operations.py

**File:** `src/erk/agent_docs/operations.py` (lines 518-567)

Two changes:

- **Remove preamble**: Drop the two lines "Before starting work, scan the read-when conditions below." and "If your current task matches, read the linked document **before writing code**." — this instruction now lives in AGENTS.md's "Documentation-First Discovery" section.
- **Change title**: "Agent Documentation" → "Agent Documentation Index"
- **Use `CATEGORY_KEYWORDS`**: Replace `CATEGORY_DESCRIPTIONS.get(category.name)` with `CATEGORY_KEYWORDS.get(category.name)`. Since every category now has keywords, the `if description` / `else` branch can use the same pattern (always include keywords if present).

### 3. Update `generate_tripwires_index()` in operations.py

**File:** `src/erk/agent_docs/operations.py` (line 460)

Change `CATEGORY_ROUTING_HINTS.get(...)` → `CATEGORY_KEYWORDS.get(...)`.

### 4. Regenerate and verify

Run `erk docs sync` to regenerate `docs/learned/index.md` and `docs/learned/tripwires-index.md`, then verify output.

## Expected Output

**Before:**

```markdown
# Agent Documentation

Before starting work, scan the read-when conditions below.
If your current task matches, read the linked document **before writing code**.

## Categories

- [architecture/](architecture/) — Explore when working on core patterns (dry-run, gateways, subprocess, shell integration). Add docs here for cross-cutting technical patterns.
- [capabilities/](capabilities/)
- [checklists/](checklists/)
```

**After:**

```markdown
# Agent Documentation Index

## Categories

- [architecture/](architecture/) — core patterns, dry-run, gateways, subprocess, shell integration
- [capabilities/](capabilities/) — Claude Code capabilities, tool use
- [checklists/](checklists/) — step-by-step checklists, implementation guides
```

Every category gets keywords. No prose. No preamble.

## What This Does NOT Change

- `@docs/learned/index.md` embed in AGENTS.md stays (this just changes what it contains)
- Per-category index files keep their current format (read-when conditions per doc)
- Uncategorized docs section format stays the same
- Tripwires generation logic stays the same (just uses the new dict name)

## Verification

1. `erk docs sync` regenerates cleanly
2. Read `docs/learned/index.md` — confirm compact format, all 25 categories with keywords
3. Read `docs/learned/tripwires-index.md` — confirm routing hints still render correctly
4. `make fast-ci` passes
